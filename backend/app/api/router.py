from fastapi import APIRouter

from backend.app.api.health import router as health_router
from backend.app.api.packet import router as packet_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(packet_router)
