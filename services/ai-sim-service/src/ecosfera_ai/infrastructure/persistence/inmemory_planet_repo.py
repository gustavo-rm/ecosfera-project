"""Adaptador de persistência de planetas em memória (MVP/testes).

Guarda o histórico append-only de checkpoints e o log de eventos por planeta
(base para replay, RF-016). Substituível pelo adaptador Postgres via a porta
`PlanetRepository` sem tocar no domínio (ADR 0001/0005). Mantido mesmo com o
Postgres disponível: os testes de unidade rodam sem banco nem container.
"""

from __future__ import annotations

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.timeline import (
    EraCheckpoint,
    EraSummary,
    EventLogEntry,
    summarize,
)


class InMemoryPlanetRepository:
    def __init__(self) -> None:
        self._history: dict[str, list[PlanetState]] = {}
        self._checkpoints: dict[str, list[EraCheckpoint]] = {}
        self._events: dict[str, list[EventLogEntry]] = {}
        self._species: dict[str, dict[str, SpeciesRecord]] = {}

    # --- Estado corrente -------------------------------------------------------
    async def save_checkpoint(self, state: PlanetState) -> None:
        self._history.setdefault(state.planet_id, []).append(state)

    async def load_latest(self, planet_id: str) -> PlanetState | None:
        history = self._history.get(planet_id)
        return history[-1] if history else None

    async def count_checkpoints(self, planet_id: str) -> int:
        """Nº de estados persistidos (append-only) — apoia testes e replay futuro."""
        return len(self._history.get(planet_id, []))

    # --- Linha do tempo --------------------------------------------------------
    async def append_checkpoint(self, checkpoint: EraCheckpoint) -> None:
        self._checkpoints.setdefault(checkpoint.planet_id, []).append(checkpoint)

    async def append_event(self, entry: EventLogEntry) -> None:
        self._events.setdefault(entry.planet_id, []).append(entry)

    async def load_checkpoint(self, planet_id: str, era: int) -> EraCheckpoint | None:
        for checkpoint in self._checkpoints.get(planet_id, []):
            if checkpoint.era == era:
                return checkpoint
        return None

    async def load_events(
        self, planet_id: str, from_tick: int, to_tick: int
    ) -> list[EventLogEntry]:
        return [
            entry for entry in self._events.get(planet_id, []) if from_tick <= entry.tick <= to_tick
        ]

    async def get_timeline(self, planet_id: str) -> list[EraSummary]:
        checkpoints = sorted(self._checkpoints.get(planet_id, []), key=lambda c: c.era)
        counts: dict[int, int] = {}
        for checkpoint in checkpoints:
            counts[checkpoint.era] = sum(
                1
                for entry in self._events.get(planet_id, [])
                if checkpoint.start_tick < entry.tick <= checkpoint.end_tick
            )
        return summarize(checkpoints, counts)

    # --- Códex de espécies (Inc 3) ---------------------------------------------
    async def save_species(self, records: list[SpeciesRecord]) -> None:
        for record in records:
            self._species.setdefault(record.planet_id, {})[record.species_id] = record

    async def load_species(self, planet_id: str) -> list[SpeciesRecord]:
        catalog = self._species.get(planet_id, {})
        return sorted(catalog.values(), key=lambda r: (r.emerged_era, r.species_id))

    async def load_species_by_id(self, planet_id: str, species_id: str) -> SpeciesRecord | None:
        return self._species.get(planet_id, {}).get(species_id)
