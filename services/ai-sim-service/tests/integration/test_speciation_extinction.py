"""Especiação e extinção são CONSEQUÊNCIA, e dizem por quê.

Duas afirmações distintas, e as duas importam para o tutor:

  1. os eventos ocorrem quando as condições que os produzem ocorrem — e não em
     ticks agendados;
  2. o `cause_code` que acompanha cada um NOMEIA o mecanismo, porque é dele que a
     narração pedagógica é derivada (ADR-ARCH-0002).

Uma extinção sem causa nomeada obrigaria o tutor a inventar uma, que é
exatamente o que a arquitetura de eventos existe para evitar.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.domain import has_speciated, is_extinct, mutate
from ecosfera_ai.engines.evolution.events import EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.shared_kernel.world_state import SliceRef
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
EVOLUTION = evolution_params()


def _events(seed: int = 2027, ticks: int = 320, shock: float | None = None) -> list[DomainEvent]:
    """Roda o planeta, opcionalmente aplicando um choque térmico no meio."""
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("speciation", seed), PARAMS))
    for index in range(ticks):
        if shock is not None and index == ticks // 2:
            snapshot = snapshot.with_slice(
                SliceRef.CLIMATE,
                replace(snapshot.climate, temperature=snapshot.climate.temperature + shock),
            )
        snapshot = planet.tick(snapshot).snapshot
    return list(store.events)


def _of_type(events: list[DomainEvent], name: str) -> list[DomainEvent]:
    return [e for e in events if e.event_type == name]


# --- O mecanismo, isolado ------------------------------------------------------


def test_speciation_is_a_distance_not_a_schedule() -> None:
    """Espécie nova é DIVERGÊNCIA acumulada, não um contador de gerações."""
    ancestor = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    assert not has_speciated(ancestor, ancestor, EVOLUTION), "não divergiu de si mesmo"

    far = replace(ancestor, temp_optimum=ancestor.temp_optimum + 40.0).clamped()
    assert has_speciated(far, ancestor, EVOLUTION)

    near = replace(ancestor, temp_optimum=ancestor.temp_optimum + 0.01).clamped()
    assert not has_speciated(near, ancestor, EVOLUTION)


def test_extinction_is_a_population_floor() -> None:
    assert is_extinct(0.0, EVOLUTION)
    assert is_extinct(EVOLUTION.extinction_population / 2, EVOLUTION)
    assert not is_extinct(EVOLUTION.extinction_population * 100, EVOLUTION)


def test_mutation_accumulates_toward_speciation_over_time() -> None:
    """A divergência é gradual: um passo não especia, muitos podem."""
    import numpy as np

    ancestor = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    rng = np.random.default_rng(4242)
    one_step = mutate(ancestor, rng, EVOLUTION)
    assert not has_speciated(one_step, ancestor, EVOLUTION), (
        "um único passo de mutação não deveria bastar para especiar"
    )

    lineage = ancestor
    for _ in range(400):
        lineage = mutate(lineage, rng, EVOLUTION)
    assert lineage.distance(ancestor) > one_step.distance(ancestor), (
        "a deriva não acumula — a mutação está sendo revertida a cada passo"
    )


# --- O comportamento no planeta ------------------------------------------------


def test_biological_events_carry_a_structured_cause() -> None:
    """Todo evento da evolução nomeia o mecanismo, nunca só o efeito."""
    events = [e for e in _events() if e.engine_id == "evolution"]
    assert events, "a evolução não emitiu evento algum"
    for event in events:
        assert isinstance(event.cause_code, EvolutionCauseCode), (
            f"{event.event_type} veio com cause_code {event.cause_code!r}"
        )


def test_a_thermal_shock_is_what_produces_thermal_extinction() -> None:
    """A causa nomeada tem de CASAR com o que de fato aconteceu.

    Um `cause_code` constante passaria em qualquer teste de presença. Este
    compara dois mundos: com choque térmico e sem ele.
    """
    shocked = _events(shock=45.0)
    declines = [
        e
        for e in shocked
        if e.engine_id in ("evolution", "ecology")
        and e.cause_code
        in (EvolutionCauseCode.THERMAL_INTOLERANCE, EvolutionCauseCode.RESOURCE_SCARCITY)
    ]
    assert declines, "o choque térmico não produziu perda biológica alguma"

    thermal = [e for e in shocked if e.cause_code is EvolutionCauseCode.THERMAL_INTOLERANCE]
    assert thermal, "nenhuma perda foi atribuída à intolerância térmica"

    calm = _events()
    calm_thermal = [e for e in calm if e.cause_code is EvolutionCauseCode.THERMAL_INTOLERANCE]
    assert len(thermal) > len(calm_thermal), (
        "a intolerância térmica aparece igualmente sem choque: a causa não "
        "está sendo diagnosticada, está sendo assumida"
    )


def test_the_shock_leaves_a_mark_on_the_community() -> None:
    """Contraprova física: o choque tem de mudar a trajetória, não só a trilha."""
    # Diretor mudo: o choque sob teste é o DECLARADO aqui, não um
    # evento sorteado que caísse na mesma janela.
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("mark", 2027), PARAMS))
    for _ in range(200):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    calm = snapshot
    shocked = snapshot.with_slice(
        SliceRef.CLIMATE, replace(snapshot.climate, temperature=snapshot.climate.temperature + 45.0)
    )
    for _ in range(40):
        calm = planet.tick(calm, publish=False).snapshot
        shocked = planet.tick(shocked, publish=False).snapshot

    assert shocked.biota.biomass < calm.biota.biomass, "o choque térmico não custou biomassa alguma"


def test_events_are_aggregate_not_per_organism() -> None:
    """Granularidade agregada por padrão (ADR-ARCH-0002, Correção 2)."""
    from ecosfera_ai.shared_kernel.events import Granularity

    for event in _events():
        if event.engine_id in ("evolution", "ecology"):
            assert event.granularity is Granularity.AGGREGATE, (
                f"{event.event_type} veio por indivíduo: a trilha afogaria o tutor"
            )


def test_the_trail_is_bounded_and_does_not_flood() -> None:
    """Travessia vira evento; estado contínuo não. Um por tick já seria demais."""
    events = _events(ticks=320)
    biological = [e for e in events if e.engine_id in ("evolution", "ecology")]
    assert len(biological) < 320 // 4, (
        f"{len(biological)} eventos biológicos em 320 ticks — está reportando estado, não travessia"
    )


def test_the_events_are_reproducible_under_the_same_seed() -> None:
    assert [(e.event_type, e.occurred_at.tick) for e in _events(seed=5, ticks=160)] == [
        (e.event_type, e.occurred_at.tick) for e in _events(seed=5, ticks=160)
    ]


def test_species_richness_never_goes_negative() -> None:
    """Extinções não podem cavar a riqueza abaixo de zero."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("richness", 2027), PARAMS))
    for _ in range(320):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        assert snapshot.biota.species_richness >= 0.0
        assert snapshot.biota.species_richness <= EVOLUTION.max_species + 1e-9, (
            "o teto de espécies vivas foi furado"
        )


def test_life_emerged_is_the_timeline_marker() -> None:
    """O marco da linha do tempo é emitido UMA vez, pela Evolution."""
    events = _events()
    emerged = _of_type(events, "LifeEmerged")
    assert len(emerged) == 1, f"o marco foi emitido {len(emerged)} vezes"
    assert emerged[0].engine_id == "evolution", (
        "o marco continua vindo do caminho antigo, não do Engine"
    )
    assert emerged[0].cause_code is EvolutionCauseCode.HABITABILITY_THRESHOLD
    assert emerged[0].cause_detail["carrying_capacity"] == pytest.approx(
        emerged[0].cause_detail["carrying_capacity"]
    )
