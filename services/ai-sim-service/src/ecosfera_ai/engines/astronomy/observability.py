"""Métricas de domínio do Astronomy Engine (Spec §5.1/§6).

Contadores projetados a partir dos EVENTOS, alimentados por um sink — isto é,
DEPOIS do tick, nunca de dentro de `tick()` (ADR-ARCH-0002).
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.astronomy.events import INSOLATION_SHIFT
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent


class AstronomyMetricsSink:
    """Projeta os eventos orbitais em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type == INSOLATION_SHIFT:
            engine_domain_events.labels(engine="astronomy", event_type=INSOLATION_SHIFT).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
