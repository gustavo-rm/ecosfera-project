"""Sanidade científica dos subsistemas (padrão Strategy)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from ecosfera_ai.simulation_engine.params import load_params
from ecosfera_ai.simulation_engine.state import PlanetState
from ecosfera_ai.simulation_engine.subsystems.chemistry import ChemistrySubsystem
from ecosfera_ai.simulation_engine.subsystems.climate import ClimateSubsystem
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _state(
    *,
    temperature: float = 15.0,
    co2: float = 280.0,
    water: float = 1.0,
    ice_cover: float = 0.3,
    biomass: float = 0.0,
) -> PlanetState:
    return PlanetState(
        planet_id="p",
        seed=1,
        tick=0,
        temperature=temperature,
        co2=co2,
        water=water,
        ice_cover=ice_cover,
        biomass=biomass,
        energy=0.0,
    )


def test_more_co2_raises_temperature() -> None:
    climate = ClimateSubsystem(PARAMS.climate)
    # Mesmo RNG isola o efeito estufa do ruído meteorológico.
    low = climate.step(_state(co2=280.0), np.random.default_rng(0))
    high = climate.step(_state(co2=560.0), np.random.default_rng(0))
    assert high.d_temperature > low.d_temperature


def test_chemistry_keeps_water_and_ice_valid_while_melting() -> None:
    chemistry = ChemistrySubsystem(PARAMS.chemistry)
    state = _state(temperature=40.0, ice_cover=0.05, water=0.0)
    for _ in range(200):
        state = state.apply(chemistry.step(state, np.random.default_rng(0)), PARAMS.bounds)
    assert 0.0 <= state.ice_cover <= 1.0
    assert state.water >= 0.0
    assert state.co2 >= 0.0


def test_chemistry_keeps_ice_and_water_valid_while_freezing() -> None:
    chemistry = ChemistrySubsystem(PARAMS.chemistry)
    state = _state(temperature=-50.0, ice_cover=0.9, water=5.0)
    for _ in range(500):
        state = state.apply(chemistry.step(state, np.random.default_rng(0)), PARAMS.bounds)
    # gelo recortado em [0,1] e água nunca negativa, mesmo no congelamento extremo
    assert 0.0 <= state.ice_cover <= 1.0
    assert state.water >= 0.0


def test_life_emerges_only_when_habitable() -> None:
    life = LifeSubsystem(replace(PARAMS.life, growth_variability=0.0))
    habitable = _state(temperature=22.0, water=1.0, biomass=0.0)
    barren = _state(temperature=-80.0, water=0.0, biomass=0.0)
    assert life.step(habitable, np.random.default_rng(0)).d_biomass > 0.0
    assert life.step(barren, np.random.default_rng(0)).d_biomass == 0.0


def test_life_grows_logistically_towards_capacity() -> None:
    life = LifeSubsystem(replace(PARAMS.life, growth_variability=0.0))
    state = _state(temperature=22.0, water=1.0, biomass=0.0)
    for _ in range(300):
        state = state.apply(life.step(state, np.random.default_rng(0)), PARAMS.bounds)
    assert state.biomass > 1.0
    assert state.biomass <= PARAMS.life.carrying_capacity


def test_habitability_ignores_water_when_not_required() -> None:
    life = LifeSubsystem(replace(PARAMS.life, water_requirement=0.0))
    # sem exigência de água, a habitabilidade depende só da temperatura ótima
    assert life.habitability(_state(temperature=22.0, water=0.0)) == 1.0
