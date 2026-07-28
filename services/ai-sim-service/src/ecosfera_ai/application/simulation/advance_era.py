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
from typing import Any

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.ports.job_queue import JobQueue, JobRef
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.evolve_biology import BiologySummary
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError
from ecosfera_ai.domain.feedback.models import CausalExplanation, Observation
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta
from ecosfera_ai.simulation_engine.timeline import (
    EraCheckpoint,
    EventLogEntry,
    detect_milestones,
)

# Nome do job pesado de evolução, compartilhado pelos adaptadores de fila.
JOB_RUN_EVOLUTION = "run_evolution"

# Variáveis observadas que existem apenas na camada emergente. São passadas ao
# MOTOR DE REGRAS já existente (sem LLM) para que a explicação da era cite
# extinção/prosperidade — as regras vivem em configs/causal_rules.yaml.
OBS_EXTINCTION = "extinction"
OBS_BIODIVERSITY = "biodiversity"


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
    # Camada emergente (Inc 3). Com a fila inline, `biology` vem preenchido e a
    # rota responde 200; com ARQ, vem `job` e a rota responde 202 (ADR 0007).
    biology: BiologySummary | None = None
    job: JobRef | None = None


class AdvanceEraUseCase:
    def __init__(
        self,
        repo: PlanetRepository,
        orchestrator: TickOrchestrator,
        explain: ExplainCausalUseCase,
        era_length: int,
        jobs: JobQueue | None = None,
        *,
        biology_enabled: bool = False,
        resolves_inline: bool = True,
    ) -> None:
        self._repo = repo
        self._orchestrator = orchestrator
        self._explain = explain
        self._era_length = era_length
        self._jobs = jobs
        self._biology_enabled = biology_enabled
        self._resolves_inline = resolves_inline

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

        # A biologia roda DEPOIS do checkpoint: ela lê o estado já fechado da era
        # e nunca o altera, o que mantém a camada determinística intacta (ADR 0006).
        biology, job = await self._run_biology(planet_id, era)

        # Observações da era: delta determinístico + sinais biológicos emergentes,
        # ambos narrados pelo MESMO motor de regras (não há LLM aqui).
        observations = state.observe(base)
        observations.extend(_biology_observations(biology))
        explanation = self._explain.execute(planet_id, observations)

        return EraOutcome(
            era=era,
            start_tick=base.tick,
            end_tick=state.tick,
            state=state,
            delta=state.delta_from(base),
            events=events,
            explanation=explanation,
            biology=biology,
            job=job,
        )

    async def _run_biology(
        self, planet_id: str, era: int
    ) -> tuple[BiologySummary | None, JobRef | None]:
        """Despacha a evolução pela porta `JobQueue`, resolvendo conforme o backend."""
        if not self._biology_enabled or self._jobs is None:
            return None, None

        ref = await self._jobs.enqueue(JOB_RUN_EVOLUTION, {"planet_id": planet_id, "era": era})
        if not self._resolves_inline:
            # Backend assíncrono: o cliente recebe 202 + referência do job.
            return None, ref

        status = await self._jobs.get_status(ref.job_id)
        if status is None or status.result is None:
            return None, ref
        return _summary_from(status.result), None


def _summary_from(result: dict[str, Any]) -> BiologySummary:
    """Reidrata o resumo biológico devolvido pelo job (inline ou ARQ)."""
    return BiologySummary(
        era=int(result.get("era", 0)),
        speciated=[str(s) for s in result.get("speciated", [])],
        extinct=[str(s) for s in result.get("extinct", [])],
        living=int(result.get("living", 0)),
        generations=int(result.get("generations", 0)),
    )


def _biology_observations(biology: BiologySummary | None) -> list[Observation]:
    """Traduz o resultado biológico em observações para o motor de regras.

    O sinal é a DIREÇÃO da mudança (houve extinção? a biodiversidade subiu ou
    caiu?), que é o que as regras causais em YAML consomem — mesma interface das
    observações físicas, sem nenhum caminho especial no motor de feedback.
    """
    if biology is None:
        return []
    observations: list[Observation] = []
    if biology.extinct:
        observations.append(Observation(variable=OBS_EXTINCTION, delta=float(len(biology.extinct))))
    net = len(biology.speciated) - len(biology.extinct)
    if net != 0:
        observations.append(Observation(variable=OBS_BIODIVERSITY, delta=float(net)))
    return observations
