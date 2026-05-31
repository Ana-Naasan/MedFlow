from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.cache.store import build_packet
from backend.app.dtos import IntakeRequest, IntakeResponse
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


@intake_router.post("/intake", status_code=status.HTTP_201_CREATED)
async def post_intake(
    body: IntakeRequest,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
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

    # #73: surface partial-data signals. log_partial_fetch returns None on a
    # complete fetch — only persist when there's something honest to surface.
    notice = log_partial_fetch(_logger, result)
    if notice is not None:
        await repo.upsert_resource(
            db,
            patient_id=patient_id,
            resource_type=FETCH_METADATA_TYPE,
            resource_id=patient_id,
            body=notice,
            source_provider=provider.id,
        )

    resource_count = 0
    for entry in result.bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")
        rid = resource.get("id")
        if rtype and rid:
            await repo.upsert_resource(
                db,
                patient_id=patient_id,
                resource_type=rtype,
                resource_id=rid,
                body=resource,
                source_provider=provider.id,
            )
            resource_count += 1

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
        actor="api",
        patient_id=patient_id,
    )

    return IntakeResponse(
        patient_id=patient_id,
        status="registered",
        resource_count=resource_count,
        hypothesis_ids=hypothesis_ids,
    )
