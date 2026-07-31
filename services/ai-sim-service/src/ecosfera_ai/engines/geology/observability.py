"""Métricas de domínio do Geology Engine (Spec §5.1/§6).

Contadores específicos deste domínio, projetados a partir dos EVENTOS. São
alimentados por um sink, isto é, DEPOIS do tick — nunca de dentro de `tick()`.
Se o Engine os incrementasse durante o cálculo, a medição estaria dentro do
caminho determinístico, que é o que o ADR-ARCH-0002 proíbe.
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent


class GeologyMetricsSink:
    """Projeta os eventos da geologia em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample  # tempo/entidades já são cobertos pelo sink genérico

    def emit(self, event: DomainEvent) -> None:
        if event.event_type == VOLCANIC_ERUPTION:
            engine_domain_events.labels(engine="geology", event_type=VOLCANIC_ERUPTION).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
