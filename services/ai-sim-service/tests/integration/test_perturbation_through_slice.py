"""A perturbação viaja pelo Canal A, e um-dono-por-fatia continua de pé (ADR 0018).

O Event Engine descreve a CAUSA; cada Engine afetado decide o EFEITO sobre a
própria fatia. É o que permite ao Atmosphere reagir à poeira sem saber que existe
um catálogo de eventos, e ao Event Engine perturbar o clima sem escrever nele.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
from ecosfera_ai.engines.event.contracts import WRITES as EVENT_WRITES
from ecosfera_ai.shared_kernel.world_state import EventSlice, SliceRef
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _settled(ticks: int = 150):
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("perturb", 2027), PARAMS))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
    return planet, snapshot


# --- A regra estrutural -------------------------------------------------------


def test_the_event_engine_owns_exactly_one_slice_and_it_is_its_own() -> None:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert planet.registry.owned_slices[SliceRef.EVENT] == "event"
    assert EVENT_WRITES is SliceRef.EVENT
    assert set(planet.registry.owned_slices) == set(SliceRef), "sobrou fatia sem dono"


def test_the_event_engine_writes_no_slice_it_perturbs() -> None:
    """A prova da rota: ele perturba clima, água e geologia sem escrevê-los."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    event = next(e for e in planet.registry.engines if e.engine_id == "event")
    for perturbed in (SliceRef.CLIMATE, SliceRef.HYDROLOGY, SliceRef.GEOLOGY, SliceRef.ATMOSPHERE):
        assert event.writes is not perturbed


def test_the_affected_engines_declare_the_lagged_read() -> None:
    """O Event roda por último: quem o lê, lê do tick anterior — e declara."""
    from ecosfera_ai.engines.climate.contracts import LAGGED_READS as CLIMATE_LAGGED
    from ecosfera_ai.engines.ecology.contracts import LAGGED_READS as ECOLOGY_LAGGED
    from ecosfera_ai.engines.evolution.contracts import LAGGED_READS as EVOLUTION_LAGGED
    from ecosfera_ai.engines.geology.contracts import LAGGED_READS as GEOLOGY_LAGGED
    from ecosfera_ai.engines.hydrology.contracts import LAGGED_READS as HYDROLOGY_LAGGED

    for name, declared in (
        ("climate", CLIMATE_LAGGED),
        ("hydrology", HYDROLOGY_LAGGED),
        ("geology", GEOLOGY_LAGGED),
        ("ecology", ECOLOGY_LAGGED),
        ("evolution", EVOLUTION_LAGGED),
    ):
        assert SliceRef.EVENT in declared, f"{name} lê a EventSlice sem declarar a defasagem"

    assert ENGINE_ORDER[-1] == "event", "o Event deixou de fechar o tick"


# --- O efeito, e não só a declaração ------------------------------------------


def test_cooling_forcing_actually_cools_the_planet() -> None:
    """Injeta a perturbação na fatia e exige que o Climate a incorpore."""
    planet, settled = _settled()

    calm = planet.tick(settled, publish=False).snapshot
    struck = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(cooling_forcing=6.0)), publish=False
    ).snapshot

    assert struck.climate.temperature < calm.climate.temperature, (
        "o resfriamento publicado na EventSlice não chegou à temperatura"
    )


def test_drought_actually_suppresses_precipitation() -> None:
    planet, settled = _settled()

    calm = planet.tick(settled, publish=False).snapshot
    dry = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(drought_intensity=0.8)), publish=False
    ).snapshot

    assert dry.hydrology.precipitation < calm.hydrology.precipitation, (
        "a seca publicada na EventSlice não reduziu a precipitação"
    )


def test_the_drought_moves_water_without_destroying_it() -> None:
    """Suprimir chuva não destrói água: o que não chove fica como vapor."""
    planet, settled = _settled()
    dry = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(drought_intensity=0.9)), publish=False
    ).snapshot

    before = sum(getattr(settled.hydrology, r) for r in ("ocean", "ice", "vapour", "freshwater"))
    after = sum(getattr(dry.hydrology, r) for r in ("ocean", "ice", "vapour", "freshwater"))
    assert after == pytest.approx(before, rel=1e-6), (
        "a seca criou ou destruiu água — ela deve apenas redistribuí-la"
    )


def test_supervolcanic_intensity_raises_the_geological_outgassing() -> None:
    planet, settled = _settled()

    calm = planet.tick(settled, publish=False).snapshot
    erupting = planet.tick(
        settled.with_slice(SliceRef.EVENT, EventSlice(supervolcanic_intensity=1.0)), publish=False
    ).snapshot

    assert erupting.geology.co2_flux > calm.geology.co2_flux, (
        "o supervulcanismo não chegou ao fluxo de carbono da geologia"
    )


def test_a_clean_event_slice_changes_nothing() -> None:
    """Sem perturbação ativa, o tick é idêntico — a rota não vaza."""
    planet, settled = _settled()
    plain = planet.tick(settled, publish=False).snapshot
    zeroed = planet.tick(settled.with_slice(SliceRef.EVENT, EventSlice()), publish=False).snapshot
    assert plain.climate.temperature == pytest.approx(zeroed.climate.temperature)
    assert plain.geology.co2_flux == pytest.approx(zeroed.geology.co2_flux)
