"""Handlers de erro no formato RFC 7807 (Problem Details), coerente com o Dossiê §5."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ecosfera_ai.application.simulation.replay_state import EraNotFoundError
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError
from ecosfera_ai.application.telemetry.ingest_event import ConsentRequiredError

_CT = "application/problem+json"


def _problem(status: int, title: str, detail: str, type_: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type=_CT,
        content={
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            422,
            "Dados inválidos",
            str(exc.errors()),
            "/errors/validation",
            str(request.url.path),
        )

    @app.exception_handler(ConsentRequiredError)
    async def _consent(request: Request, exc: ConsentRequiredError) -> JSONResponse:
        return _problem(
            403,
            "Consentimento ausente",
            "Sem consentimento do responsável, dados do menor não são processados (RNF-009).",
            "/errors/consent-required",
            str(request.url.path),
        )

    @app.exception_handler(PlanetNotFoundError)
    async def _planet_not_found(request: Request, exc: PlanetNotFoundError) -> JSONResponse:
        return _problem(
            404,
            "Planeta não encontrado",
            f"Nenhum planeta com id '{exc}' foi encontrado.",
            "/errors/planet-not-found",
            str(request.url.path),
        )

    @app.exception_handler(EraNotFoundError)
    async def _era_not_found(request: Request, exc: EraNotFoundError) -> JSONResponse:
        return _problem(
            404,
            "Era não encontrada",
            f"A era '{exc}' não existe na linha do tempo deste planeta.",
            "/errors/era-not-found",
            str(request.url.path),
        )
