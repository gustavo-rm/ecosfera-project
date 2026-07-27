"""Caso de uso: ingerir um evento de telemetria (RF-071) respeitando consentimento.

MVP: persiste o evento e deriva uma Evidência heurística mínima. Inc 7 substitui a
heurística pela inferência bayesiana (pgmpy) — sem alterar a interface de ingestão.
"""

from __future__ import annotations

from ecosfera_ai.application.ports.event_bus import EventBus
from ecosfera_ai.application.ports.telemetry_repo import TelemetryRepository
from ecosfera_ai.domain.telemetry.models import Evidence, TelemetryEvent


class ConsentRequiredError(Exception):
    """Bloqueio LGPD (RNF-009): evento de menor sem consentimento não é processado."""


class IngestTelemetryUseCase:
    def __init__(self, repo: TelemetryRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    async def execute(self, event: TelemetryEvent) -> Evidence | None:
        if not event.is_processable():
            raise ConsentRequiredError(event.student_id)

        await self._repo.save_event(event)
        evidence = self._derive_evidence(event)
        if evidence is not None:
            await self._repo.save_evidence(evidence)
            await self._bus.publish_evidence(evidence)
        return evidence

    @staticmethod
    def _derive_evidence(event: TelemetryEvent) -> Evidence | None:
        # Heurística mínima do MVP: uma intervenção com trade-off explícito sugere
        # 'systems_thinking'. Substituída pela rede bayesiana no Inc 7.
        if event.action == "intervene" and "tradeoff" in event.payload:
            return Evidence(
                student_id=event.student_id,
                competency_hint="systems_thinking",
                strength=0.4,
                source_action=event.action,
            )
        return None
