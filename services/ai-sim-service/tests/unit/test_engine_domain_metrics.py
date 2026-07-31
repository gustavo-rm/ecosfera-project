"""Sinks de domínio por Engine (Spec §5.1): métricas como projeção de eventos.

São chamados pelo Planet DEPOIS do tick. O que se verifica aqui é que cada um
conta só os eventos do próprio domínio e ignora todo o resto — inclusive o
diagnóstico técnico, que tem contador próprio.
"""

from __future__ import annotations

import pytest

from ecosfera_ai.core.observability import engine_domain_events
from ecosfera_ai.engines.atmosphere.events import GREENHOUSE_FORCING_CHANGED
from ecosfera_ai.engines.atmosphere.observability import AtmosphereMetricsSink
from ecosfera_ai.engines.climate.events import CLIMATE_THRESHOLD_CROSSED, TEMPERATURE_SHIFT
from ecosfera_ai.engines.climate.observability import ClimateMetricsSink
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION
from ecosfera_ai.engines.geology.observability import GeologyMetricsSink
from ecosfera_ai.shared_kernel.engine import PerfSample
from ecosfera_ai.shared_kernel.events import CoreCauseCode, EventEmitter


def _event(engine: str, event_type: str):
    return EventEmitter(engine_id=engine, seed=1, tick=1, era=0).emit(
        event_type, CoreCauseCode.ENGINE_HEARTBEAT
    )


def _counter(engine: str, event_type: str) -> float:
    return engine_domain_events.labels(engine=engine, event_type=event_type)._value.get()


@pytest.mark.parametrize(
    ("sink", "engine", "event_type"),
    [
        (GeologyMetricsSink(), "geology", VOLCANIC_ERUPTION),
        (AtmosphereMetricsSink(), "atmosphere", GREENHOUSE_FORCING_CHANGED),
        (ClimateMetricsSink(), "climate", TEMPERATURE_SHIFT),
        (ClimateMetricsSink(), "climate", CLIMATE_THRESHOLD_CROSSED),
    ],
)
def test_each_sink_counts_its_own_event(sink, engine: str, event_type: str) -> None:
    before = _counter(engine, event_type)
    sink.emit(_event(engine, event_type))
    assert _counter(engine, event_type) == before + 1


@pytest.mark.parametrize(
    "sink", [GeologyMetricsSink(), AtmosphereMetricsSink(), ClimateMetricsSink()]
)
def test_a_sink_ignores_events_of_other_domains(sink) -> None:
    """Contar evento alheio faria a métrica mentir sobre quem produziu o quê."""
    before = _counter("geology", VOLCANIC_ERUPTION)
    sink.emit(_event("outro", "AlgoDeOutroDominio"))
    if not isinstance(sink, GeologyMetricsSink):
        assert _counter("geology", VOLCANIC_ERUPTION) == before


@pytest.mark.parametrize(
    "sink", [GeologyMetricsSink(), AtmosphereMetricsSink(), ClimateMetricsSink()]
)
def test_the_sinks_delegate_time_and_logs_to_the_generic_pillars(sink) -> None:
    """Tempo e entidades já são medidos por Engine no sink genérico."""
    sink.record_metrics(PerfSample("x", 1, 0, 0.01, 1, 1))
    sink.log("ignorado", campo=1)


def test_the_composition_root_wires_all_three() -> None:
    from ecosfera_ai.interfaces.http.deps import get_observability_sink

    kinds = {type(s).__name__ for s in get_observability_sink().sinks}  # type: ignore[attr-defined]
    assert {"GeologyMetricsSink", "AtmosphereMetricsSink", "ClimateMetricsSink"} <= kinds
