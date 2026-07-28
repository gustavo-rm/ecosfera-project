"""GUARDA DE FRONTEIRA determinístico × IA (Dossiê §8, GDD §10, ADR 0006).

Este é o teste mais importante do incremento. A regra de ouro do projeto é que a
IA governa o EMERGENTE mas **nunca falsifica a ciência**. Traduzido em código:
ligar ou desligar a biologia não pode mudar um único bit da física, da química,
do clima ou da geologia para a mesma semente.

Se algum dia alguém fizer o motor de evolução escrever no `PlanetState`, é aqui
que a violação aparece.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.simulation.advance_era import AdvanceEraUseCase
from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.application.simulation.evolve_biology import EvolveBiologyUseCase
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.infrastructure.jobs.inline_job_queue import InlineJobQueue
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import InMemoryPlanetRepository
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem

PARAMS = load_params(Path("configs/simulation_params.yaml"))
RULES = build_engine(Path("configs/causal_rules.yaml"))

# Campos governados EXCLUSIVAMENTE pela camada determinística.
DETERMINISTIC_FIELDS = tuple(f.name for f in fields(PlanetState))


async def _run_eras(*, biology_enabled: bool, seed: int, eras: int = 3) -> PlanetState:
    """Avança N eras com a biologia ligada ou desligada e devolve o estado final."""
    repo = InMemoryPlanetRepository()
    orchestrator = build_orchestrator(PARAMS)
    explain = ExplainCausalUseCase(RULES)
    life = LifeSubsystem(PARAMS.life)
    biology = BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)

    queue = InlineJobQueue()
    evolve = EvolveBiologyUseCase(repo, biology, life)

    async def _handler(payload: dict[str, object]) -> dict[str, object]:
        return dict(
            (await evolve.execute(str(payload["planet_id"]), int(payload["era"]))).to_dict()
        )

    queue.register("run_evolution", _handler)

    await CreatePlanetUseCase(repo, PARAMS).execute(PlanetSeed("guard", seed))
    use_case = AdvanceEraUseCase(
        repo,
        orchestrator,
        explain,
        PARAMS.timeline.era_length,
        queue,
        biology_enabled=biology_enabled,
    )
    outcome = None
    for _ in range(eras):
        outcome = await use_case.execute("guard")
    assert outcome is not None
    return outcome.state


@pytest.mark.asyncio
async def test_deterministic_state_is_identical_with_biology_on_and_off() -> None:
    with_biology = await _run_eras(biology_enabled=True, seed=2027)
    without_biology = await _run_eras(biology_enabled=False, seed=2027)

    # Igualdade EXATA campo a campo: a biologia não toca no estado do planeta.
    for name in DETERMINISTIC_FIELDS:
        assert getattr(with_biology, name) == getattr(without_biology, name), (
            f"campo determinístico '{name}' mudou com a biologia ligada — "
            "a fronteira determinístico × IA foi violada"
        )
    assert with_biology == without_biology


@pytest.mark.asyncio
async def test_biology_only_adds_output_never_changes_physics() -> None:
    """Com a biologia ligada há códex; desligada, não — mas o planeta é o mesmo."""
    repo_on = InMemoryPlanetRepository()
    assert await repo_on.load_species("guard") == []

    state_on = await _run_eras(biology_enabled=True, seed=99)
    state_off = await _run_eras(biology_enabled=False, seed=99)
    assert state_on.temperature == state_off.temperature
    assert state_on.co2 == state_off.co2
    assert state_on.biomass == state_off.biomass


def test_carrying_capacity_is_the_only_coupling_point() -> None:
    """`life.py` publica a capacidade; a biologia lê e nunca devolve nada a ele."""
    life = LifeSubsystem(PARAMS.life)
    state = initial_state(PlanetSeed("p", 1), PARAMS)
    capacity = life.carrying_capacity(state)
    assert capacity == PARAMS.life.carrying_capacity * life.habitability(state)

    engine = BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)
    outcome = engine.advance_era([], state, capacity, planet_id="p", era=1)
    # O resultado é puramente biológico: nenhum PlanetState sai daqui.
    assert not hasattr(outcome, "state")
    assert all(record.planet_id == "p" for record in outcome.catalog)
