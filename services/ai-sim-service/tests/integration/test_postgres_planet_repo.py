"""Persistência real em Postgres: migrations Alembic + porta PlanetRepository.

Usa Testcontainers para subir um Postgres efêmero. Numa máquina de dev sem Docker
o módulo inteiro é PULADO — a suíte determinística continua verificável sem
infraestrutura, que é a razão de o adaptador in-memory existir.

No CI o pulo deixa de estar disponível: `ECOSFERA_REQUIRE_POSTGRES` transforma a
ausência de Docker em FALHA (M5, `tests/docker_guard.py`), porque um runner sem
daemon silenciaria a persistência inteira com a árvore verde.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.docker_guard import POSTGRES_IMAGE, requires_postgres, run_migrations

from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from ecosfera_ai.simulation_engine.timeline import (
    EVENT_INTERVENTION,
    EVENT_LIFE_EMERGED,
    EraCheckpoint,
    EventLogEntry,
)

PARAMS = load_params(Path("configs/simulation_params.yaml"))


# Pula onde pular é honesto; FALHA onde pular seria esconder (ver docker_guard).
pytestmark = requires_postgres()


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        url = container.get_connection_url()
        run_migrations(url)
        created = create_async_engine(
            url,
            poolclass=NullPool,  # não reusa conexões entre event loops
            connect_args={"statement_cache_size": 0},  # asyncpg sem prepared statements presos
        )
        yield created


@pytest.fixture
def repo(engine: Any) -> Any:
    from ecosfera_ai.infrastructure.persistence.postgres_planet_repo import (
        PostgresPlanetRepository,
    )

    return PostgresPlanetRepository(engine)


@pytest.mark.asyncio
async def test_current_state_is_upserted_and_read_back(repo: Any) -> None:
    state = initial_state(PlanetSeed("pg-current", 42), PARAMS)
    await repo.save_checkpoint(state)
    assert await repo.load_latest("pg-current") == state

    advanced = state.advanced()
    await repo.save_checkpoint(advanced)
    loaded = await repo.load_latest("pg-current")
    assert loaded is not None
    assert loaded.tick == advanced.tick  # projeção do estado corrente, não histórico


@pytest.mark.asyncio
async def test_unknown_planet_loads_as_none(repo: Any) -> None:
    assert await repo.load_latest("pg-ghost") is None
    assert await repo.load_checkpoint("pg-ghost", 1) is None
    assert await repo.get_timeline("pg-ghost") == []


@pytest.mark.asyncio
async def test_checkpoints_and_events_build_the_timeline(repo: Any) -> None:
    planet_id = "pg-timeline"
    genesis = initial_state(PlanetSeed(planet_id, 7), PARAMS)
    end_of_era = genesis.advanced().advanced()

    await repo.append_checkpoint(
        EraCheckpoint(planet_id, era=0, seed=7, start_tick=0, end_tick=0, state=genesis)
    )
    await repo.append_checkpoint(
        EraCheckpoint(planet_id, era=1, seed=7, start_tick=0, end_tick=2, state=end_of_era)
    )
    await repo.append_event(
        EventLogEntry(planet_id, tick=1, event_type=EVENT_LIFE_EMERGED, payload={"biomass": 0.5})
    )
    await repo.append_event(
        EventLogEntry(planet_id, tick=2, event_type=EVENT_INTERVENTION, payload={"co2": 10.0})
    )

    stored = await repo.load_checkpoint(planet_id, 1)
    assert stored is not None
    assert stored.state == end_of_era  # round-trip fiel do estado em JSONB
    assert stored.start_tick == 0 and stored.end_tick == 2

    timeline = await repo.get_timeline(planet_id)
    assert [(e.era, e.event_count) for e in timeline] == [(0, 0), (1, 2)]


@pytest.mark.asyncio
async def test_events_are_filtered_by_tick_window(repo: Any) -> None:
    planet_id = "pg-events"
    for tick in (1, 5, 9):
        await repo.append_event(
            EventLogEntry(planet_id, tick=tick, event_type=EVENT_INTERVENTION, payload={"co2": 1.0})
        )

    window = await repo.load_events(planet_id, 2, 9)
    assert [e.tick for e in window] == [5, 9]
    assert window[0].payload == {"co2": 1.0}


@pytest.mark.asyncio
async def test_appending_the_same_era_twice_is_idempotent(repo: Any) -> None:
    planet_id = "pg-idempotent"
    state = initial_state(PlanetSeed(planet_id, 1), PARAMS)
    checkpoint = EraCheckpoint(planet_id, era=1, seed=1, start_tick=0, end_tick=1, state=state)

    await repo.append_checkpoint(checkpoint)
    await repo.append_checkpoint(checkpoint)  # append-only: não duplica nem sobrescreve

    assert len(await repo.get_timeline(planet_id)) == 1
