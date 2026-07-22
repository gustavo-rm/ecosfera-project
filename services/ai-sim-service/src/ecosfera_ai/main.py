"""Fábrica da aplicação FastAPI (ai-sim-service)."""
from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from ecosfera_ai import __version__
from ecosfera_ai.config.settings import get_settings
from ecosfera_ai.core.errors import register_exception_handlers
from ecosfera_ai.core.logging import configure_logging
from ecosfera_ai.interfaces.http.v1.router import api_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    app = FastAPI(
        title="ECOSFERA — ai-sim-service",
        version=__version__,
        description="Serviço de simulação científica e IA (fronteira determinístico × IA).",
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
