"""Custo computacional da camada emergente dentro dos limites (RSK Inc 3).

O risco declarado do Incremento 3 é o ABM explodir em custo. A mitigação está nos
tetos configurados (`max_agents`, `max_steps`) e na agregação por espécie — um
agente por POPULAÇÃO, não por organismo. Este teste transforma essa mitigação em
verificação: no pior caso permitido pela configuração, uma era tem de fechar bem
abaixo do teto de tempo.

O teto é folgado de propósito: o objetivo é pegar regressão de ORDEM DE GRANDEZA
(ex.: alguém trocar a agregação por indivíduos), não medir microdesempenho.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from tests.support import build_orchestrator

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.ecology import simulate_ecology
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))

# Tetos de tempo por operação (segundos), com folga para CI compartilhado.
MAX_ECOLOGY_SECONDS = 2.0
MAX_ERA_SECONDS = 5.0


def _species(index: int, trophic: float) -> SpeciesRecord:
    return SpeciesRecord(
        species_id=f"s{index}",
        planet_id="perf",
        genome=Genome(15.0, 12.0, 0.2, 0.5, 0.5, trophic),
        emerged_era=1,
        population=5.0,
        fitness=0.6,
    )


def test_ecology_at_configured_ceiling_stays_fast() -> None:
    """ABM no pior caso permitido: max_agents espécies por max_steps passos."""
    params = replace(PARAMS.ecology, steps=PARAMS.ecology.max_steps)
    crowd = [_species(i, 1.0 + (i % 3)) for i in range(params.max_agents * 2)]

    started = time.perf_counter()
    outcome = simulate_ecology(crowd, capacity=200.0, params=params, seed=1)
    elapsed = time.perf_counter() - started

    # A agregação por espécie mantém o custo proporcional ao TETO, não à entrada.
    assert len(outcome.populations) == params.max_agents
    assert len(outcome.history) == params.max_steps
    assert elapsed < MAX_ECOLOGY_SECONDS, f"ecologia levou {elapsed:.2f}s"


def test_full_biology_era_stays_within_budget() -> None:
    """Uma era completa (AG + ABM) no orçamento de tempo."""
    orchestrator = build_orchestrator(PARAMS)
    engine = BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)

    state = initial_state(PlanetSeed("perf", 42), PARAMS)
    catalog: list[SpeciesRecord] = []
    for _ in range(PARAMS.timeline.era_length):
        state = orchestrator.tick(state).state

    started = time.perf_counter()
    for era in range(1, 6):
        catalog = engine.advance_era(
            catalog, state, state.carrying_capacity, planet_id="perf", era=era
        ).catalog
    elapsed = time.perf_counter() - started

    assert elapsed < MAX_ERA_SECONDS, f"5 eras de biologia levaram {elapsed:.2f}s"


def test_species_cap_bounds_the_catalog_growth() -> None:
    """O teto de espécies impede o códex de crescer sem limite ao longo das eras."""
    orchestrator = build_orchestrator(PARAMS)
    engine = BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)

    state = initial_state(PlanetSeed("perf", 3), PARAMS)
    catalog: list[SpeciesRecord] = []
    for era in range(1, 16):
        for _ in range(PARAMS.timeline.era_length):
            state = orchestrator.tick(state).state
        outcome = engine.advance_era(
            catalog, state, state.carrying_capacity, planet_id="perf", era=era
        )
        catalog = outcome.catalog
        assert len(outcome.living_species) <= PARAMS.evolution.max_species + 1
