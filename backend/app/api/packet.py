from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.app.api.auth import require_dev_token
from backend.app.cache.store import (
    build_packet,
    get_evidence_card,
    get_patient_resource,
    list_connectors,
    list_patient_ids,
    refresh_patient,
)

router = APIRouter(prefix="/patients", tags=["packet"], dependencies=[Depends(require_dev_token)])
connectors_router = APIRouter(tags=["connectors"], dependencies=[Depends(require_dev_token)])
evidence_router = APIRouter(tags=["evidence"], dependencies=[Depends(require_dev_token)])


@router.get("")
async def get_patients() -> list[dict[str, str]]:
    return [{"id": patient_id} for patient_id in list_patient_ids()]


@router.get("/{patient_id}/packet")
async def get_packet(patient_id: str, response: Response) -> dict[str, object]:
    response.headers["X-Cache"] = "HIT"
    return build_packet(patient_id).model_dump()


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
async def refresh(patient_id: str, response: Response) -> dict[str, object]:
    response.headers["X-Cache"] = "REFRESH"
    return refresh_patient(patient_id)


@connectors_router.get("/connectors")
async def get_connectors() -> list[dict[str, object]]:
    return list_connectors()


@evidence_router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> dict[str, object]:
    evidence = get_evidence_card(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence
