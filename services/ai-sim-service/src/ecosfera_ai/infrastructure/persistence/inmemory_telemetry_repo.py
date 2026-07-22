"""Adaptador de persistência em memória (MVP/testes).

Substituível pelo adaptador MongoDB no Inc 1/7 sem tocar no domínio (a porta
TelemetryRepository é o único contrato). Telemetria de alto volume e semi-estruturada
justifica MongoDB (Dossiê §6.3); em memória serve para o walking skeleton e testes.
"""
from __future__ import annotations

from ecosfera_ai.domain.telemetry.models import Evidence, TelemetryEvent


class InMemoryTelemetryRepository:
    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []
        self.evidence: list[Evidence] = []

    async def save_event(self, event: TelemetryEvent) -> None:
        self.events.append(event)

    async def save_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    async def count_events(self) -> int:
        return len(self.events)
