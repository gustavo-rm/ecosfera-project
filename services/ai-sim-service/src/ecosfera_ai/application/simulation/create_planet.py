"""Caso de uso: criar e configurar um planeta (RF-011/012).

Cria o `PlanetState` inicial a partir de uma `PlanetSeed` e dos parâmetros
versionados e grava o primeiro checkpoint. O estado inicial vem de dados
(configs), nunca hardcoded; a semente fixa a reprodutibilidade dos ticks
seguintes (RF-023).
"""

from __future__ import annotations

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.simulation_engine.params import SimulationParams, initial_state
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState
from ecosfera_ai.simulation_engine.timeline import EraCheckpoint


class CreatePlanetUseCase:
    def __init__(self, repo: PlanetRepository, params: SimulationParams) -> None:
        self._repo = repo
        self._params = params

    async def execute(self, seed: PlanetSeed) -> PlanetState:
        state = initial_state(seed, self._params)
        await self._repo.save_checkpoint(state)
        # Gênese: a era 0 ancora a linha do tempo e serve de base ao replay da
        # primeira era avançada (sem ela não haveria de onde rebobinar).
        await self._repo.append_checkpoint(
            EraCheckpoint(
                planet_id=state.planet_id,
                era=0,
                seed=state.seed,
                start_tick=state.tick,
                end_tick=state.tick,
                state=state,
            )
        )
        return state
