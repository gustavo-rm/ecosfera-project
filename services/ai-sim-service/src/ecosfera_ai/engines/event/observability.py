"""Métricas de domínio do Event Engine (Spec §5.1/§6).

Contadores projetados a partir dos EVENTOS, alimentados por um sink — isto é,
DEPOIS do tick, nunca de dentro de `tick()` (ADR-ARCH-0002). Vale sublinhar aqui
porque este é o Engine em que a tentação de realimentar é maior: um Diretor que
lesse estas métricas para "calibrar a tensão" quebraria o replay, já que métrica
é efeito da execução e não entrada dela.
"""

from __future__ import annotations

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.event.events import (
    DROUGHT_BEGAN,
    DROUGHT_ENDED,
    EVENT_FORECAST,
    ICE_AGE_ONSET,
    METEOR_IMPACT,
    STORM_OCCURRED,
    SUPERVOLCANIC_ERUPTION,
    WILDFIRE_IGNITED,
)
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import DomainEvent

_TRACKED = frozenset(
    {
        EVENT_FORECAST,
        METEOR_IMPACT,
        DROUGHT_BEGAN,
        DROUGHT_ENDED,
        WILDFIRE_IGNITED,
        ICE_AGE_ONSET,
        STORM_OCCURRED,
        SUPERVOLCANIC_ERUPTION,
    }
)


class EventMetricsSink:
    """Projeta as ocorrências extraordinárias em contadores Prometheus."""

    def record_metrics(self, sample: PerfSample) -> None:
        del sample

    def emit(self, event: DomainEvent) -> None:
        if event.event_type in _TRACKED:
            engine_domain_events.labels(engine="event", event_type=event.event_type).inc()

    def log(self, message: str, /, **fields: object) -> None:
        del message, fields
