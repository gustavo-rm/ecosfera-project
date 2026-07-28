"""Evolução emergente PORÉM reproduzível por semente (RF-023/031)."""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord, living
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine, biology_seed
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem

PARAMS = load_params(Path("configs/simulation_params.yaml"))
LIFE = LifeSubsystem(PARAMS.life)


def _engine() -> BiologyEngine:
    return BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)


def _history(seed: int, eras: int = 5) -> list[tuple[list[str], list[str]]]:
    """Sequência de (especiações, extinções) por era para uma semente."""
    orchestrator = build_orchestrator(PARAMS)
    engine = _engine()
    state = initial_state(PlanetSeed("p", seed), PARAMS)
    catalog: list[SpeciesRecord] = []
    trace: list[tuple[list[str], list[str]]] = []
    for era in range(1, eras + 1):
        for _ in range(PARAMS.timeline.era_length):
            state = orchestrator.tick(state).state
        outcome = engine.advance_era(
            catalog, state, LIFE.carrying_capacity(state), planet_id="p", era=era
        )
        catalog = outcome.catalog
        trace.append(
            ([r.species_id for r in outcome.speciated], [r.species_id for r in outcome.extinct])
        )
    return trace


def test_same_seed_reproduces_the_same_speciation_sequence() -> None:
    # RF-023: o emergente não pode ser imprevisível — só não-roteirizado.
    assert _history(42) == _history(42)


def test_different_seeds_diverge() -> None:
    assert _history(42) != _history(7)


def test_biology_seed_is_stable_and_era_dependent() -> None:
    assert biology_seed(42, 1) == biology_seed(42, 1)
    assert biology_seed(42, 1) != biology_seed(42, 2)
    assert biology_seed(42, 1) != biology_seed(43, 1)


def test_populations_are_reproducible_to_the_last_bit() -> None:
    def final_populations(seed: int) -> list[tuple[str, float]]:
        orchestrator = build_orchestrator(PARAMS)
        engine = _engine()
        state = initial_state(PlanetSeed("p", seed), PARAMS)
        catalog: list[SpeciesRecord] = []
        for era in range(1, 4):
            for _ in range(PARAMS.timeline.era_length):
                state = orchestrator.tick(state).state
            catalog = engine.advance_era(
                catalog, state, LIFE.carrying_capacity(state), planet_id="p", era=era
            ).catalog
        return [(r.species_id, r.population) for r in catalog]

    assert final_populations(11) == final_populations(11)


def test_evolution_does_not_leak_global_random_state() -> None:
    """O DEAP usa o `random` global; a evolução tem de restaurá-lo ao terminar."""
    import random

    random.seed(123)
    before = random.random()

    random.seed(123)
    _history(5, eras=2)
    after = random.random()

    assert before == after


def test_barren_planet_extinguishes_everything() -> None:
    engine = _engine()
    state = initial_state(PlanetSeed("p", 1), PARAMS)
    seeded = [
        SpeciesRecord(
            species_id="s0",
            planet_id="p",
            genome=Genome(20.0, 10.0, 0.1, 0.5, 0.5, 1.0),
            emerged_era=1,
            population=5.0,
            fitness=0.5,
        )
    ]
    # Capacidade zero = ambiente inviável: nada sobrevive.
    outcome = engine.advance_era(seeded, state, 0.0, planet_id="p", era=2)
    assert living(outcome.catalog) == []
    assert [r.species_id for r in outcome.extinct] == ["s0"]


def test_speciation_records_its_ancestor() -> None:
    """A linhagem é o que torna o códex uma árvore filogenética navegável."""
    trace: list[SpeciesRecord] = []
    orchestrator = build_orchestrator(PARAMS)
    engine = _engine()
    state: PlanetState = initial_state(PlanetSeed("p", 2027), PARAMS)
    catalog: list[SpeciesRecord] = []
    for era in range(1, 6):
        for _ in range(PARAMS.timeline.era_length):
            state = orchestrator.tick(state).state
        outcome = engine.advance_era(
            catalog, state, LIFE.carrying_capacity(state), planet_id="p", era=era
        )
        catalog = outcome.catalog
        trace.extend(outcome.speciated)

    descendants = [r for r in trace if r.ancestor_id is not None]
    assert descendants, "esperada ao menos uma espécie com ancestral"
    known = {r.species_id for r in catalog}
    assert all(r.ancestor_id in known for r in descendants)
