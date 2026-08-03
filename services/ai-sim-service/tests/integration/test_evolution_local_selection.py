"""A seleção é LOCAL: a comunidade rastreia o ambiente, e não um alvo.

O `test_no_global_fitness` audita a FORMA do cálculo. Este arquivo audita o
COMPORTAMENTO: se a média genética realmente segue o ambiente de agora, e se ela
volta a se mover quando o ambiente muda. Um alvo fixo se revelaria aqui — a
média convergiria para ele e pararia, indiferente ao que o planeta fizesse.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.domain import LocalConditions, population_change
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import SliceRef, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
EVOLUTION = evolution_params()


def _trail(seed: int = 2027, ticks: int = 300) -> list[WorldStateSnapshot]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("selection", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return trail


def _alive(trail: list[WorldStateSnapshot]) -> list[WorldStateSnapshot]:
    return [s for s in trail if s.biota.biomass > 0.0]


def test_life_appears_only_when_the_environment_allows_it() -> None:
    """A abiogênese é CONSEQUÊNCIA da capacidade, não um evento agendado."""
    trail = _trail()
    born = next((s for s in trail if s.biota.biomass > 0.0), None)
    assert born is not None, "a vida nunca surgiu"
    assert born.resource.carrying_capacity >= EVOLUTION.abiogenesis_capacity

    before = trail[trail.index(born) - 1]
    assert before.resource.carrying_capacity < EVOLUTION.abiogenesis_capacity, (
        "a vida surgiu num tick em que o limiar já estava vencido antes — "
        "o surgimento não está preso à travessia"
    )


def test_the_mean_optimum_tracks_the_temperature_it_actually_lives_in() -> None:
    """A média genética persegue o ambiente de AGORA, não um valor de projeto."""
    alive = _alive(_trail())
    assert len(alive) > 100

    settled = alive[-60:]
    gaps = [abs(s.biota.mean_temp_optimum - s.climate.temperature) for s in settled]
    assert sum(gaps) / len(gaps) < 12.0, (
        "o ótimo médio não acompanha a temperatura vivida — a seleção deixou de "
        "ser local, ou virou alvo fixo"
    )


def test_the_mean_genome_moves_again_when_the_world_moves() -> None:
    """A prova de que não há alvo: aquecendo o planeta, a média volta a andar.

    Com uma função de aptidão global mirando um ótimo fixo, a média convergiria e
    PARARIA — o planeta poderia ferver que ela não se mexeria.
    """
    # Diretor mudo: o choque sob teste é o DECLARADO aqui, não um
    # evento sorteado que caísse na mesma janela.
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("shift", 2027), PARAMS))
    for _ in range(260):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    assert snapshot.biota.biomass > 0.0, "sem vida, o teste não afirma nada"
    settled = snapshot.biota.mean_temp_optimum

    # Choque térmico imposto de fora, como faria um estudante no simulador.
    shocked = snapshot.with_slice(
        SliceRef.CLIMATE, replace(snapshot.climate, temperature=snapshot.climate.temperature + 25.0)
    )
    for _ in range(200):
        shocked = planet.tick(shocked, publish=False).snapshot

    assert shocked.biota.mean_temp_optimum > settled + 0.5, (
        "o ótimo médio ficou parado depois do choque: a média não rastreia o "
        "ambiente, está presa a um alvo"
    )


def test_a_cohort_off_its_optimum_declines_and_one_at_home_grows() -> None:
    """O mecanismo isolado: o mesmo genoma prospera ou perece pelo AMBIENTE."""
    from ecosfera_ai.simulation_engine.biology.genome import Genome

    cohort = Genome(
        temp_optimum=20.0,
        temp_tolerance=10.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    def conditions(temperature: float) -> LocalConditions:
        return LocalConditions(
            temperature=temperature,
            water_available=0.6,
            energy_available=0.10,
            carrying_capacity=100.0,
            occupied=10.0,
            predation_pressure=0.0,
        )

    at_home = population_change(cohort, 10.0, conditions(20.0), EVOLUTION)
    far_away = population_change(cohort, 10.0, conditions(60.0), EVOLUTION)

    assert at_home > 0.0, "no próprio ótimo a coorte deveria crescer"
    assert far_away < 0.0, "longe do ótimo deveria minguar"


def test_the_engine_is_a_pure_function_of_the_snapshot() -> None:
    """Mesmo snapshot e mesmo contexto ⇒ mesmo delta. É o que o replay exige.

    A semente não é passada ao contexto: ela VEM do snapshot (`ctx.seed`), que é
    justamente o que torna o Engine função pura do estado.
    """
    trail = _trail(ticks=200)
    snapshot = next(s for s in trail if s.biota.biomass > 1.0)

    engine = EvolutionEngine()

    def context() -> TickContext:
        return TickContext(
            snapshot=snapshot,
            rng=rng_for(snapshot.seed, engine.engine_id, snapshot.tick),
            tick=snapshot.tick,
            era=0,
            budget=PARAMS.engine_budget,
        )

    first = engine.tick(context())
    second = engine.tick(context())

    assert first.delta.values == second.delta.values
    assert [e.event_id for e in first.events] == [e.event_id for e in second.events]


def test_predation_pressure_costs_the_community() -> None:
    """O acoplamento de volta existe: mais predação, menos excedente."""
    from ecosfera_ai.simulation_engine.biology.genome import Genome

    cohort = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    def with_pressure(pressure: float) -> float:
        return population_change(
            cohort,
            10.0,
            LocalConditions(
                temperature=20.0,
                water_available=0.6,
                energy_available=0.10,
                carrying_capacity=100.0,
                occupied=10.0,
                predation_pressure=pressure,
            ),
            EVOLUTION,
        )

    assert with_pressure(0.8) < with_pressure(0.0)


def test_crowding_is_what_stops_the_growth() -> None:
    """A densidade-dependência é EMERGENTE, não uma logística imposta.

    A biomassa para de crescer porque a lotação corrói o excedente até cruzar
    zero — não porque uma curva a tenha travado num teto.
    """
    from ecosfera_ai.simulation_engine.biology.genome import Genome

    cohort = Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()

    def surplus(occupied: float) -> float:
        return population_change(
            cohort,
            max(occupied, 1e-6),
            LocalConditions(
                temperature=20.0,
                water_available=0.6,
                energy_available=0.10,
                carrying_capacity=100.0,
                occupied=occupied,
                predation_pressure=0.0,
            ),
            EVOLUTION,
        )

    assert surplus(5.0) > 0.0, "com o orçamento vazio, deveria crescer"
    assert surplus(400.0) < 0.0, "com o orçamento estourado, deveria minguar"


def test_the_community_settles_near_the_capacity_without_a_logistic_curve() -> None:
    """Onde o excedente cruza zero é perto da ocupação 1 — por calibração."""
    alive = _alive(_trail(ticks=420))[-120:]
    occupancy = [
        s.biota.biomass / s.resource.carrying_capacity
        for s in alive
        if s.resource.carrying_capacity > 0.0
    ]
    assert occupancy, "sem capacidade publicada não há o que afirmar"
    mean = sum(occupancy) / len(occupancy)
    assert 0.3 < mean < 1.25, f"ocupação média fora da faixa esperada: {mean:.2f}"


def test_the_trajectory_is_reproducible_under_the_same_seed() -> None:
    assert [s.biota.biomass for s in _trail(seed=77, ticks=120)] == [
        s.biota.biomass for s in _trail(seed=77, ticks=120)
    ]


def test_different_seeds_grow_different_communities() -> None:
    one = _trail(seed=11, ticks=200)[-1]
    other = _trail(seed=12, ticks=200)[-1]
    assert one.biota.biomass != pytest.approx(other.biota.biomass, abs=1e-9)
