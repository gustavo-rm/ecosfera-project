"""ANTI-REGRESSÃO: a insolação tem dono, e o clima a consome de verdade.

Este arquivo existe por causa de uma armadilha concreta do M2. A
`AstronomySlice` foi criada no M0 e ficou **órfã de escritor**: quem integrava a
órbita era o subsystem `physics`, dentro do adaptador legado. Ao aposentar o
adaptador (ADR 0014) sem portar `physics`, `solar_flux` teria ficado em zero para
sempre — e nada quebraria.

O silêncio é o problema. `incident_flux()` tem um recuo deliberado para
`params.insolation` quando o fluxo é zero, pensado para permitir testar o clima
isoladamente. Com a fatia órfã, esse recuo viraria o caminho de PRODUÇÃO: o
planeta perderia estações e excentricidade, a temperatura ficaria plausível, os
testes continuariam verdes, e ninguém saberia que a astronomia sumiu.

Daí as três asserções aqui: alguém ESCREVE a fatia, o valor VARIA ao longo do
tempo (a órbita está viva), e o clima LÊ o world-state em vez do recuo.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.astronomy.contracts import ENGINE_ID as ASTRONOMY_ID
from ecosfera_ai.engines.astronomy.contracts import load_params as astronomy_params
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.climate.contracts import load_params as climate_params
from ecosfera_ai.engines.climate.domain import absorbed_energy, incident_flux
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    AstronomySlice,
    AtmosphereSlice,
    SliceRef,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
CLIMATE = climate_params()


def _trail(ticks: int = 140, seed: int = 2027) -> list[WorldStateSnapshot]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("flux", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return trail


def test_the_astronomy_slice_has_exactly_one_writer() -> None:
    """Sem dono, `solar_flux` ficaria zerado para sempre e nada acusaria."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert planet.registry.owned_slices[SliceRef.ASTRONOMY] == ASTRONOMY_ID


def test_solar_flux_is_written_and_stays_positive() -> None:
    trail = _trail()
    assert all(s.astronomy.solar_flux > 0.0 for s in trail[1:]), "a estrela apagou"


def test_the_orbit_is_alive_across_eras() -> None:
    """As coordenadas orbitais VARIAM: o integrador está de fato rodando.

    Um `solar_flux` positivo mas congelado seria indistinguível de uma constante
    escrita à mão — é a variação que prova que existe uma órbita.
    """
    trail = _trail()
    xs = {round(s.astronomy.orbital_x, 6) for s in trail}
    ys = {round(s.astronomy.orbital_y, 6) for s in trail}
    assert len(xs) > 10 and len(ys) > 10, "a órbita não se moveu"

    # Meia volta separa posições opostas: a órbita fecha, não deriva.
    assert min(s.astronomy.orbital_x for s in trail) < 0.0
    assert max(s.astronomy.orbital_x for s in trail) > 0.0


def test_an_eccentric_orbit_makes_the_insolation_vary() -> None:
    """Estações: com excentricidade, a irradiância recebida oscila entre eras.

    Com `eccentricity_kick = 0` a órbita é circular e o fluxo é constante por
    construção — é o padrão. O que este teste fixa é que o mecanismo existe e
    responde ao parâmetro: sem Astronomy Engine, mexer nele não faria nada.
    """
    from ecosfera_ai.engines.astronomy.domain import integrate, solar_flux_at

    params = replace(astronomy_params(), eccentricity_kick=0.35)
    x, y, vx, vy = 1.0, 0.0, 0.0, (1.0 + params.eccentricity_kick)
    fluxes = []
    for _ in range(400):
        x, y, vx, vy = integrate(x, y, vx, vy, params)
        fluxes.append(solar_flux_at(x, y, params))

    assert max(fluxes) > min(fluxes) * 1.2, "órbita elíptica sem variação de insolação"


def test_climate_reads_the_world_state_not_the_fallback() -> None:
    """O recuo para `params.insolation` NÃO pode ser o caminho de produção.

    Se o Climate ignorasse a `AstronomySlice`, dois fluxos bem diferentes
    produziriam a mesma energia absorvida — e é exatamente esse empate que a
    ausência de escritor causaria.
    """

    def _energy(flux: float) -> float:
        snapshot = WorldStateSnapshot(
            planet_id="p",
            seed=3,
            tick=0,
            era=0,
            astronomy=AstronomySlice(solar_flux=flux),
            atmosphere=AtmosphereSlice(co2=280.0),
        )
        ctx = TickContext(
            snapshot=snapshot,
            rng=rng_for(snapshot.seed, "climate", snapshot.tick),
            tick=0,
            era=0,
            budget=TickBudget(),
        )
        result = ClimateEngine().tick(ctx)
        return result.delta.values["energy"]

    dim, bright = _energy(0.5), _energy(1.5)
    assert dim != bright, "o clima não está lendo a insolação da astronomia"
    assert bright > dim, "mais irradiância tem de absorver mais energia"

    # E o valor bate com a irradiância do world-state, não com a de referência.
    assert bright == pytest.approx(absorbed_energy(1.5, 0.0, CLIMATE))
    assert bright != pytest.approx(absorbed_energy(CLIMATE.insolation, 0.0, CLIMATE))


def test_the_fallback_still_protects_isolated_unit_tests() -> None:
    """O recuo continua existindo — só deixou de ser o que produção usa."""
    assert incident_flux(0.0, CLIMATE) == CLIMATE.insolation
    assert incident_flux(0.75, CLIMATE) == 0.75


def test_climate_declares_astronomy_as_a_same_tick_read() -> None:
    """Defasar a irradiância atrasaria a estação do planeta em um tick."""
    engine = ClimateEngine()
    assert SliceRef.ASTRONOMY in engine.reads
    assert SliceRef.ASTRONOMY not in engine.lagged_reads
