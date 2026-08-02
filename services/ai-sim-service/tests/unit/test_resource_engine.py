"""Resource Engine: o orçamento biológico que a física oferece (M2/M3).

O Resource DERIVA a capacidade de suporte; quem a CONSOME é a Evolution desde o
M3 (o Biota provisório do M2 foi removido — ADR 0016). A fronteira é a mesma e
continua sendo o assunto: capacidade é LIMITE, biomassa é OCUPAÇÃO.
"""

from __future__ import annotations

import pytest

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
