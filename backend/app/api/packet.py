from __future__ import annotations

from collections.abc import AsyncGenerator, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.cache.models import CachedResource
from backend.app.cache.store import (
    build_packet,
    get_evidence_card,
    get_evidence_cards,
    get_patient_resource,
    get_patient_resources,
    list_patient_ids,
)
from backend.app.config import CACHE_TTL_SECONDS
from backend.app.dtos import ConnectorStatus, DecisionPacket
from backend.app.fhir.subset import reasoning_view
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.knowledge.rxnav import DrugResolutionReport
from backend.app.providers.status import list_connector_status
from backend.app.reasoning.knowledge_evidence import (
    build_knowledge_evidence,
    patient_age_years,
)
from backend.app.reasoning.pipeline import build_reasoned_packet

# Must match backend.app.api.intake.FETCH_METADATA_TYPE — the resource_type
# used to persist a per-patient partial-data notice (#73). Duplicated here so
# this module doesn't import from /intake (which would create a cycle).
_FETCH_METADATA_TYPE = "FetchMetadata"

router = APIRouter(prefix="/patients", tags=["packet"], dependencies=[Depends(require_dev_token)])
connectors_router = APIRouter(tags=["connectors"], dependencies=[Depends(require_dev_token)])
evidence_router = APIRouter(tags=["evidence"], dependencies=[Depends(require_dev_token)])
audit_router = APIRouter(tags=["audit"], dependencies=[Depends(require_dev_token)])


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            yield session


@router.get("")
async def get_patients(db: AsyncSession = Depends(get_db)) -> list[dict[str, str]]:  # noqa: B008
    db_ids = set(await repo.list_patient_ids_from_db(db))
    static_ids = set(list_patient_ids())
    all_ids = sorted(static_ids | db_ids)
    return [{"id": pid} for pid in all_ids]


async def _build_packet_body(db: AsyncSession, patient_id: str) -> dict[str, object]:
    """Build the servable DecisionPacket for a patient.

    Computes REAL cited drug-knowledge evidence (RxNav→openFDA/DDInter/Beers/ACB)
    for the patient's medications, persists it to the evidence_card store
    (CACHE-04), then runs the live reasoning pipeline (Gemini → citation gate →
    cache-authoritative verifier); on any abstention it falls back to the static
    scaffold so the result is always citation-safe. The curated static cards
    remain citable alongside the computed ones.
    """
    scaffold = build_packet(patient_id)
    resources, resource_lookup = await _patient_resources(db, patient_id)

    # KNOW-01..05: compute real cited evidence. Each source degrades gracefully,
    # so an exhausted API token / timeout simply yields fewer cards.
    knowledge = await build_knowledge_evidence(resources, patient_age_years(resources))
    for card in knowledge.cards:
        await repo.upsert_evidence_card(
            db,
            evidence_id=str(card["id"]),
            kind=str(card["kind"]),
            body={k: card[k] for k in ("id", "source", "snippet", "ref_url")},
        )

    # Merge the computed cards with the curated static cards (the hero-demo
    # narrative) into the citation allow-list, deduped by the canonical id.
    static_snippets = [
        EvidenceSnippet(
            id=str(card["id"]),
            kind="evidence",
            ref=str(card["id"]),
            label=str(card.get("snippet", "")),
        )
        for card in get_evidence_cards(patient_id)
    ]
    seen: set[str] = set()
    evidence: list[EvidenceSnippet] = []
    for snippet in [*knowledge.snippets, *static_snippets]:
        if snippet.id not in seen:
            seen.add(snippet.id)
            evidence.append(snippet)

    # The verifier resolves a citation against the computed cards first, then the
    # static store — so both computed and curated evidence pass the gate.
    computed_mirror = {str(card["id"]): dict(card) for card in knowledge.cards}

    def evidence_lookup(ref: str) -> dict | None:
        return computed_mirror.get(ref) or get_evidence_card(ref)

    packet = await build_reasoned_packet(
        scaffold,
        resources,
        evidence,
        resource_lookup=resource_lookup,
        evidence_lookup=evidence_lookup,
    )
    # REASON-07 min-input contract: fold the RxNorm-resolution honesty signals
    # (per-med unresolved flags + the thin-input low-confidence note) into the
    # packet's data gaps, so it never implies confident reasoning over drugs it
    # could not normalize. Derived from the resolution report (the input), not the
    # reasoning output, so it holds on both the reasoned and abstained paths and is
    # baked into the cached body.
    body = packet.model_dump()
    return _extend_data_gaps(body, _reason07_data_gaps(knowledge.resolution_report))


