"""Métricas de domínio do Chemistry Engine (Spec §5.1/§6).

Contadores projetados a partir dos EVENTOS, alimentados por um sink — isto é,
DEPOIS do tick. Se o Engine os incrementasse durante o cálculo, a medição estaria
dentro do caminho determinístico, que é o que o ADR-ARCH-0002 proíbe.
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.chemistry.events import (
    CARBON_FLUX_SHIFT,
    NUTRIENT_DEPLETION,
    OCEAN_ACIDIFICATION,
)
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent

_TRACKED = frozenset({NUTRIENT_DEPLETION, OCEAN_ACIDIFICATION, CARBON_FLUX_SHIFT})


class ChemistryMetricsSink:
    """Projeta os eventos da química em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type in _TRACKED:
            engine_domain_events.labels(engine="chemistry", event_type=event.event_type).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
