"""O teto eltoniano do M4 NÃO é furado pela onivoria.

O risco declarado da fase: um generalista que drena dois poços poderia ganhar
capacidade "de graça", furando o teto por nível (Q11, ADR 0019 §6) e invertendo
a pirâmide (Elton, 1927). Estes testes exigem que o teto siga mordendo o ganho
TOTAL do predador — venha ele de uma fonte ou de duas — e que a pirâmide de
biomassa continue não invertendo ao longo de uma corrida generalista longa.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import (
    EcologyEngine,
    _renormalised,
    _trophic_step,
)
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

ECOLOGY = ecology_params()
GENERALIST = replace(
    ecology_params(),
    generalist_unlock_era=0,
    generalist_full_era=0,
    predator_diet_herbivore=0.70,
    predator_diet_producer=0.30,
)
PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _ctx(era: int, *, tick: int = 5, seed: int = 2027) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("elton", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


def test_a_predator_at_the_ceiling_gains_nothing_even_with_two_food_sources() -> None:
    """No teto, `_room` vai a 0 e o ganho zera — a onivoria não compra exceção.

    Prova direta de "sem capacidade de graça": produtor E herbívoro fartos, mas o
    predador já ocupa o teto do seu nível. Comer de dois poços não o faz crescer;
    só a mortalidade age.
    """
    params = replace(GENERALIST, demographic_noise=0.0)
    capacity = 300.0
    ceiling = capacity * params.consumer_capacity_share  # teto do nível consumidor
    predator = ceiling  # exatamente no teto: _room = 0
    out = _trophic_step((250.0, 120.0, predator), capacity, params, _ctx(era=0))
    assert out[2] < predator, "o predador cresceu no teto: a onivoria furou o limite eltoniano"
    assert out[2] == pytest.approx(predator * (1.0 - params.mortality_rate), rel=1e-9), (
        "no teto, só a mortalidade deveria mover o predador"
    )


def test_the_generalist_gain_is_still_damped_near_the_ceiling() -> None:
    """Perto do teto o generalista ganha MENOS que longe dele — o teto morde."""
    params = replace(GENERALIST, demographic_noise=0.0)
    capacity = 300.0
    scarce = _trophic_step((250.0, 120.0, 2.0), capacity, params, _ctx(era=0))
    packed_ceiling = capacity * params.consumer_capacity_share * 0.95
    packed = _trophic_step((250.0, 120.0, packed_ceiling), capacity, params, _ctx(era=0))

    scarce_growth = (scarce[2] - 2.0) / 2.0
    packed_growth = (packed[2] - packed_ceiling) / packed_ceiling
    assert scarce_growth > packed_growth, "o predador onívoro ignora a ocupação do nível"


def test_renormalisation_still_caps_generalist_consumers() -> None:
    """A soma dos consumidores segue limitada a `max_consumer_share` do total.

    A renormalização não mudou; este teste fixa que ela continua valendo sobre uma
    pirâmide de forma generalista (consumidores inflados), sem inverter a base.
    """
    biomass = 100.0
    producer, herbivore, predator = _renormalised((10.0, 60.0, 50.0), biomass, ECOLOGY)
    assert herbivore + predator <= biomass * ECOLOGY.max_consumer_share + 1e-9
    assert producer >= herbivore >= predator, "a pirâmide inverteu na renormalização"
    assert sum((producer, herbivore, predator)) == pytest.approx(biomass, abs=1e-9)


def test_the_generalist_pyramid_keeps_three_levels_and_does_not_invert() -> None:
    """Corrida longa com onivoria plena: os três níveis sobrevivem, base > topo.

    É o teste que a forma plana do teto reprovava (predador extinto por fome). Se
    a onivoria furasse o teto, o predador inflaria e a pirâmide inverteria; se o
    teto a estrangulasse, o topo morreria. Nenhum dos dois pode acontecer.

    Usa uma onivoria MODERADA (0,15): a força plena precoce (0,30 desde a era 0) é
    ela mesma desestabilizadora do topo (ADR 0030) e deixaria o predador rente a
    zero — o que testaria a desestabilização, não o teto. O que se afirma aqui é
    que o teto do M4 não estrangula NEM é furado sob onivoria real.
    """
    moderate = replace(GENERALIST, predator_diet_herbivore=0.85, predator_diet_producer=0.15)
    planet = build_quiet_planet(ecology=EcologyEngine(params=moderate))
    snapshot = snapshot_of(initial_state(PlanetSeed("pyramid", 2027), PARAMS))
    for _ in range(400):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    e = snapshot.ecology
    assert e.producer_biomass > 0.0
    assert e.herbivore_biomass > 0.0
    assert e.predator_biomass > 0.0, "o topo da cadeia se extinguiu sob onivoria"
    assert e.producer_biomass > e.herbivore_biomass > e.predator_biomass, (
        f"pirâmide invertida sob onivoria: {e.producer_biomass:.1f} / "
        f"{e.herbivore_biomass:.1f} / {e.predator_biomass:.1f}"
    )
