"""Barramento no-op (MVP). Inc 1/7 troca por Redis Streams (fan-out simples)."""
from __future__ import annotations

from ecosfera_ai.core.logging import get_logger
from ecosfera_ai.domain.telemetry.models import Evidence

_log = get_logger(__name__)


class NullEventBus:
    async def publish_evidence(self, evidence: Evidence) -> None:
        _log.debug("evidence.published", student=evidence.student_id, hint=evidence.competency_hint)
