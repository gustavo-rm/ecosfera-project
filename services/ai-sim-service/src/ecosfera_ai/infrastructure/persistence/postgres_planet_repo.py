"""Adaptador de persistência de planetas em PostgreSQL (SQLAlchemy 2.0 async).

Implementa a porta `PlanetRepository` sobre três tabelas do schema `simulation`
(ADR 0005):

  - `planets`         — projeção do estado CORRENTE (upsert por planeta);
  - `era_checkpoints` — histórico append-only de eras (nunca sofre UPDATE);
  - `event_log`       — log append-only de eventos (intervenções e marcos).

O estado é gravado como JSONB: o `PlanetState` ganha campos a cada incremento
(física, geologia, oceano...) e um schema colunar exigiria migration a cada
mudança. A leitura ignora chaves desconhecidas e preenche ausentes com o default
da dataclass, de modo que checkpoints antigos continuam legíveis (compatibilidade
para frente e para trás).

Este módulo importa SQLAlchemy no topo de propósito: ele só é carregado pelo
composition root quando o backend Postgres está selecionado, então o serviço sobe
em modo `inmemory` sem o extra `infra` instalado.
"""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.timeline import (
    EraCheckpoint,
    EraSummary,
    EventLogEntry,
)

_STATE_FIELDS: frozenset[str] = frozenset(f.name for f in fields(PlanetState))


def state_to_json(state: PlanetState) -> str:
    """Serializa o estado para JSONB — delegando a forma canônica ao domínio.

    A serialização deixou de morar aqui no M5: export portável, Event Store e
    persistência precisam da MESMA forma, e mantê-la num adaptador faria a
    aplicação depender da infraestrutura para exportar (ADR 0021).
    """
    return json.dumps(state.to_dict())


def state_from_json(raw: Any) -> PlanetState:
    """Reconstrói o estado tolerando chaves desconhecidas (evolução de schema)."""
    data = json.loads(raw) if isinstance(raw, str) else dict(raw)
    return PlanetState.from_dict(data)


def create_engine(database_url: str) -> AsyncEngine:
    """Cria o engine assíncrono (driver asyncpg)."""
    return create_async_engine(database_url, pool_pre_ping=True, future=True)


