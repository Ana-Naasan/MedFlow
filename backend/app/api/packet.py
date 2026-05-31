from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
    list_connectors,
    list_patient_ids,
)
from backend.app.config import CACHE_TTL_SECONDS
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.pipeline import build_reasoned_packet

# Must match backend.app.api.intake.FETCH_METADATA_TYPE — the resource_type
# used to persist a per-patient partial-data notice (#73). Duplicated here so
# this module doesn't import from /intake (which would create a cycle).
_FETCH_METADATA_TYPE = "FetchMetadata"

router = APIRouter(prefix="/patients", tags=["packet"], dependencies=[Depends(require_dev_token)])
connectors_router = APIRouter(tags=["connectors"], dependencies=[Depends(require_dev_token)])
evidence_router = APIRouter(tags=["evidence"], dependencies=[Depends(require_dev_token)])


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


async def _build_packet_body(patient_id: str) -> dict[str, object]:
    """Build the servable DecisionPacket for a patient.

    Runs the live reasoning pipeline (Gemini → citation gate → cache-authoritative
    verifier); on any abstention it falls back to the static scaffold so the
    result is always citation-safe. This is the production caller for
    ``run_reasoning`` (EVAL-REVIEW BLOCKER #1).
    """
    scaffold = build_packet(patient_id)
    evidence = [
        EvidenceSnippet(
            id=str(card["id"]),
            kind="evidence",
            ref=str(card["id"]),
            label=str(card.get("snippet", "")),
        )
        for card in get_evidence_cards(patient_id)
    ]
    packet = await build_reasoned_packet(
        scaffold,
        get_patient_resources(patient_id),
        evidence,
        resource_lookup=get_patient_resource,
        evidence_lookup=get_evidence_card,
    )
    return packet.model_dump()


@router.get("/{patient_id}/packet")
async def get_packet(
    patient_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    built: dict[str, object] = {}

    async def fetcher() -> dict[str, object]:
        nonlocal built
        built = await _build_packet_body(patient_id)
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
        actor="api",
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
    body = await _merge_partial_data_notice(db, patient_id, body)
    return {**body, "cache_status": cache_status.value}


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
    if not extra_gaps:
        return body
    existing = list(body.get("data_gaps") or [])
    # Preserve order, dedupe — a second /intake on the same partial fetch
    # mustn't accumulate duplicates if the cached packet already has them.
    seen = set(existing)
    for g in extra_gaps:
        if g not in seen:
            existing.append(g)
            seen.add(g)
    return {**body, "data_gaps": existing}


@router.get("/{patient_id}/resource/{resource_type}/{resource_id}")
async def get_patient_citation(
    patient_id: str,
    resource_type: str,
    resource_id: str,
) -> dict[str, object]:
    resource = get_patient_resource(patient_id, resource_type, resource_id)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")
    return resource


@router.post("/{patient_id}/refresh")
async def refresh(
    patient_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    body = await _build_packet_body(patient_id)
    await repo.upsert_resource(
        db,
        patient_id=patient_id,
        resource_type="DecisionPacket",
        resource_id=patient_id,
        body=body,
        source_provider="static",
        ttl_seconds=CACHE_TTL_SECONDS,
    )
    response.headers["X-Cache"] = "REFRESH"
    return {"patient_id": patient_id, "status": "refreshed"}


@connectors_router.get("/connectors")
async def get_connectors() -> list[dict[str, object]]:
    return list_connectors()


@evidence_router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> dict[str, object]:
    evidence = get_evidence_card(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence
