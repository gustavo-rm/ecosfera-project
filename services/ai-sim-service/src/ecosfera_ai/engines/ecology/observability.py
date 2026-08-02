"""Métricas de domínio do Ecology Engine (Spec §5.1/§6).

Contadores projetados a partir dos EVENTOS, alimentados por um sink — isto é,
DEPOIS do tick, nunca de dentro de `tick()` (ADR-ARCH-0002).
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.ecology.events import POPULATION_DECLINED, TROPHIC_COLLAPSE
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent

_TRACKED = frozenset({POPULATION_DECLINED, TROPHIC_COLLAPSE})


class EcologyMetricsSink:
    """Projeta os eventos da ecologia em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type in _TRACKED:
            engine_domain_events.labels(engine="ecology", event_type=event.event_type).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