class PostgresPlanetRepository:
    """Repositório de planetas em Postgres, fiel à porta `PlanetRepository`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # --- Estado corrente -------------------------------------------------------
    async def save_checkpoint(self, state: PlanetState) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO simulation.planets (planet_id, seed, tick, state)
                    VALUES (:planet_id, :seed, :tick, CAST(:state AS jsonb))
                    ON CONFLICT (planet_id) DO UPDATE
                        SET tick = EXCLUDED.tick,
                            state = EXCLUDED.state,
                            updated_at = now()
                    """
                ),
                {
                    "planet_id": state.planet_id,
                    "seed": state.seed,
                    "tick": state.tick,
                    "state": state_to_json(state),
                },
            )

    async def load_latest(self, planet_id: str) -> PlanetState | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT state FROM simulation.planets WHERE planet_id = :planet_id"),
                    {"planet_id": planet_id},
                )
            ).first()
        return state_from_json(row[0]) if row is not None else None

    # --- Linha do tempo (append-only) -----------------------------------------
    async def append_checkpoint(self, checkpoint: EraCheckpoint) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO simulation.era_checkpoints
                        (planet_id, era, seed, start_tick, end_tick, state)
                    VALUES
                        (:planet_id, :era, :seed, :start_tick, :end_tick, CAST(:state AS jsonb))
                    ON CONFLICT (planet_id, era) DO NOTHING
                    """
                ),
                {
                    "planet_id": checkpoint.planet_id,
                    "era": checkpoint.era,
                    "seed": checkpoint.seed,
                    "start_tick": checkpoint.start_tick,
                    "end_tick": checkpoint.end_tick,
                    "state": state_to_json(checkpoint.state),
                },
            )

    async def append_event(self, entry: EventLogEntry) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO simulation.event_log (planet_id, tick, event_type, payload)
                    VALUES (:planet_id, :tick, :event_type, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "planet_id": entry.planet_id,
                    "tick": entry.tick,
                    "event_type": entry.event_type,
                    "payload": json.dumps(dict(entry.payload)),
                },
            )

    async def load_checkpoint(self, planet_id: str, era: int) -> EraCheckpoint | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT planet_id, era, seed, start_tick, end_tick, state
                        FROM simulation.era_checkpoints
                        WHERE planet_id = :planet_id AND era = :era
                        """
                    ),
                    {"planet_id": planet_id, "era": era},
                )
            ).first()
        if row is None:
            return None
        return EraCheckpoint(
            planet_id=row[0],
            era=row[1],
            seed=row[2],
            start_tick=row[3],
            end_tick=row[4],
            state=state_from_json(row[5]),
        )

    async def load_events(
        self, planet_id: str, from_tick: int, to_tick: int
    ) -> list[EventLogEntry]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT planet_id, tick, event_type, payload
                        FROM simulation.event_log
                        WHERE planet_id = :planet_id AND tick BETWEEN :from_tick AND :to_tick
                        ORDER BY tick, id
                        """
                    ),
                    {"planet_id": planet_id, "from_tick": from_tick, "to_tick": to_tick},
                )
            ).all()
        return [
            EventLogEntry(
                planet_id=row[0],
                tick=row[1],
                event_type=row[2],
                payload=row[3] if isinstance(row[3], dict) else json.loads(row[3]),
            )
            for row in rows
        ]

    async def get_timeline(self, planet_id: str) -> list[EraSummary]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT c.era,
                               c.start_tick,
                               c.end_tick,
                               (SELECT count(*)
                                  FROM simulation.event_log e
                                 WHERE e.planet_id = c.planet_id
                                   AND e.tick > c.start_tick
                                   AND e.tick <= c.end_tick) AS event_count
                        FROM simulation.era_checkpoints c
                        WHERE c.planet_id = :planet_id
                        ORDER BY c.era
                        """
                    ),
                    {"planet_id": planet_id},
                )
            ).all()
        return [
            EraSummary(era=row[0], start_tick=row[1], end_tick=row[2], event_count=row[3])
            for row in rows
        ]

    # --- Códex de espécies (Inc 3) ---------------------------------------------
    async def save_species(self, records: list[SpeciesRecord]) -> None:
        """Upsert do códex: a espécie é a projeção corrente; a HISTÓRIA de
        especiação/extinção vive no `event_log` append-only (ADR 0004/0006)."""
        if not records:
            return
        async with self._engine.begin() as conn:
            for record in records:
                await conn.execute(
                    text(
                        """
                        INSERT INTO simulation.species
                            (species_id, planet_id, genome, emerged_era, extinct_era,
                             ancestor_id, population, fitness)
                        VALUES
                            (:species_id, :planet_id, CAST(:genome AS jsonb), :emerged_era,
                             :extinct_era, :ancestor_id, :population, :fitness)
                        ON CONFLICT (planet_id, species_id) DO UPDATE
                            SET genome = EXCLUDED.genome,
                                extinct_era = EXCLUDED.extinct_era,
                                population = EXCLUDED.population,
                                fitness = EXCLUDED.fitness,
                                updated_at = now()
                        """
                    ),
                    {
                        "species_id": record.species_id,
                        "planet_id": record.planet_id,
                        "genome": json.dumps(record.genome.to_dict()),
                        "emerged_era": record.emerged_era,
                        "extinct_era": record.extinct_era,
                        "ancestor_id": record.ancestor_id,
                        "population": record.population,
                        "fitness": record.fitness,
                    },
                )

    async def load_species(self, planet_id: str) -> list[SpeciesRecord]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT species_id, planet_id, genome, emerged_era, extinct_era,
                               ancestor_id, population, fitness
                        FROM simulation.species
                        WHERE planet_id = :planet_id
                        ORDER BY emerged_era, species_id
                        """
                    ),
                    {"planet_id": planet_id},
                )
            ).all()
        return [_species_from_row(row) for row in rows]

    async def load_species_by_id(self, planet_id: str, species_id: str) -> SpeciesRecord | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT species_id, planet_id, genome, emerged_era, extinct_era,
                               ancestor_id, population, fitness
                        FROM simulation.species
                        WHERE planet_id = :planet_id AND species_id = :species_id
                        """
                    ),
                    {"planet_id": planet_id, "species_id": species_id},
                )
            ).first()
        return _species_from_row(row) if row is not None else None


def _species_from_row(row: Any) -> SpeciesRecord:
    """Reconstrói o registro do códex a partir da linha do Postgres."""
    genome = row[2] if isinstance(row[2], dict) else json.loads(row[2])
    return SpeciesRecord(
        species_id=row[0],
        planet_id=row[1],
        genome=Genome.from_dict(genome),
        emerged_era=row[3],
        extinct_era=row[4],
        ancestor_id=row[5],
        population=float(row[6]),
        fitness=float(row[7]),
    )
