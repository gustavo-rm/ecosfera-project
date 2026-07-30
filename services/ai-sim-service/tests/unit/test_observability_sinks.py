"""Os quatro pilares como adaptadores: Event Store, métricas, logs e traces."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ecosfera_ai.shared_kernel.engine import PerfSample, TickBudget
from ecosfera_ai.shared_kernel.events import CoreCauseCode, EventEmitter, diagnostic_event
from ecosfera_ai.shared_kernel.observability import (
    CompositeSink,
    InMemoryEventStore,
    NullSink,
    PrometheusMetricsSink,
    StructlogSink,
    configure_tracing,
    span,
    tracing_enabled,
)


def _sample(engine: str = "climate", duration: float = 0.01) -> PerfSample:
    return PerfSample(
        engine_id=engine,
        tick=1,
        era=0,
        duration_s=duration,
        events_emitted=2,
        entities_processed=7,
    )


def _emitter() -> EventEmitter:
    return EventEmitter(engine_id="climate", seed=5, tick=1, era=0)


def test_null_sink_accepts_every_signal_and_keeps_nothing() -> None:
    sink = NullSink()
    sink.record_metrics(_sample())
    sink.emit(_emitter().emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT))
    sink.log("qualquer coisa", engine="climate")


def test_event_store_is_append_only_and_ordered() -> None:
    store = InMemoryEventStore()
    emitter = _emitter()
    first = emitter.emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT)
    second = emitter.emit("Cooled", CoreCauseCode.ENGINE_HEARTBEAT)

    store.emit(first)
    store.emit(second)
    store.record_metrics(_sample())  # métricas têm sink próprio
    store.log("ignorado")

    assert [e.event_id for e in store.events] == [first.event_id, second.event_id]


def test_event_store_separates_the_scientific_and_technical_views() -> None:
    store = InMemoryEventStore()
    emitter = _emitter()
    store.emit(emitter.emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT))
    store.emit(diagnostic_event(emitter, CoreCauseCode.BUDGET_EXCEEDED, {"limit": "events"}))

    assert len(store.scientific_view()) == 1
    assert len(store.technical_view()) == 1
    assert len(store.by_correlation(emitter.correlation_id)) == 2
    assert store.by_correlation("inexistente") == ()


def test_prometheus_sink_records_metrics_and_derives_budget_breaches() -> None:
    from ecosfera_ai.core.observability import engine_budget_exceeded, engine_events_emitted

    sink = PrometheusMetricsSink()
    before = engine_events_emitted.labels(engine="climate")._value.get()
    breaches_before = engine_budget_exceeded.labels(engine="climate", limit="events")._value.get()

    sink.record_metrics(_sample())
    sink.emit(_emitter().emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT))  # não é diagnóstico
    sink.emit(
        diagnostic_event(
            _emitter(), CoreCauseCode.BUDGET_EXCEEDED, {"engine": "climate", "limit": "events"}
        )
    )
    sink.log("ignorado")

    assert engine_events_emitted.labels(engine="climate")._value.get() == before + 2
    assert (
        engine_budget_exceeded.labels(engine="climate", limit="events")._value.get()
        == breaches_before + 1
    )


@dataclass(slots=True)
class _FakeLogger:
    lines: list[tuple[str, str]] = field(default_factory=list)

    def debug(self, message: str, **fields: object) -> None:
        self.lines.append(("debug", message))

    def info(self, message: str, **fields: object) -> None:
        self.lines.append(("info", message))


def test_structlog_sink_projects_events_and_metrics_into_logs() -> None:
    """O log é PROJEÇÃO: ele reescreve o evento, nunca inspeciona estado interno."""
    logger = _FakeLogger()
    sink = StructlogSink(logger)  # type: ignore[arg-type]

    sink.record_metrics(_sample())
    sink.emit(_emitter().emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT))
    sink.log("engines_registered", count=1)

    assert logger.lines == [
        ("debug", "engine_tick"),
        ("info", "domain_event"),
        ("info", "engines_registered"),
    ]


def test_composite_sink_fans_out_in_order() -> None:
    store = InMemoryEventStore()
    logger = _FakeLogger()
    composite = CompositeSink([store, StructlogSink(logger)])  # type: ignore[arg-type,list-item]

    composite.record_metrics(_sample())
    composite.emit(_emitter().emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT))
    composite.log("boot")

    assert len(store.events) == 1
    assert [kind for kind, _ in logger.lines] == ["debug", "info", "info"]


def test_tracing_is_a_no_op_until_enabled() -> None:
    assert tracing_enabled() is False
    with span("engine.tick", engine="climate"):
        pass

    configure_tracing(enabled=True)
    try:
        assert tracing_enabled() is True
        with span("engine.tick", engine="climate"):
            pass
    finally:
        configure_tracing(enabled=False)
    assert tracing_enabled() is False


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        (_sample(duration=10.0), ("duration_s",)),
        (PerfSample("x", 1, 0, 0.0, events_emitted=10_000, entities_processed=0), ("events",)),
        (PerfSample("x", 1, 0, 0.0, events_emitted=0, entities_processed=10**9), ("entities",)),
        (PerfSample("x", 1, 0, 0.0, events_emitted=0, entities_processed=0), ()),
    ],
)
def test_perf_sample_reports_which_ceiling_was_crossed(
    sample: PerfSample, expected: tuple[str, ...]
) -> None:
    assert sample.exceeded(TickBudget()) == expected
