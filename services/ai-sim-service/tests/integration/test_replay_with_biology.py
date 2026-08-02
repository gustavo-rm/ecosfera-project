"""Replay reconstrói a biologia idêntica ao original (RF-016/023).

O replay NÃO lê o códex persistido: ele reexecuta o motor de evolução/ecologia
era a era, semeado por (semente do planeta, era). Bater com o original é a prova
de que a camada emergente também é reproduzível — e não só a determinística.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.support import build_orchestrator

from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.application.simulation.evolve_biology import EvolveBiologyUseCase
from ecosfera_ai.application.simulation.replay_state import ReplayStateUseCase
from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import InMemoryPlanetRepository
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.params import load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from ecosfera_ai.simulation_engine.timeline import EraCheckpoint

BASE = "/ai/api/v1/simulation"
PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _biology_use_case(repo: InMemoryPlanetRepository) -> EvolveBiologyUseCase:
    engine = BiologyEngine(EvolutionEngine(PARAMS.evolution, PARAMS.fitness), PARAMS.ecology)
    return EvolveBiologyUseCase(repo, engine)


@pytest.mark.asyncio
async def test_replay_rebuilds_the_same_codex() -> None:
    repo = InMemoryPlanetRepository()
    orchestrator = build_orchestrator(PARAMS)
    evolve = _biology_use_case(repo)

    # Trajetória original: 3 eras de física + biologia, tudo persistido.
    state = await CreatePlanetUseCase(repo, PARAMS).execute(PlanetSeed("replay", 777))
    for era in range(1, 4):
        for _ in range(PARAMS.timeline.era_length):
            state = orchestrator.tick(state).state
        await repo.append_checkpoint(
            EraCheckpoint(
                planet_id="replay",
                era=era,
                seed=state.seed,
                start_tick=state.tick - PARAMS.timeline.era_length,
                end_tick=state.tick,
                state=state,
            )
        )
        await repo.save_checkpoint(state)
        await evolve.execute("replay", era)

    original = await repo.load_species("replay")
    assert original, "a trajetória original produziu espécies"

    # Replay: reconstrói do zero, sem consultar o códex gravado.
    rebuilt = await ReplayStateUseCase(repo, orchestrator, _biology_use_case(repo)).execute(
        "replay", 3
    )
    assert rebuilt.matches_checkpoint is True

    def signature(records: list) -> list[tuple]:  # type: ignore[type-arg]
        return sorted(
            (r.species_id, r.emerged_era, r.extinct_era, round(r.population, 9), r.ancestor_id)
            for r in records
        )

    assert signature(rebuilt.species) == signature(original)


@pytest.mark.asyncio
async def test_replay_without_biology_still_rebuilds_physics() -> None:
    """Com a biologia desligada o replay segue funcionando: fronteira preservada."""
    repo = InMemoryPlanetRepository()
    orchestrator = build_orchestrator(PARAMS)
    state = await CreatePlanetUseCase(repo, PARAMS).execute(PlanetSeed("nobio", 5))
    for _ in range(PARAMS.timeline.era_length):
        state = orchestrator.tick(state).state
    await repo.append_checkpoint(EraCheckpoint("nobio", 1, state.seed, 0, state.tick, state))

    outcome = await ReplayStateUseCase(repo, orchestrator, None).execute("nobio", 1)
    assert outcome.matches_checkpoint is True
    assert outcome.species == []


def test_replayed_era_matches_the_live_era_over_http(client: TestClient) -> None:
    planet_id = client.post(f"{BASE}/planets", json={"seed": 8080}).json()["planet_id"]
    live = client.post(f"{BASE}/planets/{planet_id}/advance-era").json()

    rebuilt = client.get(f"{BASE}/planets/{planet_id}/eras/1").json()
    assert rebuilt["matches_checkpoint"] is True
    assert rebuilt["state"] == live["state"]
