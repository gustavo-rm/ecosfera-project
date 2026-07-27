"""Caso de uso: reconstruir o estado de uma era passada (RF-016/023).

Rebobinar a simulação é reexecutar o motor a partir do checkpoint da era anterior,
reaplicando os eventos registrados. Como o motor é determinístico por semente, a
reconstrução tem de bater EXATAMENTE com o estado gravado na época — e este caso
de uso verifica isso explicitamente (`matches_checkpoint`), transformando o
determinismo (RF-023) numa garantia observável em produção, não só nos testes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.timeline import replay


class EraNotFoundError(Exception):
    """Era inexistente na linha do tempo do planeta (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class ReplayOutcome:
    """Estado reconstruído e o veredito da verificação de determinismo."""

    era: int
    state: PlanetState
    matches_checkpoint: bool


class ReplayStateUseCase:
    def __init__(self, repo: PlanetRepository, orchestrator: TickOrchestrator) -> None:
        self._repo = repo
        self._orchestrator = orchestrator

    async def execute(self, planet_id: str, era: int) -> ReplayOutcome:
        target = await self._repo.load_checkpoint(planet_id, era)
        if target is None:
            raise EraNotFoundError(f"{planet_id}#{era}")

        # A era 0 é a gênese: o próprio checkpoint já é o estado reconstruído.
        base = await self._repo.load_checkpoint(planet_id, era - 1) if era > 0 else None
        if base is None:
            return ReplayOutcome(era=era, state=target.state, matches_checkpoint=True)

        events = await self._repo.load_events(planet_id, base.end_tick, target.end_tick)
        rebuilt = replay(
            base.state,
            events,
            target.end_tick,
            self._orchestrator,
            self._orchestrator.bounds,
        )
        return ReplayOutcome(era=era, state=rebuilt, matches_checkpoint=rebuilt == target.state)
