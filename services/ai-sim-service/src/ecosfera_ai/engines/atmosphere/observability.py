"""Métricas de domínio do Atmosphere Engine (Spec §5.1/§6).

Contadores específicos deste domínio, projetados a partir dos EVENTOS. São
alimentados por um sink, isto é, DEPOIS do tick — nunca de dentro de `tick()`.
Se o Engine os incrementasse durante o cálculo, a medição estaria dentro do
caminho determinístico, que é o que o ADR-ARCH-0002 proíbe.
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.atmosphere.events import GREENHOUSE_FORCING_CHANGED
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent


class AtmosphereMetricsSink:
    """Projeta os eventos da atmosfera em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type == GREENHOUSE_FORCING_CHANGED:
            engine_domain_events.labels(
                engine="atmosphere", event_type=GREENHOUSE_FORCING_CHANGED
            ).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
