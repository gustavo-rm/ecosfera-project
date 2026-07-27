"""Porta de saída para persistir telemetria/evidência (Repository + Ports&Adapters)."""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.domain.telemetry.models import Evidence, TelemetryEvent


class TelemetryRepository(Protocol):
    async def save_event(self, event: TelemetryEvent) -> None: ...
    async def save_evidence(self, evidence: Evidence) -> None: ...
    async def count_events(self) -> int: ...
