"""Chemistry Engine: troca ar<->oceano, acidificação e nutrientes (M2)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ecosfera_ai.engines.chemistry.contracts import load_params
from ecosfera_ai.engines.chemistry.domain import (
    air_sea_flux,
    carbon_burial,
    element_change,
    nutrient_change,
    ocean_partial_pressure,
    ocean_ph,
)
from ecosfera_ai.engines.chemistry.events import (
    CARBON_FLUX_SHIFT,
    NUTRIENT_DEPLETION,
    OCEAN_ACIDIFICATION,
    ChemistryCauseCode,
)
from ecosfera_ai.engines.chemistry.service import ChemistryEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    AtmosphereSlice,
    ChemistrySlice,
    GeologySlice,
    SliceRef,
    WorldStateSnapshot,
)

PARAMS = load_params()


def _snapshot(
    co2: float = 280.0,
    relief: float = 0.2,
    volcanism: float = 1.0,
    **chemistry: float,
) -> WorldStateSnapshot:
    return WorldStateSnapshot(
        planet_id="p",
        seed=9,
        tick=0,
        era=0,
        geology=GeologySlice(relief=relief, volcanism=volcanism),
        atmosphere=AtmosphereSlice(co2=co2),
        chemistry=ChemistrySlice(**chemistry),
    )


def _context(snapshot: WorldStateSnapshot, caused_by: dict | None = None) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "chemistry", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
        caused_by=caused_by or {},
    )


def test_declares_the_geology_read_and_the_two_lagged_ones() -> None:
    engine = ChemistryEngine()
    assert engine.writes is SliceRef.CHEMISTRY
    assert engine.reads == frozenset({SliceRef.GEOLOGY})
    # A atmosfera roda DEPOIS: a defasagem é o que quebra o ciclo (ADR 0012).
    assert SliceRef.ATMOSPHERE in engine.lagged_reads


def test_the_flux_is_zero_at_equilibrium() -> None:
    """Sem gradiente de pressão parcial, não há troca — lei de Henry."""
    equilibrium = PARAMS.reference_ocean_carbon
    assert ocean_partial_pressure(equilibrium, PARAMS) == pytest.approx(PARAMS.reference_co2)
    assert air_sea_flux(PARAMS.reference_co2, equilibrium, PARAMS) == pytest.approx(0.0)


def test_the_ocean_absorbs_when_the_air_is_richer_and_outgasses_when_poorer() -> None:
    equilibrium = PARAMS.reference_ocean_carbon
    assert air_sea_flux(PARAMS.reference_co2 * 2, equilibrium, PARAMS) > 0.0
    assert air_sea_flux(PARAMS.reference_co2 / 2, equilibrium, PARAMS) < 0.0


def test_a_saturated_ocean_stops_absorbing() -> None:
    """Sem saturação o oceano seria sumidouro infinito e o ar esvaziaria."""
    full = PARAMS.ocean_carbon_capacity
    assert air_sea_flux(10_000.0, full, PARAMS) == pytest.approx(0.0)


def test_ph_falls_logarithmically_with_dissolved_carbon() -> None:
    """Cada DÉCUPLO de carbono tira a mesma quantidade de pH (definição de pH)."""
    ref = PARAMS.reference_ocean_carbon
    assert ocean_ph(ref, PARAMS) == pytest.approx(PARAMS.reference_ph)
    first = ocean_ph(ref, PARAMS) - ocean_ph(ref * 10, PARAMS)
    second = ocean_ph(ref * 10, PARAMS) - ocean_ph(ref * 100, PARAMS)
    assert first == pytest.approx(second)


def test_burial_is_the_only_exit_and_never_negative() -> None:
    assert carbon_burial(500.0, PARAMS) > 0.0
    assert carbon_burial(-10.0, PARAMS) == 0.0


def test_buried_carbon_becomes_sediment_instead_of_vanishing() -> None:
    """Sem este livro, o teste de balanço confundiria sumidouro com vazamento."""
    result = ChemistryEngine().tick(_context(_snapshot(ocean_carbon=500.0)))
    buried = carbon_burial(500.0, PARAMS)
    assert result.delta.values["soil_carbon"] == pytest.approx(buried)


def test_weathering_needs_both_relief_and_volcanism() -> None:
    """O intemperismo é o produto: sem relevo exposto ou sem calor, não libera."""
    assert nutrient_change(0.0, relief=0.0, volcanism=1.0, params=PARAMS) == pytest.approx(0.0)
    assert nutrient_change(0.0, relief=0.5, volcanism=0.0, params=PARAMS) == pytest.approx(0.0)
    assert nutrient_change(0.0, relief=0.5, volcanism=1.0, params=PARAMS) > 0.0


def test_elements_drain_by_burial_when_weathering_stops() -> None:
    stock = element_change(10.0, 0.0, 0.0, PARAMS.phosphorus_yield, PARAMS)
    assert stock < 0.0


def test_a_fresh_planet_emits_nothing_even_with_empty_stocks() -> None:
    """Regressão: uma fatia zerada está ABAIXO de todo limiar de escassez.

    Se as regras testassem o valor corrente em vez da travessia, este tick
    emitiria `NutrientDepletion` — e emitiria de novo em todos os seguintes,
    afogando o Canal B (ADR-ARCH-0002, Correção 2).
    """
    result = ChemistryEngine().tick(_context(_snapshot()))
    assert result.events == ()


def test_nutrient_depletion_fires_on_the_crossing_only() -> None:
    scarce = replace(PARAMS, weathering_nutrient_yield=0.0, nutrient_recycling=0.9)
    engine = ChemistryEngine(scarce)

    # Acima do limiar e caindo para baixo dele: travessia, um evento.
    crossing = engine.tick(_context(_snapshot(nutrients=scarce.nutrient_depletion_threshold * 1.5)))
    assert [e.event_type for e in crossing.events] == [NUTRIENT_DEPLETION]
    assert crossing.events[0].cause_code is ChemistryCauseCode.NUTRIENT_EXHAUSTION

    # Já abaixo do limiar: continua escasso, mas não é notícia nova.
    already = engine.tick(_context(_snapshot(nutrients=scarce.nutrient_depletion_threshold * 0.5)))
    assert all(e.event_type != NUTRIENT_DEPLETION for e in already.events)


def test_acidification_fires_when_the_ph_crosses_down() -> None:
    threshold = PARAMS.acidification_threshold
    # Carbono suficiente para levar o pH abaixo do limiar, vindo de um pH medido.
    acidic = 10 ** ((PARAMS.reference_ph - threshold) / PARAMS.ph_sensitivity)
    snapshot = _snapshot(
        co2=280.0, ocean_carbon=PARAMS.reference_ocean_carbon * acidic * 1.5, ph=threshold + 0.1
    )
    result = ChemistryEngine().tick(_context(snapshot))
    acid_events = [e for e in result.events if e.event_type == OCEAN_ACIDIFICATION]
    assert acid_events
    assert acid_events[0].cause_code is ChemistryCauseCode.CARBON_DISSOLUTION


def test_the_flux_reversal_is_what_becomes_an_event() -> None:
    """Trocar de sentido muda a história; a magnitude de um tick, não."""
    # Antes absorvendo (+), agora o ar está pobre e o oceano devolve (-).
    snapshot = _snapshot(co2=10.0, ocean_carbon=PARAMS.reference_ocean_carbon, air_sea_flux=0.5)
    result = ChemistryEngine().tick(_context(snapshot))
    shifts = [e for e in result.events if e.event_type == CARBON_FLUX_SHIFT]
    assert shifts
    assert shifts[0].cause_code is ChemistryCauseCode.CARBON_OUTGASSING


def test_the_engine_never_writes_outside_its_slice() -> None:
    result = ChemistryEngine().tick(_context(_snapshot(ocean_carbon=100.0)))
    assert result.delta.writes is SliceRef.CHEMISTRY
    assert set(result.delta.values) <= {
        "ocean_carbon",
        "soil_carbon",
        "nutrients",
        "nitrogen",
        "phosphorus",
        "sulfur",
        "ph",
        "air_sea_flux",
    }
