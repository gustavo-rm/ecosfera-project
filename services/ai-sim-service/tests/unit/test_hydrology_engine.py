"""Hydrology Engine: quatro reservatórios, cinco fluxos, uma conservação (M2)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ecosfera_ai.engines.hydrology.contracts import load_params
from ecosfera_ai.engines.hydrology.domain import (
    apply_fluxes,
    ice_fraction,
    target_circulation,
    target_salinity,
    total_water,
    water_fluxes,
)
from ecosfera_ai.engines.hydrology.events import ICE_SHEET_CHANGED, HydrologyCauseCode
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    ClimateSlice,
    HydrologySlice,
    SliceRef,
    WorldStateSnapshot,
)

PARAMS = load_params()


def _snapshot(temperature: float = 15.0, **water: float) -> WorldStateSnapshot:
    defaults = {"ocean": 1.0, "ice": 0.1, "vapour": 0.05, "freshwater": 0.05}
    defaults.update(water)
    return WorldStateSnapshot(
        planet_id="p",
        seed=5,
        tick=0,
        era=0,
        climate=ClimateSlice(temperature=temperature),
        hydrology=HydrologySlice(**defaults),
    )


def _context(snapshot: WorldStateSnapshot, caused_by: dict | None = None) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "hydrology", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
        caused_by=caused_by or {},
    )


def test_declares_the_climate_read_and_owns_the_water() -> None:
    engine = HydrologyEngine()
    assert engine.writes is SliceRef.HYDROLOGY
    assert engine.reads == frozenset({SliceRef.CLIMATE})
    assert engine.lagged_reads == frozenset({SliceRef.EVENT})


def test_the_fluxes_only_move_mass_they_never_create_it() -> None:
    """A invariante central: a soma dos quatro reservatórios não muda."""
    before = (1.0, 0.1, 0.05, 0.05)
    fluxes = water_fluxes(*before, temperature=20.0, params=PARAMS)
    after = apply_fluxes(*before, fluxes)
    assert total_water(*after) == pytest.approx(total_water(*before), abs=1e-12)


@pytest.mark.parametrize("temperature", [-30.0, -5.0, 0.0, 12.0, 25.0, 60.0])
def test_conservation_holds_across_the_whole_thermal_range(temperature: float) -> None:
    """Inclusive nos extremos, onde o degelo ou o congelamento saturam."""
    before = (1.0, 0.4, 0.05, 0.05)
    after = apply_fluxes(*before, water_fluxes(*before, temperature=temperature, params=PARAMS))
    assert total_water(*after) == pytest.approx(total_water(*before), abs=1e-12)
    assert all(reservoir >= 0.0 for reservoir in after)


def test_no_flux_drains_more_than_its_source_holds() -> None:
    """A não-negatividade vem do limite por ORIGEM, antes da invariante."""
    fluxes = water_fluxes(0.001, 0.001, 0.001, 0.001, temperature=90.0, params=PARAMS)
    assert fluxes.evaporation <= 0.001
    assert fluxes.melt <= 0.001
    assert fluxes.precipitation <= 0.001


def test_evaporation_grows_with_temperature() -> None:
    """Clausius-Clapeyron linearizada: mais calor, mais vapor."""
    cold = water_fluxes(1.0, 0.1, 0.0, 0.0, temperature=12.0, params=PARAMS)
    hot = water_fluxes(1.0, 0.1, 0.0, 0.0, temperature=30.0, params=PARAMS)
    assert hot.evaporation > cold.evaporation


def test_ice_melts_when_warm_and_forms_when_cold() -> None:
    warm = water_fluxes(1.0, 0.3, 0.0, 0.0, temperature=25.0, params=PARAMS)
    assert warm.melt > 0.0 and warm.freeze == 0.0

    cold = water_fluxes(1.0, 0.3, 0.0, 0.0, temperature=-15.0, params=PARAMS)
    assert cold.freeze > 0.0 and cold.melt == 0.0


def test_the_engine_publishes_the_ice_fraction_for_the_albedo() -> None:
    """O Climate LÊ esta fração; recalculá-la lá seria importar outro Engine."""
    snapshot = _snapshot(temperature=25.0)
    result = HydrologyEngine().tick(_context(snapshot))
    published = snapshot.hydrology.ice_fraction + result.delta.values["ice_fraction"]

    current = snapshot.hydrology
    fluxes = water_fluxes(
        current.ocean, current.ice, current.vapour, current.freshwater, 25.0, PARAMS
    )
    ocean, ice, vapour, freshwater = apply_fluxes(
        current.ocean, current.ice, current.vapour, current.freshwater, fluxes
    )
    assert published == pytest.approx(ice_fraction(ice, ocean, vapour, freshwater))


def test_salinity_dilutes_as_the_ocean_grows() -> None:
    """Sal conservado numa água que cresce: a concentração cai."""
    assert target_salinity(2.0, PARAMS) < target_salinity(1.0, PARAMS)


def test_cold_and_salty_water_strengthens_the_circulation() -> None:
    salty = target_circulation(0.40, 14.0, PARAMS)
    fresh = target_circulation(0.30, 14.0, PARAMS)
    warm = target_circulation(0.35, 30.0, PARAMS)
    cool = target_circulation(0.35, 5.0, PARAMS)
    assert salty > fresh
    assert cool > warm


def test_a_melting_event_carries_the_temperature_cause() -> None:
    """Degelo grande o bastante vira travessia, com causa estruturada."""
    hot = replace(PARAMS, melt_coeff=0.9, ice_event_threshold=0.001)
    snapshot = _snapshot(temperature=40.0, ice=0.5)
    result = HydrologyEngine(hot).tick(_context(snapshot))

    melting = [e for e in result.events if e.event_type == ICE_SHEET_CHANGED]
    assert melting, "um degelo massivo deveria virar evento"
    assert melting[0].cause_code is HydrologyCauseCode.TEMPERATURE_RISE


def test_a_calm_tick_produces_no_event() -> None:
    """O Canal B registra travessia, não o contínuo (ADR-ARCH-0002)."""
    result = HydrologyEngine().tick(_context(_snapshot(temperature=0.0, ice=0.1)))
    assert result.events == ()


def test_the_engine_never_writes_outside_its_slice() -> None:
    result = HydrologyEngine().tick(_context(_snapshot()))
    assert result.delta.writes is SliceRef.HYDROLOGY
    assert set(result.delta.values) <= {
        "ocean",
        "ice",
        "vapour",
        "freshwater",
        "salinity",
        "ocean_circulation",
        "ice_fraction",
        "evaporation",
        "precipitation",
    }
