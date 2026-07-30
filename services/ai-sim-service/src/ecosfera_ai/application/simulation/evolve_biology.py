"""Caso de uso: rodar a biologia emergente de uma era (RF-031/032).

É o trabalho pesado do Inc 3 e o corpo do job `run_evolution`. Fica isolado num
caso de uso próprio justamente para que os DOIS backends de fila — inline e ARQ —
executem exatamente o mesmo código: o adaptador só muda ONDE ele roda, nunca O
QUE ele faz (ADR 0007).

Persiste o códex atualizado e registra especiações/extinções no event log
append-only, de onde o replay e o feedback causal os leem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError
from ecosfera_ai.core.observability import (
    biology_extinctions,
    biology_generations,
    biology_speciations,
)
from ecosfera_ai.simulation_engine.biology.codex import (
    EVENT_EXTINCTION,
    EVENT_SPECIATION,
    SpeciesRecord,
)
from ecosfera_ai.simulation_engine.biology.engine import BiologyEngine, BiologyOutcome
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem
from ecosfera_ai.simulation_engine.timeline import EventLogEntry


class SpeciesNotFoundError(Exception):
    """Espécie inexistente no códex do planeta (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class BiologySummary:
    """Resumo serializável do resultado biológico (também é o payload do job)."""

    era: int
    speciated: list[str]
    extinct: list[str]
    living: int
    generations: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "era": self.era,
            "speciated": list(self.speciated),
            "extinct": list(self.extinct),
            "living": self.living,
            "generations": self.generations,
        }


def biology_events(outcome: BiologyOutcome, planet_id: str, tick: int) -> list[EventLogEntry]:
    """Traduz especiações/extinções em entradas do event log append-only."""
    entries = [
        EventLogEntry(
            planet_id=planet_id,
            tick=tick,
            event_type=EVENT_SPECIATION,
            payload={"species_id": record.species_id, "fitness": record.fitness},
        )
        for record in outcome.speciated
    ]
    entries.extend(
        EventLogEntry(
            planet_id=planet_id,
            tick=tick,
            event_type=EVENT_EXTINCTION,
            payload={"species_id": record.species_id, "fitness": record.fitness},
        )
        for record in outcome.extinct
    )
    return entries


class EvolveBiologyUseCase:
    def __init__(
        self,
        repo: PlanetRepository,
        biology: BiologyEngine,
        life: LifeSubsystem,
    ) -> None:
        self._repo = repo
        self._biology = biology
        self._life = life

    async def execute(self, planet_id: str, era: int) -> BiologySummary:
        """Evolui a biologia da era já fechada e persiste códex + eventos."""
        checkpoint = await self._repo.load_checkpoint(planet_id, era)
        if checkpoint is None:
            raise PlanetNotFoundError(planet_id)

        catalog = await self._repo.load_species(planet_id)
        outcome = self.run(catalog, checkpoint.state, planet_id=planet_id, era=era)

        await self._repo.save_species(outcome.catalog)
        for entry in biology_events(outcome, planet_id, checkpoint.end_tick):
            await self._repo.append_event(entry)

        biology_generations.inc(outcome.generations)
        biology_speciations.inc(len(outcome.speciated))
        biology_extinctions.inc(len(outcome.extinct))

        return BiologySummary(
            era=era,
            speciated=[r.species_id for r in outcome.speciated],
            extinct=[r.species_id for r in outcome.extinct],
            living=len(outcome.living_species),
            generations=outcome.generations,
        )

    def run(
        self,
        catalog: list[SpeciesRecord],
        state: PlanetState,
        *,
        planet_id: str,
        era: int,
    ) -> BiologyOutcome:
        """Executa a biologia da era SEM I/O — reutilizado pelo replay (RF-016)."""
        capacity = self._life.carrying_capacity(state)
        return self._biology.advance_era(catalog, state, capacity, planet_id=planet_id, era=era)
