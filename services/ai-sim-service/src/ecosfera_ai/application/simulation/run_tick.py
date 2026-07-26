"""Caso de uso: avançar um tick da simulação e explicar o resultado (RF-013/014).

Fecha o core loop do MVP: carrega o último estado -> orquestra o tick
determinístico -> persiste o novo checkpoint -> deriva observações -> REUTILIZA o
motor de feedback causal existente (`ExplainCausalUseCase`) para narrar o delta.
Não duplica lógica de simulação nem de explicação — apenas compõe as peças.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.domain.feedback.models import CausalExplanation
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


class PlanetNotFoundError(Exception):
    """Planeta inexistente: nenhum checkpoint carregado para o id (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class TickOutcome:
    """Saída do caso de uso: novo estado, delta agregado e explicação causal."""

    state: PlanetState
    delta: StateDelta
    explanation: CausalExplanation


class RunTickUseCase:
    def __init__(
        self,
        repo: PlanetRepository,
        orchestrator: TickOrchestrator,
        explain: ExplainCausalUseCase,
    ) -> None:
        self._repo = repo
        self._orchestrator = orchestrator
        self._explain = explain

    async def execute(self, planet_id: str) -> TickOutcome:
        state = await self._repo.load_latest(planet_id)
        if state is None:
            raise PlanetNotFoundError(planet_id)
        result = self._orchestrator.tick(state)
        await self._repo.save_checkpoint(result.state)
        explanation = self._explain.execute(planet_id, result.observations)
        return TickOutcome(state=result.state, delta=result.delta, explanation=explanation)
