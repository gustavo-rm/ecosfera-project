from __future__ import annotations

from fastapi import APIRouter

from ecosfera_ai.interfaces.http.v1 import (
    biology,
    feedback,
    health,
    simulation,
    telemetry,
    timeline,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(feedback.router)
api_router.include_router(telemetry.router)
api_router.include_router(simulation.router)
api_router.include_router(timeline.router)
api_router.include_router(biology.router)
