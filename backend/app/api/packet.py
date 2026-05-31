from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.cache.store import (
    build_packet,
    get_evidence_card,
    get_patient_resource,
    list_connectors,
    list_patient_ids,
)
from backend.app.config import CACHE_TTL_SECONDS

router = APIRouter(prefix="/patients", tags=["packet"], dependencies=[Depends(require_dev_token)])
connectors_router = APIRouter(tags=["connectors"], dependencies=[Depends(require_dev_token)])
evidence_router = APIRouter(tags=["evidence"], dependencies=[Depends(require_dev_token)])


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            yield session


@router.get("")
async def get_patients(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict[str, str]]:
    db_ids = set(await repo.list_patient_ids_from_db(db))
    static_ids = set(list_patient_ids())
    all_ids = sorted(static_ids | db_ids)
    return [{"id": pid} for pid in all_ids]


@router.get("/{patient_id}/packet")
async def get_packet(
    patient_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    built: dict[str, object] = {}

    async def fetcher() -> dict[str, object]:
        nonlocal built
        built = build_packet(patient_id).model_dump()
        return built

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
    return {**body, "cache_status": cache_status.value}


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
    body = build_packet(patient_id).model_dump()
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
