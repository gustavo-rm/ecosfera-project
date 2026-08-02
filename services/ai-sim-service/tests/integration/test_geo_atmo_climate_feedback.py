"""O feedback físico do M1 EMERGE ao longo dos ticks — não é programado.

Nenhum Engine contém a regra "vulcanismo aquece o planeta". A geologia
desgaseifica, a atmosfera integra e irradia, o clima responde ao que recebe. O
aquecimento é consequência da composição, e é isso que este arquivo verifica.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.astronomy.service import AstronomyEngine
from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.chemistry.service import ChemistryEngine
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.composition import build_planet_engine, planet_invariants
from ecosfera_ai.engines.ecology.service import EcologyEngine
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.engines.geology.contracts import load_params as geology_params
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.world_state import SliceRef, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 60


def _run(seed: int = 2027, ticks: int = TICKS) -> list[WorldStateSnapshot]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("feedback", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    return trail


def test_the_whole_chain_rises_together() -> None:
    """vulcanismo↑ ⇒ CO2↑ ⇒ forçamento↑ ⇒ temperatura↑, ao longo da série."""
    trail = _run()
    first, last = trail[1], trail[-1]

    assert last.geology.co2_flux > 0.0
    assert last.atmosphere.co2 > first.atmosphere.co2
    assert last.atmosphere.greenhouse_forcing > first.atmosphere.greenhouse_forcing
    assert last.climate.temperature > first.climate.temperature


def test_carbon_stock_is_monotonic_while_the_source_beats_the_sinks() -> None:
    trail = _run()
    stocks = [s.atmosphere.co2 for s in trail[1:]]
    assert stocks == sorted(stocks), "o estoque não deveria oscilar nesta janela"


def test_forcing_follows_the_stock_and_saturates() -> None:
    """A resposta logarítmica: o mesmo ganho de CO2 rende cada vez menos."""
    trail = _run()
    early = trail[10].atmosphere, trail[20].atmosphere
    late = trail[-11].atmosphere, trail[-1].atmosphere

    early_gain = early[1].greenhouse_forcing - early[0].greenhouse_forcing
    late_gain = late[1].greenhouse_forcing - late[0].greenhouse_forcing
    assert early_gain > 0.0 and late_gain > 0.0
    assert late_gain < early_gain, "sem saturação, seria a resposta linear de antes"


def test_a_quiet_planet_does_not_warm() -> None:
    """Contraprova: zerando a desgaseificação, a cadeia inteira para.

    Sem ela o teste anterior poderia estar apenas observando uma deriva
    qualquer — é este que amarra o aquecimento à FONTE geológica.
    """
    planet = PlanetEngine(
        EngineRegistry.of(
            [
                AstronomyEngine(),
                GeologyEngine(replace(geology_params(), outgassing_base=0.0)),
                ChemistryEngine(),
                AtmosphereEngine(),
                ClimateEngine(),
                HydrologyEngine(),
                ResourceEngine(),
                EvolutionEngine(),
                EcologyEngine(),
            ]
        ),
        invariants=planet_invariants(
            PARAMS.bounds, water_tolerance=hydrology_params().conservation_tolerance
        ),
    )

    snapshot = snapshot_of(initial_state(PlanetSeed("quiet", 2027), PARAMS))
    start = snapshot.atmosphere.co2
    for _ in range(TICKS):
        snapshot = planet.tick(snapshot).snapshot

    assert snapshot.atmosphere.co2 < start, "sem fonte, só resta o intemperismo"
    assert snapshot.atmosphere.greenhouse_forcing < 0.0


def test_each_arrow_crosses_only_through_the_world_state() -> None:
    """Cada Engine escreve a própria fatia e nada além dela."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert planet.registry.owned_slices == {
        SliceRef.ASTRONOMY: "astronomy",
        SliceRef.GEOLOGY: "geology",
        SliceRef.CHEMISTRY: "chemistry",
        SliceRef.ATMOSPHERE: "atmosphere",
        SliceRef.CLIMATE: "climate",
        SliceRef.HYDROLOGY: "hydrology",
        SliceRef.RESOURCE: "resource",
        # A biota tem DOIS produtores, então duas fatias com um dono cada — a
        # regra de um-escritor da moldura força a divisão (ADR 0016).
        SliceRef.BIOTA: "evolution",
        SliceRef.ECOLOGY: "ecology",
    }
    # Desde o M2 nao sobra fatia sem dono: a `LegacySlice` deixou de existir.
    assert set(planet.registry.owned_slices) == set(SliceRef)


def test_the_feedback_is_reproducible_under_the_same_seed() -> None:
    assert [s.climate.temperature for s in _run(seed=99)] == [
        s.climate.temperature for s in _run(seed=99)
    ]


def test_different_seeds_produce_different_planets() -> None:
    assert _run(seed=1)[-1].climate.temperature != _run(seed=2)[-1].climate.temperature


def test_the_planet_stays_physically_sane() -> None:
    """Sanidade científica: nada de estoque negativo nem fração fora de faixa."""
    for snapshot in _run():
        assert snapshot.atmosphere.co2 >= 0.0
        assert snapshot.geology.volcanism >= 0.0
        assert 0.0 <= snapshot.hydrology.ice_fraction <= 1.0
        assert 0.0 <= snapshot.geology.relief <= 1.0
        assert snapshot.climate.temperature == pytest.approx(
            snapshot.climate.temperature
        )  # não é NaN
        # Estoques do M2: nenhum reservatório pode ficar negativo.
        for reservoir in ("ocean", "ice", "vapour", "freshwater"):
            assert getattr(snapshot.hydrology, reservoir) >= 0.0
        assert snapshot.chemistry.ocean_carbon >= 0.0
        assert snapshot.resource.carrying_capacity >= 0.0
        assert snapshot.biota.biomass >= 0.0
