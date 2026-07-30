"""Canal B: envelope de evento completo e identificadores determinísticos (Spec §4)."""

from __future__ import annotations

import dataclasses

import pytest

from ecosfera_ai.shared_kernel.events import (
    DIAGNOSTIC_EVENT_TYPE,
    CauseCodeEnum,
    CoreCauseCode,
    DomainEvent,
    EventEmitter,
    Granularity,
    SimulationTime,
    deterministic_id,
    diagnostic_event,
)


# Vocabulário de causa de um Engine hipotético — prova que a base é extensível.
class DemoCauseCode(CauseCodeEnum):
    RESOURCE_SCARCITY = "RESOURCE_SCARCITY"


def _emitter(seed: int = 42, tick: int = 7, era: int = 2) -> EventEmitter:
    return EventEmitter(engine_id="demo", seed=seed, tick=tick, era=era)


def test_envelope_carries_every_field_of_the_spec() -> None:
    """Explicabilidade é requisito de esquema: o evento responde tudo sozinho."""
    event = _emitter().emit(
        "PopulationDeclined",
        DemoCauseCode.RESOURCE_SCARCITY,
        location={"region_id": "norte"},
        participants=["species:Alpha"],
        environmental_factors=["resource:water#low"],
        genes=["gene:tolerancia_termica"],
        resources=["water"],
        cause_detail={"duration_ticks": 5},
        consequences=["event:downstream"],
    )

    present = {f.name for f in dataclasses.fields(event)}
    assert present == {
        "event_id",
        "event_type",
        "engine_id",
        "occurred_at",
        "seed",
        "cause_code",
        "correlation_id",
        "causation_id",
        "location",
        "participants",
        "environmental_factors",
        "genes",
        "resources",
        "cause_detail",
        "consequences",
        "granularity",
    }
    assert event.occurred_at == SimulationTime(tick=7, era=2)
    assert event.granularity is Granularity.AGGREGATE  # agregado por padrão (Corr. 2)


def test_cause_code_must_be_an_enum_never_prose() -> None:
    """A frase pedagógica é do Tutor; o Engine emite código estruturado."""
    with pytest.raises(TypeError, match="CauseCodeEnum"):
        DomainEvent(
            event_id="x",
            event_type="PopulationDeclined",
            engine_id="demo",
            occurred_at=SimulationTime(tick=1, era=1),
            seed=1,
            cause_code="a espécie perdeu população porque faltou água",  # type: ignore[arg-type]
            correlation_id="c",
        )


def test_ids_are_derived_from_seed_tick_and_engine() -> None:
    """Mesma trajetória, mesmos ids: `uuid4` no loop quebraria o replay."""
    first = _emitter().emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)
    second = _emitter().emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)

    assert first.event_id == second.event_id
    assert first.correlation_id == second.correlation_id
    assert first.event_id == deterministic_id(42, 2, 7, "demo", "Speciated", 1)


def test_different_seeds_produce_different_ids() -> None:
    a = _emitter(seed=1).emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)
    b = _emitter(seed=2).emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)
    assert a.event_id != b.event_id
    assert a.correlation_id != b.correlation_id


def test_sequence_disambiguates_events_of_the_same_tick() -> None:
    emitter = _emitter()
    first = emitter.emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)
    second = emitter.emit("Speciated", CoreCauseCode.ENGINE_HEARTBEAT)

    assert first.event_id != second.event_id
    assert first.correlation_id == second.correlation_id  # mesma cadeia causal
    assert emitter.emitted == 2


def test_events_of_the_same_tick_share_the_correlation_id() -> None:
    """É o que permite reconstruir a cadeia causal de um instante (Pilar 4)."""
    geology = EventEmitter(engine_id="geology", seed=9, tick=3, era=1)
    climate = EventEmitter(engine_id="climate", seed=9, tick=3, era=1)
    assert geology.correlation_id == climate.correlation_id


def test_causation_id_links_an_event_to_its_parent() -> None:
    emitter = _emitter()
    cause = emitter.emit("Erupted", CoreCauseCode.ENGINE_HEARTBEAT)
    effect = emitter.emit(
        "PopulationDeclined", DemoCauseCode.RESOURCE_SCARCITY, causation_id=cause.event_id
    )
    assert effect.causation_id == cause.event_id


def test_diagnostic_event_uses_the_same_envelope() -> None:
    """Fonte única de verdade: a visão técnica é projeção, não segundo formato."""
    event = diagnostic_event(
        _emitter(), CoreCauseCode.BUDGET_EXCEEDED, {"engine": "demo", "limit": "duration_s"}
    )
    assert isinstance(event, DomainEvent)
    assert event.event_type == DIAGNOSTIC_EVENT_TYPE
    assert event.is_diagnostic is True


def test_mappings_inside_the_envelope_are_frozen() -> None:
    event = _emitter().emit(
        "Speciated", CoreCauseCode.ENGINE_HEARTBEAT, location={"region_id": "sul"}
    )
    with pytest.raises(TypeError):
        event.location["region_id"] = "norte"  # type: ignore[index]
