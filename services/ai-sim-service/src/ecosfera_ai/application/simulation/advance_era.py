"""Caso de uso: avançar uma era completa da simulação (RF-013/014/016).

Uma era é um bloco de `era_length` ticks determinísticos. Ao fim dela grava-se um
**checkpoint append-only** e as entradas do **log de eventos** (marcos observados
durante o percurso), que juntos permitem reconstruir a era depois (Dossiê §9).

A explicação causal do delta AGREGADO da era reutiliza o `ExplainCausalUseCase`
já existente — o motor de regras é o mesmo de `/ai/explain` e do tick fino; aqui
só muda a janela de observação (uma era em vez de um tick).
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError
from ecosfera_ai.domain.feedback.models import CausalExplanation
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta
from ecosfera_ai.simulation_engine.timeline import (
    EraCheckpoint,
    EventLogEntry,
    detect_milestones,
)


@dataclass(frozen=True, slots=True)
class EraOutcome:
    """Resultado de uma era: estado final, delta agregado, marcos e explicação."""

    era: int
    start_tick: int
    end_tick: int
    state: PlanetState
    delta: StateDelta
    events: list[EventLogEntry]
    explanation: CausalExplanation


class AdvanceEraUseCase:
    def __init__(
        self,
        repo: PlanetRepository,
        orchestrator: TickOrchestrator,
        explain: ExplainCausalUseCase,
        era_length: int,
    ) -> None:
        self._repo = repo
        self._orchestrator = orchestrator
        self._explain = explain
        self._era_length = era_length

    async def execute(self, planet_id: str) -> EraOutcome:
        base = await self._repo.load_latest(planet_id)
        if base is None:
            raise PlanetNotFoundError(planet_id)

        timeline = await self._repo.get_timeline(planet_id)
        era = (max(entry.era for entry in timeline) + 1) if timeline else 1

        state = base
        events: list[EventLogEntry] = []
        for _ in range(self._era_length):
            previous = state
            state = self._orchestrator.tick(state).state
            events.extend(detect_milestones(planet_id, previous, state))

        checkpoint = EraCheckpoint(
            planet_id=planet_id,
            era=era,
            seed=state.seed,
            start_tick=base.tick,
            end_tick=state.tick,
            state=state,
        )
        for entry in events:
            await self._repo.append_event(entry)
        await self._repo.append_checkpoint(checkpoint)
        await self._repo.save_checkpoint(state)

        # Observações da era inteira: delta agregado entre o início e o fim.
        explanation = self._explain.execute(planet_id, state.observe(base))
        return EraOutcome(
            era=era,
            start_tick=base.tick,
            end_tick=state.tick,
            state=state,
            delta=state.delta_from(base),
            events=events,
            explanation=explanation,
        )
