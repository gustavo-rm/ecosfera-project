# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Métricas de domínio do Biota Engine provisório (Spec §5.1/§6).

Contadores projetados a partir dos EVENTOS, alimentados por um sink — isto é,
DEPOIS do tick, nunca de dentro de `tick()` (ADR-ARCH-0002).
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.biota.events import ABIOGENESIS, BIOMASS_COLLAPSE
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent

_TRACKED = frozenset({ABIOGENESIS, BIOMASS_COLLAPSE})


class BiotaMetricsSink:
    """Projeta os eventos da biota em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type in _TRACKED:
            engine_domain_events.labels(engine="biota", event_type=event.event_type).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
