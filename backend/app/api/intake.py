from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.cache.store import build_packet
from backend.app.dtos import IntakeRequest, IntakeResponse
from backend.app.providers import build as build_connector
from backend.app.providers.base import ConnectorError
from backend.app.providers.registry import ConnectorNotFound

intake_router = APIRouter(tags=["intake"], dependencies=[Depends(require_dev_token)])


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
            detail=f"Connector {body.connector!r} not found",
        ) from exc

    try:
        result = await provider.fetch_patient(body.source_patient_id)
    except ConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    bundle = result.bundle
    entries = bundle.get("entry", []) if isinstance(bundle, dict) else []

    resource_count = 0
    for entry in entries:
        resource = entry.get("resource", {}) if isinstance(entry, dict) else {}
        if not isinstance(resource, dict):
            continue
        rtype = resource.get("resourceType")
        rid = resource.get("id")
        if not rtype or not rid:
            continue
        await repo.upsert_resource(
            db,
            patient_id=patient_id,
            resource_type=rtype,
            resource_id=str(rid),
            body=resource,
            source_provider=body.connector,
        )
        resource_count += 1

    # Ensure at least one row exists so the patient appears in GET /patients.
    if resource_count == 0:
        await repo.upsert_resource(
            db,
            patient_id=patient_id,
            resource_type="Patient",
            resource_id=patient_id,
            body={"resourceType": "Patient", "id": patient_id},
            source_provider=body.connector,
        )
        resource_count = 1

    # Seed hypotheses from the packet so confirm/dismiss have records to act on.
    packet = build_packet(patient_id)
    hypothesis_ids: list[str] = []
    for hyp in packet.hypotheses:
        hyp_db_id = str(uuid.uuid4())
        await repo.upsert_hypothesis(
            db,
            id=hyp_db_id,
            patient_id=patient_id,
            title=hyp.title,
            group=hyp.group,
        )
        hypothesis_ids.append(hyp_db_id)

    await repo.write_audit_event(
        db,
        event_type="intake_registered",
        resource_ref=f"Patient/{patient_id}",
        actor="intake",
        patient_id=patient_id,
    )

    return IntakeResponse(
        patient_id=patient_id,
        status="registered",
        resource_count=resource_count,
        hypothesis_ids=hypothesis_ids,
    )
