"""Atmosphere Engine: estoque de carbono e forçamento logarítmico (M1)."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from ecosfera_ai.engines.atmosphere.contracts import load_params
from ecosfera_ai.engines.atmosphere.domain import (
    carbon_sinks,
    co2_change,
    forcing_band,
    radiative_forcing,
)
from ecosfera_ai.engines.atmosphere.events import (
    GREENHOUSE_FORCING_CHANGED,
    AtmosphereCauseCode,
)
from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    AtmosphereSlice,
    BiotaSlice,
    ChemistrySlice,
    GeologySlice,
    SliceRef,
    WorldStateSnapshot,
)

PARAMS = load_params()


def _snapshot(
    co2: float = 280.0,
    forcing: float = 0.0,
    flux: float = 0.0,
    biomass: float = 0.0,
    air_sea_flux: float = 0.0,
) -> WorldStateSnapshot:
    return WorldStateSnapshot(
        planet_id="p",
        seed=7,
        tick=0,
        era=0,
        geology=GeologySlice(co2_flux=flux),
        atmosphere=AtmosphereSlice(co2=co2, greenhouse_forcing=forcing),
        biota=BiotaSlice(biomass=biomass),
        chemistry=ChemistrySlice(air_sea_flux=air_sea_flux),
    )


def _context(snapshot: WorldStateSnapshot, caused_by: dict | None = None) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "atmosphere", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
        caused_by=caused_by or {},
    )


def test_reads_geology_in_the_same_tick() -> None:
    engine = AtmosphereEngine()
    assert SliceRef.GEOLOGY in engine.reads
    assert engine.writes is SliceRef.ATMOSPHERE


def test_the_flux_from_geology_becomes_stock() -> None:
    result = AtmosphereEngine().tick(_context(_snapshot(co2=280.0, flux=10.0)))
    sinks = carbon_sinks(280.0, 0.0, PARAMS)
    assert result.delta.values["co2"] == pytest.approx(10.0 - sinks)


def test_forcing_is_logarithmic_in_co2() -> None:
    """Myhre et al. 1998: cada DUPLICAÇÃO acrescenta o mesmo forçamento."""
    ref = PARAMS.reference_co2
    one = radiative_forcing(2 * ref, PARAMS) - radiative_forcing(ref, PARAMS)
    two = radiative_forcing(4 * ref, PARAMS) - radiative_forcing(2 * ref, PARAMS)
    assert one == pytest.approx(two)
    assert one == pytest.approx(PARAMS.forcing_coefficient * math.log(2.0))


def test_forcing_is_zero_at_the_reference_and_negative_below() -> None:
    assert radiative_forcing(PARAMS.reference_co2, PARAMS) == pytest.approx(0.0)
    assert radiative_forcing(PARAMS.reference_co2 / 2, PARAMS) < 0.0


def test_forcing_is_finite_even_with_no_carbon_left() -> None:
    """ln(0) é -infinito: sem piso, um planeta sem carbono quebraria o clima."""
    assert math.isfinite(radiative_forcing(0.0, PARAMS))


def test_co2_never_goes_negative() -> None:
    """Invariante de estoque: sumidouros não podem consumir mais do que existe."""
    result = AtmosphereEngine().tick(_context(_snapshot(co2=0.001, flux=0.0, biomass=1e6)))
    assert 0.001 + result.delta.values["co2"] >= 0.0


def test_carbon_entering_equals_carbon_stored_when_there_are_no_sinks() -> None:
    """Conservação: sem sumidouros, tudo que a geologia emite vira estoque."""
    no_sinks = replace(PARAMS, weathering_coeff=0.0, carbon_uptake_coeff=0.0)
    assert co2_change(
        500.0, inflow=7.5, biomass=3.0, air_sea_flux=0.0, params=no_sinks
    ) == pytest.approx(7.5)


def test_weathering_grows_with_the_stock() -> None:
    """Termostato do ciclo carbonato-silicato: mais CO2, mais remoção."""
    assert carbon_sinks(1000.0, 0.0, PARAMS) > carbon_sinks(300.0, 0.0, PARAMS)


def test_event_fires_only_when_the_forcing_changes_band() -> None:
    inside = AtmosphereEngine().tick(_context(_snapshot(co2=281.0, forcing=0.0, flux=0.1)))
    assert inside.events == ()

    crossing = AtmosphereEngine().tick(_context(_snapshot(co2=280.0, forcing=0.0, flux=200.0)))
    assert [e.event_type for e in crossing.events] == [GREENHOUSE_FORCING_CHANGED]


def test_the_band_comparison_survives_a_truncated_snapshot() -> None:
    """A faixa anterior vem do ESTOQUE, não do forçamento guardado.

    Na borda HTTP o snapshot é truncado a cada tick (o estado persistido ainda é
    o `PlanetState` legado, sem campo para o forçamento). Se a comparação usasse
    o valor guardado, ela veria zero toda vez e emitiria evento em TODO tick.
    """
    # Estoque alto e forçamento guardado ZERADO — exatamente o que a borda HTTP
    # entrega. Um passo minúsculo não pode disparar evento.
    quiet = AtmosphereEngine().tick(_context(_snapshot(co2=900.0, forcing=0.0, flux=0.5)))
    assert quiet.events == ()


def test_rising_and_falling_carry_different_cause_codes() -> None:
    rising = AtmosphereEngine().tick(_context(_snapshot(co2=280.0, forcing=0.0, flux=200.0)))
    assert rising.events[0].cause_code is AtmosphereCauseCode.CO2_ACCUMULATION

    # Queda de faixa: o estoque parte logo acima de 3,7 W/m² e a absorção
    # biótica o puxa para baixo do limiar no mesmo tick.
    falling = AtmosphereEngine().tick(
        _context(_snapshot(co2=560.0, forcing=3.71, flux=0.0, biomass=200.0))
    )
    assert falling.events[0].cause_code is AtmosphereCauseCode.CO2_DRAWDOWN


def test_event_chains_to_the_eruption_of_the_same_tick() -> None:
    ctx = _context(
        _snapshot(co2=280.0, forcing=0.0, flux=200.0),
        caused_by={SliceRef.GEOLOGY: ("evento-da-erupcao",)},
    )
    event = AtmosphereEngine().tick(ctx).events[0]
    assert event.causation_id == "evento-da-erupcao"


def test_forcing_band_is_monotonic() -> None:
    bands = [forcing_band(f, PARAMS) for f in (-1.0, 0.6, 2.0, 4.0, 8.0)]
    assert bands == sorted(bands)
    assert bands[0] == 0


def test_the_engine_never_writes_outside_its_slice() -> None:
    result = AtmosphereEngine().tick(_context(_snapshot(flux=5.0)))
    assert result.delta.writes is SliceRef.ATMOSPHERE
    assert set(result.delta.values) <= {"co2", "greenhouse_forcing", "pressure"}
