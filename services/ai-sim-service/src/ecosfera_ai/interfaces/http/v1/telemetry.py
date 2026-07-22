from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ecosfera_ai.application.telemetry.ingest_event import IngestTelemetryUseCase
from ecosfera_ai.core.observability import telemetry_events
from ecosfera_ai.domain.telemetry.models import TelemetryEvent
from ecosfera_ai.interfaces.http.deps import get_ingest_use_case
from ecosfera_ai.interfaces.http.schemas.telemetry import EvidenceOut, TelemetryEventIn

router = APIRouter(prefix="/assessment", tags=["assessment"])


@router.post("/events", status_code=202)
async def ingest_event(
    body: TelemetryEventIn,
    response: Response,
    uc: IngestTelemetryUseCase = Depends(get_ingest_use_case),
) -> EvidenceOut | dict[str, str]:
    """Ingesta de telemetria (RF-071). 202 Accepted — processamento assíncrono (EDA)."""
    event = TelemetryEvent(
        student_id=body.student_id,
        planet_id=body.planet_id,
        action=body.action,
        payload=body.payload,
        consent=body.consent,
    )
    evidence = await uc.execute(event)  # ConsentRequiredError -> 403 (handler)
    telemetry_events.labels(processed="true").inc()
    if evidence is None:
        return {"status": "accepted"}
    return EvidenceOut(
        student_id=evidence.student_id,
        competency_hint=evidence.competency_hint,
        strength=evidence.strength,
        source_action=evidence.source_action,
    )
