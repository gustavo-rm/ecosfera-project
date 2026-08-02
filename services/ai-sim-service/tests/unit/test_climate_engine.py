"""Climate Engine: temperatura resolvida a partir do forçamento radiativo (M1)."""

from __future__ import annotations

import pytest

from ecosfera_ai.engines.climate.contracts import load_params
from ecosfera_ai.engines.climate.domain import (
    absorbed_energy,
    albedo,
    equilibrium_temperature,
    ocean_heat_flux,
    temperature_band,
)
from ecosfera_ai.engines.climate.events import TEMPERATURE_SHIFT, ClimateCauseCode
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    AstronomySlice,
    AtmosphereSlice,
    ClimateSlice,
    HydrologySlice,
    SliceRef,
    WorldStateSnapshot,
)

PARAMS = load_params()


def _snapshot(
    forcing: float = 0.0,
    temperature: float = 14.0,
    ice: float = 0.1,
    circulation: float = 0.5,
) -> WorldStateSnapshot:
    return WorldStateSnapshot(
        planet_id="p",
        seed=11,
        tick=0,
        era=0,
        atmosphere=AtmosphereSlice(greenhouse_forcing=forcing),
        climate=ClimateSlice(temperature=temperature),
        astronomy=AstronomySlice(solar_flux=1.0),
        hydrology=HydrologySlice(ice_fraction=ice, ocean_circulation=circulation),
    )


def _context(snapshot: WorldStateSnapshot, caused_by: dict | None = None) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "climate", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
        caused_by=caused_by or {},
    )


def test_reads_the_forcing_and_never_recomputes_co2() -> None:
    engine = ClimateEngine()
    assert SliceRef.ATMOSPHERE in engine.reads
    assert engine.writes is SliceRef.CLIMATE
    result = engine.tick(_context(_snapshot()))
    assert set(result.delta.values) == {"temperature", "energy"}


def test_temperature_responds_monotonically_to_the_forcing() -> None:
    """Mais forçamento, mais aquecimento — a resposta não pode inverter."""
    warming = [
        ClimateEngine().tick(_context(_snapshot(forcing=f))).delta.values["temperature"]
        for f in (0.0, 2.0, 4.0, 8.0)
    ]
    assert warming == sorted(warming)


def test_equilibrium_grows_with_the_forcing_by_the_climate_sensitivity() -> None:
    base = equilibrium_temperature(0.66, 0.0, PARAMS)
    doubled = equilibrium_temperature(0.66, 3.7, PARAMS)
    assert doubled - base == pytest.approx(PARAMS.climate_sensitivity * 3.7)


def test_ice_raises_the_albedo_and_cools_the_planet() -> None:
    """Retroalimentação do gelo: reflete mais, absorve menos."""
    assert albedo(1.0, PARAMS) > albedo(0.0, PARAMS)
    assert absorbed_energy(1.0, ice_cover=1.0, params=PARAMS) < absorbed_energy(
        1.0, ice_cover=0.0, params=PARAMS
    )


def test_ocean_circulation_damps_the_warming() -> None:
    """Sequestro de calor é retroalimentação NEGATIVA: sempre amortece."""
    hot = ocean_heat_flux(30.0, ocean_circulation=1.0, params=PARAMS)
    cold = ocean_heat_flux(0.0, ocean_circulation=1.0, params=PARAMS)
    assert hot < 0.0 < cold
    assert ocean_heat_flux(30.0, ocean_circulation=0.0, params=PARAMS) == 0.0


def test_is_deterministic_under_the_same_seed() -> None:
    first = ClimateEngine().tick(_context(_snapshot(forcing=2.0)))
    second = ClimateEngine().tick(_context(_snapshot(forcing=2.0)))
    assert dict(first.delta.values) == dict(second.delta.values)


def test_shift_event_needs_a_change_above_the_threshold() -> None:
    calm = ClimateEngine().tick(_context(_snapshot(forcing=0.0, temperature=17.6)))
    assert not [e for e in calm.events if e.event_type == TEMPERATURE_SHIFT]

    shock = ClimateEngine().tick(_context(_snapshot(forcing=12.0, temperature=0.0)))
    assert [e for e in shock.events if e.event_type == TEMPERATURE_SHIFT]


def test_shift_event_carries_the_radiative_cause_code() -> None:
    event = ClimateEngine().tick(_context(_snapshot(forcing=12.0, temperature=0.0))).events[0]
    assert event.cause_code is ClimateCauseCode.RADIATIVE_FORCING
    assert event.engine_id == "climate"
    assert "forcing" in event.cause_detail


def test_event_chains_to_the_atmosphere_of_the_same_tick() -> None:
    ctx = _context(
        _snapshot(forcing=12.0, temperature=0.0),
        caused_by={SliceRef.ATMOSPHERE: ("evento-do-forcamento",)},
    )
    event = ClimateEngine().tick(ctx).events[0]
    assert event.causation_id == "evento-do-forcamento"


def test_threshold_crossing_chains_to_the_shift_of_the_same_tick() -> None:
    """Quando os dois eventos ocorrem juntos, o patamar é efeito do salto."""
    result = ClimateEngine().tick(_context(_snapshot(forcing=12.0, temperature=0.0)))
    types = [e.event_type for e in result.events]
    if len(types) == 2:
        assert result.events[1].causation_id == result.events[0].event_id


def test_temperature_band_is_monotonic() -> None:
    bands = [temperature_band(t, PARAMS) for t in (-10.0, 5.0, 15.0, 25.0, 35.0)]
    assert bands == sorted(bands)
