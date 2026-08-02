"""Métodos puros do estado do planeta e carga de parâmetros (dados versionados)."""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.domain.feedback.models import Direction
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import (
    PlanetSeed,
    PlanetState,
    StateBounds,
    StateDelta,
)

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _state(
    *,
    temperature: float = 10.0,
    co2: float = 100.0,
    water: float = 1.0,
    ice_cover: float = 0.2,
    biomass: float = 0.1,
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


def test_params_expose_version_and_scientific_values() -> None:
    assert PARAMS.version >= 1
    assert PARAMS.bounds.ice_cover_max == 1.0
    # A ciência por domínio saiu deste YAML no M2 e vive no `params.yaml` de cada
    # Engine (ADR 0014); o que sobrou aqui é o que não pertence a Engine algum.
    assert PARAMS.timeline.era_length > 0
    assert PARAMS.initial_state.co2 > 0.0


def test_initial_state_comes_from_params_not_seed() -> None:
    a = initial_state(PlanetSeed("a", 1), PARAMS)
    b = initial_state(PlanetSeed("b", 999), PARAMS)
    # a semente não altera o estado inicial (só a estocasticidade dos ticks)
    assert a.temperature == b.temperature == PARAMS.initial_state.temperature
    assert a.tick == 0
    assert a.seed == 1


def test_apply_clamps_non_negative_and_ice_range() -> None:
    bounds = StateBounds()
    over_drained = _state().apply(
        StateDelta(d_co2=-999.0, d_water=-999.0, d_ice_cover=-999.0, d_biomass=-999.0),
        bounds,
    )
    assert over_drained.co2 == 0.0
    assert over_drained.water == 0.0
    assert over_drained.ice_cover == 0.0
    assert over_drained.biomass == 0.0
    # gelo não ultrapassa 1.0
    assert _state().apply(StateDelta(d_ice_cover=999.0), bounds).ice_cover == 1.0


def test_delta_addition_is_componentwise() -> None:
    total = StateDelta(d_co2=1.0, d_temperature=2.0) + StateDelta(d_co2=0.5, d_water=3.0)
    assert total.d_co2 == 1.5
    assert total.d_temperature == 2.0
    assert total.d_water == 3.0


def test_observe_reports_relative_change_and_direction() -> None:
    before = _state(co2=100.0, temperature=10.0)
    after = before.apply(StateDelta(d_co2=50.0), StateBounds()).advanced()
    observations = {o.variable: o for o in after.observe(before)}
    assert observations["co2"].delta == 0.5  # +50 sobre 100
    assert observations["co2"].direction is Direction.UP
    # variáveis inalteradas não viram observação
    assert "temperature" not in observations
