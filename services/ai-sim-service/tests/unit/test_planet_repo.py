"""Adaptador in-memory: checkpoints append-only por era (Dossiê §9)."""

from __future__ import annotations

import pytest

from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import (
    InMemoryPlanetRepository,
)
from ecosfera_ai.simulation_engine.state import PlanetState


def _state(planet_id: str, tick: int) -> PlanetState:
    return PlanetState(
        planet_id=planet_id,
        seed=1,
        tick=tick,
        temperature=14.0,
        co2=280.0,
        water=1.0,
        ice_cover=0.1,
        biomass=0.0,
        energy=0.0,
    )


@pytest.mark.asyncio
async def test_load_latest_is_none_for_unknown_planet() -> None:
    repo = InMemoryPlanetRepository()
    assert await repo.load_latest("ghost") is None
    assert await repo.count_checkpoints("ghost") == 0


@pytest.mark.asyncio
async def test_checkpoints_are_append_only_and_latest_wins() -> None:
    repo = InMemoryPlanetRepository()
    await repo.save_checkpoint(_state("p", tick=0))
    await repo.save_checkpoint(_state("p", tick=1))
    await repo.save_checkpoint(_state("p", tick=2))

    latest = await repo.load_latest("p")
    assert latest is not None
    assert latest.tick == 2
    # histórico preservado (append-only), base para replay (RF-016)
    assert await repo.count_checkpoints("p") == 3
