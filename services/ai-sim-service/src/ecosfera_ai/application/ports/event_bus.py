"""Porta de saída para publicar eventos de domínio (EDA — pub/sub)."""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.domain.telemetry.models import Evidence


class EventBus(Protocol):
    async def publish_evidence(self, evidence: Evidence) -> None: ...
