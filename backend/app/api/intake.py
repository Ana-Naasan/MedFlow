from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.cache.store import build_packet
from backend.app.dtos import IntakeRequest, IntakeResponse
from backend.app.fhir.validate import validate_fhir_resource
from backend.app.observability import get_logger, log_partial_fetch
from backend.app.providers import ConnectorNotFound
from backend.app.providers.base import ConnectorError
from backend.app.providers.registry import build as build_connector

intake_router = APIRouter(tags=["intake"], dependencies=[Depends(require_dev_token)])

# Stable resource_type for the per-patient partial-data notice row, so /packet
# can read it back at response time and fold it into DecisionPacket.data_gaps.
FETCH_METADATA_TYPE = "FetchMetadata"

_logger = get_logger(__name__)


async def _get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            yield session


def _with_validation_warnings(
    notice: dict[str, object] | None, source: str, warnings: list[str]
) -> dict[str, object]:
    """Fold boundary-validation warnings into the partial-data notice (creating one
    if the fetch itself was clean) so /packet surfaces dropped resources as data gaps.
    """
    if notice is None:
        notice = {"source": source, "partial": True, "warnings": [], "missing": []}
    existing = notice.get("warnings")
    existing_list = list(existing) if isinstance(existing, list) else []
    return {**notice, "warnings": [*existing_list, *warnings]}


@intake_router.post("/intake", status_code=status.HTTP_201_CREATED)
async def post_intake(
    body: IntakeRequest,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> IntakeResponse:
    patient_id = body.patient_id or str(uuid.uuid4())

    try:
        provider = build_connector(body.connector)
    except ConnectorNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found: {body.connector!r}",
        ) from exc

    try:
        result = await provider.fetch_patient(body.source_patient_id)
    except ConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Connector error: {exc}",
        ) from exc

    # FHIR-01/02: validate each fetched resource against the R4B subset at the trust
    # boundary and persist only the valid ones, so a misbehaving (non-mock) connector
    # can never inject malformed FHIR into the cache / reasoning / citation path. An
    # in-subset resource that FAILS validation is dropped and surfaced as an honest
    # data gap below (never silently read as "none"); an out-of-subset type is an
    # expected projection boundary and is filtered silently. Bodies are persisted RAW
    # here (a Patient still carries name/address/telecom) and minimised at every
    # egress via reasoning_view (see get_patient_citation) — minimise-at-rest is a
    # separate SEC-02 concern, intentionally not part of this validation slice.
    # Provenance spans (e.g. PDF char-offsets) travel alongside the resource, not
    # inside the FHIR body — keyed by "{type}/{id}". Merge the matching span into the
    # persisted body AFTER validation (span is not an R4B field, so it must not be
    # present when model_validate runs), so a DB-resolved citation can render the
    # source-PDF highlight (source_span), matching the seeded demo path.
    span_by_ref = {
        prov.resource_ref: prov.span for prov in result.provenance if isinstance(prov.span, dict)
    }
    resource_count = 0
    validation_warnings: list[str] = []
    for entry in result.bundle.get("entry", []):
        resource = entry.get("resource", {})
        if not isinstance(resource, dict):
            continue
        rtype = resource.get("resourceType")
        rid = resource.get("id")
        if not (rtype and rid):
            continue
        ok, warning = validate_fhir_resource(resource)
        if warning is not None:
            validation_warnings.append(warning)
        if not ok:
            continue
        span = span_by_ref.get(f"{rtype}/{rid}")
        body = {**resource, "span": span} if span is not None else resource
        await repo.upsert_resource(
            db,
            patient_id=patient_id,
            resource_type=rtype,
            resource_id=rid,
            body=body,
            source_provider=provider.id,
        )
        resource_count += 1

    # #73 + FHIR-01/02: surface partial-fetch AND validation-drop signals as one
    # honest notice that /packet folds into data_gaps. log_partial_fetch returns None
    # on a complete, fully-valid fetch — then a stale notice is cleared (#91).
    notice = log_partial_fetch(_logger, result)
    if validation_warnings:
        _logger.warning(
            "intake dropped %d invalid resource(s) from %s",
            len(validation_warnings),
            provider.id,
            extra={"context": {"warnings": validation_warnings}},
        )
        notice = _with_validation_warnings(notice, provider.id, validation_warnings)
    if notice is not None:
        await repo.upsert_resource(
            db,
            patient_id=patient_id,
            resource_type=FETCH_METADATA_TYPE,
            resource_id=patient_id,
            body=notice,
            source_provider=provider.id,
        )
    else:
        # #91: a clean fetch must CLEAR any stale partial-data notice from a prior
        # partial fetch, so /packet stops surfacing 'missing data' once the source
        # recovers. FetchMetadata is authoritative per intake — no-op if absent.
        await repo.delete_resource(
            db,
            patient_id=patient_id,
            resource_type=FETCH_METADATA_TYPE,
            resource_id=patient_id,
        )

    packet = build_packet(patient_id)
    hypothesis_ids: list[str] = []
    for hyp in packet.hypotheses:
        # Deterministic id (patient + packet hypothesis id) so re-running intake
        # for the same patient updates the row instead of minting a duplicate.
        hyp_id = f"{patient_id}:{hyp.id}"
        await repo.upsert_hypothesis(
            db,
            id=hyp_id,
            patient_id=patient_id,
            title=hyp.title,
            group=hyp.group,
        )
        hypothesis_ids.append(hyp_id)

    await repo.write_audit_event(
        db,
        event_type="intake_registered",
        resource_ref=f"patient/{patient_id}",
        actor=subject,
        patient_id=patient_id,
    )

    return IntakeResponse(
        patient_id=patient_id,
        status="registered",
        resource_count=resource_count,
        hypothesis_ids=hypothesis_ids,
    )
