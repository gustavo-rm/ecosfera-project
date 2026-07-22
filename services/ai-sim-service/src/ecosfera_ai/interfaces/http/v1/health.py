from __future__ import annotations

from fastapi import APIRouter

from ecosfera_ai import __version__
from ecosfera_ai.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    s = get_settings()
    return {"status": "ok", "service": s.app_name, "version": __version__, "env": s.environment}
