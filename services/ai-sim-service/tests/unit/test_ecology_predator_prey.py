"""Dinâmica trófica emergente: predador-presa observável e limitado (RF-032)."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from pathlib import Path

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.ecology import simulate_ecology
from ecosfera_ai.simulation_engine.biology.genome import (
    TROPHIC_HERBIVORE,
    TROPHIC_PREDATOR,
    TROPHIC_PRODUCER,
    Genome,
)
from ecosfera_ai.simulation_engine.params import load_params

PARAMS = load_params(Path("configs/simulation_params.yaml"))
CAPACITY = 100.0


def _species(species_id: str, trophic: int, population: float) -> SpeciesRecord:
    return SpeciesRecord(
        species_id=species_id,
        planet_id="p",
        genome=Genome(
            temp_optimum=15.0,
            temp_tolerance=15.0,
            water_need=0.2,
            size=0.5,
            metabolism=0.5,
            trophic_level=float(trophic),
        ),
        emerged_era=1,
        population=population,
        fitness=0.8,
    )


def _food_web() -> list[SpeciesRecord]:
    return [
        _species("plant", TROPHIC_PRODUCER, 40.0),
        _species("herbivore", TROPHIC_HERBIVORE, 8.0),
        _species("predator", TROPHIC_PREDATOR, 2.0),
    ]


def test_predator_prey_oscillations_emerge_and_are_observable() -> None:
    """As oscilações não são roteirizadas: emergem das regras locais dos agentes."""
    params = replace(PARAMS.ecology, steps=40, max_steps=60, demographic_noise=0.0)
    outcome = simulate_ecology(_food_web(), CAPACITY, params, seed=7)

    herbivores = [step["herbivore"] for step in outcome.history]
    # Sobe e desce ao longo da série: há dinâmica, não crescimento monotônico.
    rises = any(b > a for a, b in pairwise(herbivores))
    falls = any(b < a for a, b in pairwise(herbivores))
    assert rises and falls, "esperada oscilação na população de herbívoros"


def test_predation_couples_the_trophic_levels() -> None:
    """Sem predadores, a presa termina a era mais numerosa — o acoplamento existe."""
    params = replace(PARAMS.ecology, steps=25, max_steps=40, demographic_noise=0.0)
    with_predator = simulate_ecology(_food_web(), CAPACITY, params, seed=3)
    without_predator = simulate_ecology(_food_web()[:2], CAPACITY, params, seed=3)

    assert without_predator.population_of("herbivore") > with_predator.population_of("herbivore")


def test_populations_never_go_negative() -> None:
    params = replace(PARAMS.ecology, steps=50, max_steps=60)
    outcome = simulate_ecology(_food_web(), CAPACITY, params, seed=1)
    for step in outcome.history:
        assert all(value >= 0.0 for value in step.values())
    assert all(snapshot.population >= 0.0 for snapshot in outcome.populations)


def test_producers_respect_the_carrying_capacity() -> None:
    """A capacidade vem da camada determinística; a ecologia não pode estourá-la."""
    params = replace(PARAMS.ecology, steps=60, max_steps=80, demographic_noise=0.0)
    crowded = [_species("plant", TROPHIC_PRODUCER, 5.0)]
    outcome = simulate_ecology(crowded, capacity=20.0, params=params, seed=2)
    # Tolerância pequena: o crescimento logístico converge à capacidade por cima.
    assert outcome.population_of("plant") <= 20.0 * 1.05


def test_ecology_is_reproducible_by_seed() -> None:
    params = replace(PARAMS.ecology, steps=20)
    a = simulate_ecology(_food_web(), CAPACITY, params, seed=99)
    b = simulate_ecology(_food_web(), CAPACITY, params, seed=99)
    c = simulate_ecology(_food_web(), CAPACITY, params, seed=100)
    assert a.history == b.history
    assert a.history != c.history


def test_agent_cap_contains_the_cost() -> None:
    """Teto de agentes: mitigação do risco de custo computacional do Inc 3."""
    many = [_species(f"s{i}", TROPHIC_PRODUCER, 1.0 + i) for i in range(50)]
    params = replace(PARAMS.ecology, max_agents=5, steps=3)
    outcome = simulate_ecology(many, CAPACITY, params, seed=1)
    assert len(outcome.populations) == 5


def test_step_cap_bounds_the_era() -> None:
    params = replace(PARAMS.ecology, steps=999, max_steps=4)
    outcome = simulate_ecology(_food_web(), CAPACITY, params, seed=1)
    assert len(outcome.history) == 4


def test_empty_world_is_handled() -> None:
    outcome = simulate_ecology([], CAPACITY, PARAMS.ecology, seed=1)
    assert outcome.populations == []
    assert outcome.population_of("nobody") == 0.0


def test_collapsing_environment_kills_the_producers() -> None:
    """Capacidade zero: a população decai e acaba cruzando o mínimo viável."""
    params = replace(PARAMS.ecology, steps=40, max_steps=200, demographic_noise=0.0)
    partial = simulate_ecology([_species("plant", TROPHIC_PRODUCER, 10.0)], 0.0, params, seed=1)
    # Decaimento exponencial: já perdeu a maior parte da população em 40 passos...
    assert partial.population_of("plant") < 1.0

    extended = replace(params, steps=150)
    collapsed = simulate_ecology([_species("plant", TROPHIC_PRODUCER, 10.0)], 0.0, extended, seed=1)
    # ...e com tempo suficiente cruza o limiar de viabilidade e some.
    assert collapsed.population_of("plant") == 0.0
