"""Funções de aptidão ambiental: puras, coerentes e dentro das faixas (RF-031)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ecosfera_ai.simulation_engine.biology.fitness import (
    crowding_penalty,
    energy_suitability,
    environmental_fitness,
    maintenance_penalty,
    thermal_suitability,
    water_suitability,
)
from ecosfera_ai.simulation_engine.biology.genome import (
    TROPHIC_HERBIVORE,
    TROPHIC_PRODUCER,
    Genome,
)
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
STATE = initial_state(PlanetSeed("p", 1), PARAMS)
F = PARAMS.fitness


def _genome(**over: float) -> Genome:
    base = {
        "temp_optimum": 14.0,
        "temp_tolerance": 10.0,
        "water_need": 0.2,
        "size": 0.5,
        "metabolism": 0.5,
        "trophic_level": float(TROPHIC_PRODUCER),
    }
    base.update(over)
    return Genome(**base).clamped()  # type: ignore[arg-type]


def test_species_adapted_to_the_climate_is_fitter() -> None:
    adapted = _genome(temp_optimum=STATE.temperature)
    maladapted = _genome(temp_optimum=STATE.temperature + 40.0)
    assert environmental_fitness(adapted, STATE, F) > environmental_fitness(maladapted, STATE, F)


def test_fitness_always_lies_within_zero_and_one() -> None:
    extremes = [
        _genome(temp_optimum=-40.0, metabolism=3.0, size=100.0),
        _genome(temp_optimum=80.0, water_need=2.0),
        _genome(temp_optimum=STATE.temperature, metabolism=0.05, size=0.01),
    ]
    for genome in extremes:
        value = environmental_fitness(genome, STATE, F, occupancy=0.5)
        assert 0.0 <= value <= 1.0


def test_thermal_suitability_peaks_at_the_optimum() -> None:
    perfect = _genome(temp_optimum=STATE.temperature)
    assert thermal_suitability(perfect, STATE) == 1.0
    colder = _genome(temp_optimum=STATE.temperature - 30.0)
    assert thermal_suitability(colder, STATE) < 0.2


def test_specialists_lose_fitness_faster_than_generalists() -> None:
    """Tolerância estreita é a mecânica que transforma aquecimento em extinção."""
    warmed = replace(STATE, temperature=STATE.temperature + 12.0)
    specialist = _genome(temp_optimum=STATE.temperature, temp_tolerance=5.0)
    generalist = _genome(temp_optimum=STATE.temperature, temp_tolerance=40.0)
    assert thermal_suitability(specialist, warmed) < thermal_suitability(generalist, warmed)


def test_water_suitability_saturates_and_never_exceeds_one() -> None:
    thirsty = _genome(water_need=10.0)
    modest = _genome(water_need=0.01)
    assert water_suitability(thirsty, STATE) < water_suitability(modest, STATE)
    assert water_suitability(modest, STATE) == 1.0
    assert water_suitability(_genome(water_need=0.0), STATE) == 1.0


def test_only_producers_depend_on_sunlight() -> None:
    producer = _genome(trophic_level=float(TROPHIC_PRODUCER))
    herbivore = _genome(trophic_level=float(TROPHIC_HERBIVORE))
    dark = replace(STATE, solar_flux=0.01)
    assert energy_suitability(producer, dark, F) < 1.0
    # Consumidores tiram energia da cadeia trófica, resolvida na ecologia.
    assert energy_suitability(herbivore, dark, F) == 1.0


def test_expensive_bodies_pay_a_maintenance_penalty() -> None:
    cheap = _genome(metabolism=0.05, size=0.01)
    costly = _genome(metabolism=3.0, size=100.0)
    assert maintenance_penalty(cheap, F) > maintenance_penalty(costly, F)
    assert 0.0 < maintenance_penalty(costly, F) <= 1.0


def test_crowding_reduces_fitness_monotonically() -> None:
    assert crowding_penalty(0.0, F) == 1.0
    assert crowding_penalty(0.5, F) > crowding_penalty(2.0, F)


def test_fitness_is_pure() -> None:
    """Sem RNG e sem estado: chamar duas vezes dá exatamente o mesmo número."""
    genome = _genome()
    assert environmental_fitness(genome, STATE, F) == environmental_fitness(genome, STATE, F)