async def _patient_resources(
    db: AsyncSession, patient_id: str
) -> tuple[list[dict[str, object]], Callable[[str, str, str], dict | None]]:
    """Resolve a patient's FHIR resources from the static seed store + the DB cache.

    Intake'd patients have their fetched resources in ``cached_resource``, not the
    static seed store, so both the reasoning input list (flattener + knowledge
    evidence) and the per-citation lookup (the verifier's ``resource_lookup``) must
    consult both. Returns the merged resource list and a synchronous lookup closure,
    BOTH DB-first: on the rare collision where one ``patient_id`` holds a static seed
    and a fetched resource with the same ``(type, id)``, the persisted body wins in
    the list AND the lookup — so the flattened context the model/verifier sees never
    disagrees with the body the gate resolves (the provenance-precedence lesson). For the
    seeded demo patients there are no DB FHIR rows, so the list is exactly the static
    seed set. Resource rows are patient-scoped (composite PK) — no cross-patient leak.
    """
    static_resources = get_patient_resources(patient_id)
    db_rows = await repo.list_patient_resources(db, patient_id=patient_id)
    db_by_key: dict[tuple[str, str], dict[str, object]] = {
        (str(row.resource_type), str(row.resource_id)): row.body
        for row in db_rows
        if isinstance(row.body, dict)
    }
    resources = [
        *db_by_key.values(),
        *(
            r
            for r in static_resources
            if (str(r.get("resourceType")), str(r.get("id"))) not in db_by_key
        ),
    ]

    def resource_lookup(pid: str, resource_type: str, resource_id: str) -> dict | None:
        return db_by_key.get((resource_type, resource_id)) or get_patient_resource(
            pid, resource_type, resource_id
        )

    return resources, resource_lookup


