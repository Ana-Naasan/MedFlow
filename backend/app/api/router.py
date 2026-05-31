from fastapi import APIRouter

from backend.app.api.health import router as health_router
from backend.app.api.hypotheses import hypotheses_router
from backend.app.api.intake import intake_router
from backend.app.api.packet import (
    connectors_router,
    evidence_router,
)
from backend.app.api.packet import (
    router as packet_router,
)

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(packet_router)
api_router.include_router(connectors_router)
api_router.include_router(evidence_router)
api_router.include_router(intake_router)
api_router.include_router(hypotheses_router)
