"""Subsistemas estendidos: física, geologia e oceano (determinismo + invariantes)."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from ecosfera_ai.simulation_engine.orchestrator import SUBSYSTEM_ORDER
from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState
from ecosfera_ai.simulation_engine.subsystems.chemistry import ChemistrySubsystem
from ecosfera_ai.simulation_engine.subsystems.geology import GeologySubsystem
from ecosfera_ai.simulation_engine.subsystems.ocean import OceanSubsystem
from ecosfera_ai.simulation_engine.subsystems.physics import PhysicsSubsystem

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _state(**over: float) -> PlanetState:
    base = initial_state(PlanetSeed(planet_id="p", seed=1), PARAMS)
    return replace(base, **over)  # type: ignore[arg-type]


# --- Física ------------------------------------------------------------------


def test_physics_is_deterministic_and_ignores_rng() -> None:
    physics = PhysicsSubsystem(PARAMS.physics)
    state = _state()
    # A física é puramente determinística: RNGs distintos dão o mesmo delta.
    assert physics.step(state, np.random.default_rng(0)) == physics.step(
        state, np.random.default_rng(999)
    )


def test_verlet_conserves_orbital_energy() -> None:
    physics = PhysicsSubsystem(PARAMS.physics)
    state = _state()
    initial_energy = physics.orbital_energy(state)
    rng = np.random.default_rng(0)
    for _ in range(500):
        state = state.apply(physics.step(state, rng), PARAMS.bounds)
    # Integrador simplético: a energia orbital não deriva (órbita não decai).
    assert abs(physics.orbital_energy(state) - initial_energy) < 1e-4


def test_orbit_stays_bounded_and_flux_follows_inverse_square() -> None:
    physics = PhysicsSubsystem(PARAMS.physics)
    state = _state()
    rng = np.random.default_rng(0)
    radii = []
    for _ in range(300):
        state = state.apply(physics.step(state, rng), PARAMS.bounds)
        radii.append(math.hypot(state.orbital_x, state.orbital_y))
    assert min(radii) > 0.5 and max(radii) < 2.0  # órbita estável, não escapa
    assert state.solar_flux > 0.0
    # Lei do inverso do quadrado: dobrar a distância cai a irradiância a 1/4.
    assert physics.solar_flux_at(2.0, 0.0) == physics.solar_flux_at(1.0, 0.0) / 4.0


# --- Geologia ----------------------------------------------------------------


def test_physics_degenerates_safely_at_the_star_centre() -> None:
    # Guarda de robustez: distância zero não pode gerar divisão por zero.
    physics = PhysicsSubsystem(PARAMS.physics)
    assert physics.solar_flux_at(0.0, 0.0) == 0.0
    centred = _state(orbital_x=0.0, orbital_y=0.0, orbital_vx=0.0, orbital_vy=0.0)
    delta = physics.step(centred, np.random.default_rng(0))
    assert delta.d_orbital_vx == 0.0 and delta.d_orbital_vy == 0.0


def test_geology_is_reproducible_by_seed_and_diverges_across_seeds() -> None:
    geology = GeologySubsystem(PARAMS.geology)
    state = _state()
    assert geology.step(state, np.random.default_rng(7)) == geology.step(
        state, np.random.default_rng(7)
    )
    assert geology.step(state, np.random.default_rng(7)) != geology.step(
        state, np.random.default_rng(8)
    )


def test_geology_keeps_volcanism_and_relief_in_valid_ranges() -> None:
    geology = GeologySubsystem(PARAMS.geology)
    state = _state()
    rng = np.random.default_rng(3)
    for _ in range(400):
        state = state.apply(geology.step(state, rng), PARAMS.bounds)
        assert state.volcanism >= 0.0
        assert 0.0 <= state.relief <= 1.0


def test_erosion_wears_relief_down_without_volcanism() -> None:
    # Sem soerguimento, a água desgasta o relevo (erosão domina).
    geology = GeologySubsystem(replace(PARAMS.geology, uplift_coeff=0.0))
    state = _state(relief=0.8, volcanism=0.0, water=1.0)
    rng = np.random.default_rng(0)
    for _ in range(50):
        state = state.apply(geology.step(state, rng), PARAMS.bounds)
    assert state.relief < 0.8


def test_volcanism_raises_co2_through_chemistry() -> None:
    # Acoplamento geologia -> química: mais vulcanismo, mais desgaseificação.
    chemistry = ChemistrySubsystem(PARAMS.chemistry)
    quiet = chemistry.step(_state(volcanism=0.0), np.random.default_rng(0))
    active = chemistry.step(_state(volcanism=5.0), np.random.default_rng(0))
    assert active.d_co2 > quiet.d_co2


# --- Oceano ------------------------------------------------------------------


def test_salinity_relaxes_towards_salt_over_water() -> None:
    ocean = OceanSubsystem(PARAMS.ocean)
    # Mais água que o equilíbrio => oceano dilui (salinidade cai).
    diluted = _state(water=2.0, salinity=PARAMS.ocean.reference_salinity)
    assert ocean.step(diluted, np.random.default_rng(0)).d_salinity < 0.0
    # Menos água => concentra.
    concentrated = _state(water=0.5, salinity=PARAMS.ocean.reference_salinity)
    assert ocean.step(concentrated, np.random.default_rng(0)).d_salinity > 0.0


def test_warming_weakens_circulation_and_ocean_absorbs_heat() -> None:
    ocean = OceanSubsystem(replace(PARAMS.ocean, circulation_variability=0.0))
    warm = _state(temperature=PARAMS.ocean.reference_temperature + 20.0)
    cold = _state(temperature=PARAMS.ocean.reference_temperature - 20.0)
    rng = np.random.default_rng(0)
    # Aquecimento enfraquece a circulação termohalina...
    assert ocean.step(warm, rng).d_ocean_circulation < ocean.step(cold, rng).d_ocean_circulation
    # ...e o oceano retira calor da superfície quente (retroalimentação negativa).
    assert ocean.step(warm, np.random.default_rng(0)).d_temperature < 0.0


def test_ocean_keeps_the_water_cycle_closed() -> None:
    ocean = OceanSubsystem(PARAMS.ocean)
    state = _state()
    rng = np.random.default_rng(0)
    for _ in range(100):
        delta = ocean.step(state, rng)
        assert delta.d_water == 0.0  # evaporação retorna como precipitação
        state = state.apply(delta, PARAMS.bounds)
    assert state.salinity >= 0.0
    assert 0.0 <= state.ocean_circulation <= 1.0


# --- Acoplamento e invariantes globais ---------------------------------------


def test_orchestrator_runs_subsystems_in_the_canonical_order() -> None:
    assert build_orchestrator(PARAMS).subsystem_names == SUBSYSTEM_ORDER


def test_hydrosphere_mass_is_approximately_conserved() -> None:
    # A química só TROCA massa entre gelo e água líquida; a grandeza
    # `água + fator * gelo` é, portanto, um invariante do subsistema.
    chemistry = ChemistrySubsystem(PARAMS.chemistry)
    factor = PARAMS.chemistry.water_ice_exchange
    state = _state(temperature=5.0, ice_cover=0.4, water=1.0)
    total_before = state.water + factor * state.ice_cover
    rng = np.random.default_rng(0)
    for _ in range(100):
        state = state.apply(chemistry.step(state, rng), PARAMS.bounds)
    assert math.isclose(state.water + factor * state.ice_cover, total_before, rel_tol=1e-9)


def test_full_tick_keeps_every_stock_within_bounds() -> None:
    orchestrator = build_orchestrator(PARAMS)
    state = initial_state(PlanetSeed(planet_id="p", seed=11), PARAMS)
    for _ in range(200):
        state = orchestrator.tick(state).state
        assert state.co2 >= 0.0
        assert state.water >= 0.0
        assert state.biomass >= 0.0
        assert state.solar_flux >= 0.0
        assert state.volcanism >= 0.0
        assert state.salinity >= 0.0
        assert 0.0 <= state.ice_cover <= 1.0
        assert 0.0 <= state.relief <= 1.0
        assert 0.0 <= state.ocean_circulation <= 1.0
