"""Resource e Biota: o orçamento biológico e quem o gasta (M2).

Os dois vêm juntos porque a fronteira entre eles é o assunto: o Resource DERIVA
a capacidade de suporte a partir da física, o Biota a CONSOME, e nenhum dos dois
faz o trabalho do outro (ADR 0013).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ecosfera_ai.engines.biota.contracts import load_params as biota_params
from ecosfera_ai.engines.biota.domain import emergence, logistic_growth
from ecosfera_ai.engines.biota.events import ABIOGENESIS, BIOMASS_COLLAPSE, BiotaCauseCode
from ecosfera_ai.engines.biota.service import BiotaEngine
from ecosfera_ai.engines.resource.contracts import load_params as resource_params
from ecosfera_ai.engines.resource.domain import (
    carrying_capacity,
    energy_available,
    habitability,
    limiting_nutrient,
    nutrients_available,
    thermal_suitability,
    water_available,
)
from ecosfera_ai.engines.resource.events import (
    CARRYING_CAPACITY_SHIFT,
    RESOURCE_SCARCITY,
    ResourceCauseCode,
)
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    AstronomySlice,
    BiotaSlice,
    ChemistrySlice,
    ClimateSlice,
    HydrologySlice,
    ResourceSlice,
    SliceRef,
    WorldStateSnapshot,
)

RESOURCE = resource_params()
BIOTA = biota_params()


def _context(snapshot: WorldStateSnapshot, engine_id: str) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, engine_id, snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
    )


def _world(
    *,
    temperature: float = 22.0,
    ocean: float = 2.0,
    freshwater: float = 0.5,
    nutrients: float = 1.0,
    solar_flux: float = 1.0,
    biomass: float = 0.0,
    resource: ResourceSlice | None = None,
) -> WorldStateSnapshot:
    return WorldStateSnapshot(
        planet_id="p",
        seed=13,
        tick=0,
        era=0,
        astronomy=AstronomySlice(solar_flux=solar_flux),
        climate=ClimateSlice(temperature=temperature),
        hydrology=HydrologySlice(ocean=ocean, freshwater=freshwater),
        chemistry=ChemistrySlice(nutrients=nutrients, nitrogen=1.0, phosphorus=1.0, sulfur=1.0),
        resource=resource or ResourceSlice(),
        biota=BiotaSlice(biomass=biomass),
    )


# --- Resource -----------------------------------------------------------------


def test_resource_declares_the_four_physical_reads_and_the_lagged_biota() -> None:
    engine = ResourceEngine()
    assert engine.writes is SliceRef.RESOURCE
    assert engine.reads == frozenset(
        {SliceRef.ASTRONOMY, SliceRef.CLIMATE, SliceRef.HYDROLOGY, SliceRef.CHEMISTRY}
    )
    # O Biota roda DEPOIS: o consumo contabilizado é o da biomassa anterior.
    assert engine.lagged_reads == frozenset({SliceRef.BIOTA})


def test_the_scarcest_element_is_what_limits_growth() -> None:
    """Lei do mínimo: o fósforo escasso limita, por mais nitrogênio que haja."""
    plenty = limiting_nutrient(100.0, 100.0, 100.0, RESOURCE)
    starved = limiting_nutrient(100.0, 0.0, 100.0, RESOURCE)
    assert plenty > 1.0
    assert starved == pytest.approx(0.0)

    assert nutrients_available(5.0, 100.0, 0.0, 100.0, RESOURCE) == pytest.approx(0.0)


def test_habitability_is_multiplicative_so_one_zero_zeroes_everything() -> None:
    """Nenhum excesso compensa um recurso ausente — é a lei do mínimo."""
    assert habitability(22.0, 0.0, 10.0, 10.0, RESOURCE) == pytest.approx(0.0)
    assert habitability(22.0, 10.0, 0.0, 10.0, RESOURCE) == pytest.approx(0.0)
    assert habitability(22.0, 10.0, 10.0, 0.0, RESOURCE) == pytest.approx(0.0)
    assert habitability(22.0, 10.0, 10.0, 10.0, RESOURCE) > 0.9


def test_thermal_suitability_peaks_at_the_optimum_and_falls_symmetrically() -> None:
    optimum = RESOURCE.optimal_temperature
    delta = RESOURCE.temperature_tolerance / 2
    assert thermal_suitability(optimum, RESOURCE) == pytest.approx(1.0)
    assert thermal_suitability(optimum - delta, RESOURCE) == pytest.approx(
        thermal_suitability(optimum + delta, RESOURCE)
    )
    assert thermal_suitability(optimum + 5 * delta, RESOURCE) < 0.05


def test_the_thermal_and_water_terms_match_the_ported_life_subsystem() -> None:
    """O porte não recalibrou a ciência que já existia (ADR 0013).

    Os valores de ótimo, tolerância e requisito hídrico são os do `life`
    determinístico; o que o M2 acrescentou foram os fatores de nutriente e
    energia, que não existiam.
    """
    assert RESOURCE.optimal_temperature == 22.0
    assert RESOURCE.temperature_tolerance == 15.0
    assert RESOURCE.water_requirement == 0.2
    assert RESOURCE.max_carrying_capacity == 100.0


def test_salt_water_is_only_partly_usable() -> None:
    """A água doce entra inteira; a oceânica, em parte."""
    assert water_available(10.0, 1.0, RESOURCE) == pytest.approx(
        1.0 + RESOURCE.ocean_accessibility * 10.0
    )


def test_energy_available_scales_with_insolation() -> None:
    assert energy_available(2.0, RESOURCE) == pytest.approx(2 * energy_available(1.0, RESOURCE))
    assert energy_available(0.0, RESOURCE) == 0.0


def test_capacity_is_never_negative() -> None:
    assert carrying_capacity(-1.0, RESOURCE) == 0.0


def test_a_hostile_planet_gets_no_capacity() -> None:
    result = ResourceEngine().tick(_context(_world(temperature=-200.0), "resource"))
    assert result.delta.values["carrying_capacity"] == pytest.approx(0.0, abs=1e-9)


def test_capacity_shift_uses_relative_change_not_absolute() -> None:
    """Cinco unidades significam coisas opostas em planetas de escalas diferentes."""
    engine = ResourceEngine()
    # Capacidade anterior alta e ambiente igual: variação relativa desprezível.
    world = _world(resource=ResourceSlice(carrying_capacity=95.0))
    quiet = engine.tick(_context(world, "resource"))
    assert all(e.event_type != CARRYING_CAPACITY_SHIFT for e in quiet.events)

    # Anterior pequena, ambiente ótimo: salto relativo enorme, evento.
    world = _world(resource=ResourceSlice(carrying_capacity=1.0))
    jump = engine.tick(_context(world, "resource"))
    shifts = [e for e in jump.events if e.event_type == CARRYING_CAPACITY_SHIFT]
    assert shifts
    assert shifts[0].cause_code is ResourceCauseCode.HABITABILITY_GAIN


def test_scarcity_names_one_limiting_resource_not_three() -> None:
    """A lei do mínimo diz que há UM limitante; nomeá-lo é a informação."""
    engine = ResourceEngine()
    world = _world(ocean=0.0, freshwater=0.0, nutrients=0.0, solar_flux=0.0)
    result = engine.tick(_context(world, "resource"))
    scarcity = [e for e in result.events if e.event_type == RESOURCE_SCARCITY]
    assert len(scarcity) <= 1


def test_the_resource_engine_never_writes_outside_its_slice() -> None:
    result = ResourceEngine().tick(_context(_world(), "resource"))
    assert result.delta.writes is SliceRef.RESOURCE
    assert set(result.delta.values) <= {
        "water_available",
        "nutrients_available",
        "energy_available",
        "carrying_capacity",
        "consumed",
    }


# --- Biota (PROVISÓRIO — ADR 0013) -------------------------------------------


def test_biota_only_reads_the_capacity() -> None:
    """Ele não sabe o que é temperatura, água ou nutriente — e é por isso que a
    fronteira física/biologia se sustenta."""
    engine = BiotaEngine()
    assert engine.writes is SliceRef.BIOTA
    assert engine.reads == frozenset({SliceRef.RESOURCE})
    assert engine.lagged_reads == frozenset()


def test_the_abiogenesis_threshold_is_the_ported_one_reparameterised() -> None:
    """`h >= 0,35` virou `capacidade >= 35`: mesma desigualdade (ADR 0013).

    A capacidade é `100 × h`, então o limiar em unidades de capacidade é o
    produto do limiar de habitabilidade pelo máximo — reparametrização, não
    mudança de ciência.
    """
    assert BIOTA.abiogenesis_capacity == pytest.approx(RESOURCE.max_carrying_capacity * 0.35)


def test_life_emerges_once_and_only_above_the_threshold() -> None:
    below = BIOTA.abiogenesis_capacity * 0.5
    above = BIOTA.abiogenesis_capacity * 1.5
    assert emergence(0.0, below, BIOTA) == 0.0
    assert emergence(0.0, above, BIOTA) == BIOTA.emergence_amount
    # Já havendo vida, não há nova abiogênese.
    assert emergence(1.0, above, BIOTA) == 0.0


def test_growth_is_logistic_and_stops_at_the_capacity() -> None:
    capacity = 100.0
    assert logistic_growth(1.0, capacity, BIOTA) > 0.0
    assert logistic_growth(capacity, capacity, BIOTA) == pytest.approx(0.0)
    # Acima da capacidade, a população decresce de volta a ela.
    assert logistic_growth(capacity * 1.5, capacity, BIOTA) < 0.0


def test_an_unviable_planet_kills_the_life_it_had() -> None:
    assert logistic_growth(10.0, 0.0, BIOTA) == pytest.approx(-BIOTA.growth_rate * 10.0)


def test_abiogenesis_emits_the_milestone_chained_to_the_resource() -> None:
    world = _world(resource=ResourceSlice(carrying_capacity=BIOTA.abiogenesis_capacity * 2))
    result = BiotaEngine().tick(_context(world, "biota"))
    births = [e for e in result.events if e.event_type == ABIOGENESIS]
    assert births
    assert births[0].cause_code is BiotaCauseCode.HABITABILITY_THRESHOLD


def test_collapse_fires_when_the_capacity_vanishes() -> None:
    world = _world(biomass=0.05, resource=ResourceSlice(carrying_capacity=0.0))
    # Sem ruído, o declínio é limpo: isola o colapso do sorteio demográfico.
    result = BiotaEngine(replace(BIOTA, growth_rate=1.0, growth_variability=0.0)).tick(
        _context(world, "biota")
    )
    collapses = [e for e in result.events if e.event_type == BIOMASS_COLLAPSE]
    assert collapses
    assert collapses[0].cause_code is BiotaCauseCode.CAPACITY_COLLAPSE


def test_biomass_never_goes_negative() -> None:
    world = _world(biomass=1e-6, resource=ResourceSlice(carrying_capacity=0.0))
    result = BiotaEngine().tick(_context(world, "biota"))
    assert 1e-6 + result.delta.values["biomass"] >= 0.0


def test_the_biota_engine_writes_only_the_biomass() -> None:
    """`species_richness` fica com a camada emergente do M3 — escrevê-la aqui
    seria fingir uma riqueza que este Engine provisório não modela."""
    world = _world(resource=ResourceSlice(carrying_capacity=50.0))
    result = BiotaEngine().tick(_context(world, "biota"))
    assert result.delta.writes is SliceRef.BIOTA
    assert set(result.delta.values) == {"biomass"}