@router.get("/{patient_id}/packet", response_model=DecisionPacket)
async def get_packet(
    patient_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> dict[str, object]:
    built: dict[str, object] = {}

    async def fetcher() -> dict[str, object]:
        nonlocal built
        built = await _build_packet_body(db, patient_id)
        return built

    # KNOWN LIMITATION (follow-up #66): on a REFRESH the fetcher's multi-second
    # Gemini call runs inside this request's DB transaction while holding the
    # per-patient advisory lock, so a pooled connection is held for the whole LLM
    # latency. Fine for the single-user demo (and abstention is cheap), but at
    # production concurrency over distinct patients it can exhaust the pool. The
    # real fix moves the LLM call outside the txn/lock — deferred to avoid
    # disturbing the once-only refresh guarantee here.
    row, cache_status = await repo.get_or_refresh(
        db,
        patient_id=patient_id,
        resource_type="DecisionPacket",
        resource_id=patient_id,
        actor=subject,
        fetcher=fetcher,
        source_provider="static",
        ttl_seconds=CACHE_TTL_SECONDS,
    )
    response.headers["X-Cache"] = cache_status.value

    # Reuse the body produced inside get_or_refresh — never re-fetch outside the
    # lock (which would bypass the once-only refresh + audit). A MISS (lost the
    # race with nothing cached) yields an empty body; the X-Cache: MISS header
    # signals the client to retry.
    body = row.body if row is not None else built
    if not body:
        # Serve a minimal, VALID empty packet on the MISS race rather than a bare
        # dict — the DecisionPacket response_model would otherwise 500 on the
        # missing required fields, turning a graceful retry signal into an error.
        body = DecisionPacket(patient_id=patient_id, summary_markdown="").model_dump()
    body = await _merge_partial_data_notice(db, patient_id, body)
    await _persist_servable_hypotheses(db, patient_id, body)
    return {**body, "cache_status": cache_status.value}


async def _persist_servable_hypotheses(
    db: AsyncSession, patient_id: str, body: dict[str, object]
) -> None:
    """Persist the served packet's hypotheses so the provider can confirm/dismiss
    them.

    Keyed ``{patient_id}:{hyp_id}`` (collision-free across patients, matching the
    /intake convention). ``upsert_hypothesis`` refreshes title/group but leaves any
    existing confirmed/dismissed status untouched, so re-fetching a packet never
    un-resolves a hypothesis the clinician already actioned.
    """
    hyps = body.get("hypotheses")
    if not isinstance(hyps, list):
        return
    for hyp in hyps:
        if not isinstance(hyp, dict):
            continue
        hyp_id = hyp.get("id")
        title = hyp.get("title")
        if not isinstance(hyp_id, str) or not isinstance(title, str):
            continue
        group = hyp.get("group")
        await repo.upsert_hypothesis(
            db,
            id=f"{patient_id}:{hyp_id}",
            patient_id=patient_id,
            title=title,
            group=group if isinstance(group, str) else None,
        )


def _extend_data_gaps(body: dict[str, object], extra_gaps: list[str]) -> dict[str, object]:
    """Append gap strings to ``body['data_gaps']``, order-preserving and deduped.

    Shared by the REASON-07 resolution gaps and the partial-data notice so a
    re-fetch never accumulates duplicate lines.
    """
    if not extra_gaps:
        return body
    existing = list(body.get("data_gaps") or [])
    seen = set(existing)
    for gap in extra_gaps:
        if gap not in seen:
            existing.append(gap)
            seen.add(gap)
    return {**body, "data_gaps": existing}


def _reason07_data_gaps(report: DrugResolutionReport) -> list[str]:
    """REASON-07 min-input contract → explicit data gaps from RxNorm resolution.

    Emits one gap per medication that failed to normalize to RxNorm (KNOW-01:
    flagged, never silently dropped — distinguishing an unavailable RxNav from a
    genuine no-match) plus the thin-input low-confidence note when most of the
    provided drugs failed to resolve.

    The total==0 "no drugs provided" variant is intentionally NOT surfaced: a
    patient with no medications is a completeness gap, not a low-confidence
    reasoning signal (and the offline test stub yields an empty report by
    construction, so firing on it would pollute every packet).
    """
    gaps: list[str] = []
    if report.low_confidence_note and report.total_count > 0:
        gaps.append(report.low_confidence_note)
    for resolution in report.resolutions:
        if resolution.resolved:
            continue
        reason = (
            "RxNorm lookup unavailable"
            if resolution.network_error
            else "could not be matched to RxNorm"
        )
        gaps.append(
            f"{resolution.input_name}: {reason} — "
            "drug-knowledge checks skipped for this medication"
        )
    return gaps


async def _merge_partial_data_notice(
    db: AsyncSession, patient_id: str, body: dict[str, object]
) -> dict[str, object]:
    """Fold any persisted partial-data notice into the packet at response time.

    The notice is the source of truth for partial-fetch state — we merge at
    response time rather than baking it into the cached packet so a later
    refetch (clean → partial, or partial → clean) is reflected without having
    to invalidate the cached DecisionPacket.
    """
    meta = await db.get(CachedResource, (patient_id, _FETCH_METADATA_TYPE, patient_id))
    if meta is None or not isinstance(meta.body, dict):
        return body
    notice = meta.body
    missing = notice.get("missing") or []
    warnings_ = notice.get("warnings") or []
    extra_gaps: list[str] = []
    for cat in missing:
        if isinstance(cat, str) and cat:
            extra_gaps.append(f"{cat} not returned by source")
    for w in warnings_:
        if isinstance(w, str) and w:
            extra_gaps.append(w)
    # Preserve order, dedupe — a second /intake on the same partial fetch mustn't
    # accumulate duplicates if the cached packet already has them.
    return _extend_data_gaps(body, extra_gaps)


@router.get("/{patient_id}/resource/{resource_type}/{resource_id}")
async def get_patient_citation(
    patient_id: str,
    resource_type: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> dict[str, object]:
    # DB-first (intake'd patients persist their fetched resources to the cache),
    # then the static seed store — mirroring /evidence and the verifier's
    # precedence so a citation resolves to the body that was actually persisted.
    # Resource rows are patient-scoped (composite PK), so there is no cross-patient
    # id-collision risk. repo.get_resource also writes the per-read audit (CACHE-03);
    # a genuine miss rolls back with the 404.
    row = await repo.get_resource(
        db,
        patient_id=patient_id,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=subject,
    )
    resource: dict[str, object] | None
    if row is not None and isinstance(row.body, dict):
        # SEC-02: intake persists raw provider bundles (Patient.name/address/telecom),
        # so project the DB body through the fail-closed reasoning_view before egress —
        # it drops demographic PHI while keeping MRN/gender/ageYears + clinical fields +
        # the PDF span. The static seed bodies are already hand-minimised (and carry a
        # bare urn:mrn identifier the MR-typed allow-list would otherwise strip), so the
        # static fallback is returned as-is.
        resource = reasoning_view(row.body)
    else:
        resource = get_patient_resource(patient_id, resource_type, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")
    # PDF-sourced resources carry a "span" key (page/start/end/snippet). Surface
    # it under the DTO field name "source_span" so the highlight view can render
    # straight from the /resource response, mirroring Citation.source_span.
    span = resource.get("span")
    if isinstance(span, dict):
        resource = {**resource, "source_span": span}
    return resource


@router.post("/{patient_id}/refresh")
async def refresh(
    patient_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> dict[str, object]:
    body = await _build_packet_body(db, patient_id)
    await repo.upsert_resource(
        db,
        patient_id=patient_id,
        resource_type="DecisionPacket",
        resource_id=patient_id,
        body=body,
        source_provider="static",
        ttl_seconds=CACHE_TTL_SECONDS,
    )
    # upsert_resource writes no audit (CACHE-03 audits reads); a forced refresh
    # re-pulls + overwrites the packet, so leave an explicit resource_read trail
    # attributed to the caller (API-07), matching how get_packet audits.
    await repo.write_audit_event(
        db,
        event_type="resource_read",
        resource_ref=f"DecisionPacket/{patient_id}",
        actor=subject,
        patient_id=patient_id,
    )
    response.headers["X-Cache"] = "REFRESH"
    return {"patient_id": patient_id, "status": "refreshed"}


@connectors_router.get("/connectors", response_model=list[ConnectorStatus])
async def get_connectors() -> list[dict[str, object]]:
    # Live registry + real per-connector health probe (API-05). Replaces the static
    # STATIC_CONNECTORS list, so newly-registered connectors (pdf, hl7v2,
    # institution-a/-b) self-advertise and the reported health is real, not hardcoded.
    return await list_connector_status()


@evidence_router.get("/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> dict[str, object]:
    # Resolve the persistent evidence_card store FIRST, then fall back to the curated
    # static cards. This deliberately mirrors the verifier's precedence in
    # _build_packet_body (``computed_mirror.get(ref) or get_evidence_card(ref)``), so
    # the body the UI renders for a citation chip is the SAME body the
    # anti-hallucination gate validated — never a curated card that happens to share
    # an id with a freshly computed one (citation-provenance integrity, API-03).
    # Without this DB lookup a computed card the reasoning core produced would 404 in
    # the UI even though it passed the verifier. The persisted ``body`` is the same
    # {id, source, snippet, ref_url} shape as a static card (the internal ``kind``
    # column is not part of ``body``), so the response stays byte-identical across
    # both paths.
    #
    # repo.get_evidence_card also writes the per-read audit event (CACHE-03), so a
    # resolved read — computed OR curated — is logged; a genuine miss (both stores
    # empty) rolls back with the 404, matching the repo's not-found convention
    # (confirm/dismiss likewise skip auditing a not-found).
    #
    # actor=subject is the authenticated token subject (API-07). Known limitation:
    # evidence ids are a GLOBAL namespace (the static store scans all patients; a DB
    # row is keyed by the bare id), so an id shared across patients resolves to a
    # single body — patient-scoped evidence resolution is a tracked follow-up.
    row = await repo.get_evidence_card(db, evidence_id=evidence_id, actor=subject)
    if row is not None and isinstance(row.body, dict):
        return row.body
    static_card = get_evidence_card(evidence_id)
    if static_card is not None:
        return static_card
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")


@audit_router.get("/audit")
async def get_audit(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict[str, object]]:
    """Read the immutable audit log, newest first (API-05)."""
    events = await repo.list_audit_events(db, limit=limit)
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "patient_id": event.patient_id,
            "resource_ref": event.resource_ref,
            "actor": event.actor,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        }
        for event in events
    ]
