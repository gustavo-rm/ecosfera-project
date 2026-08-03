"""Q11 (validação Tássia): capacidade de suporte em TODOS os níveis tróficos.

Antes do M4 só o produtor tinha teto: herbívoro e predador cresciam apenas pelo
que conseguiam converter, sem limite ambiental algum. Um ambiente pobre podia
sustentar uma pirâmide inteira de consumidores desde que a predação corresse bem.

A FORMA do teto é decisão de engenharia sobre o princípio validado: o teto de
cada consumidor é fração do nível ABAIXO dele, não do ambiente inteiro. Um teto
plano sobre a capacidade ambiental foi tentado e medido — travava os herbívoros
e levava os predadores à extinção por fome, achatando a cadeia em dois níveis.
Ancorar na presa é a forma eltoniana do mesmo limite (ADR 0019, D2).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import _renormalised, _room, _trophic_step
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

ECOLOGY = ecology_params()
PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _ctx(tick: int = 5) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("q11", 2027), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=0,
        budget=PARAMS.engine_budget,
    )


# --- O termo de teto, isolado -------------------------------------------------


def test_room_is_the_verhulst_term() -> None:
    assert _room(0.0, 100.0) == pytest.approx(1.0)
    assert _room(50.0, 100.0) == pytest.approx(0.5)
    assert _room(100.0, 100.0) == pytest.approx(0.0)


def test_room_never_goes_negative() -> None:
    """Acima do teto o nível PARA de ganhar; quem o reduz é a mortalidade.

    Um ganho negativo seria uma segunda via de morte, contabilizada além da
    mortalidade que já existe — a mesma dupla contagem, de outro nome.
    """
    assert _room(500.0, 100.0) == 0.0


def test_a_vanished_ceiling_admits_no_growth() -> None:
    """Sem presa, não há espaço: o consumidor não ganha do nada."""
    assert _room(1.0, 0.0) == 0.0


# --- O teto morde, em todos os níveis -----------------------------------------


def test_consumers_are_capped_by_the_level_below_them() -> None:
    """Herbívoro farto contra produtor escasso: o ganho é amortecido."""
    ctx = _ctx()
    scarce_prey = _trophic_step((10.0, 60.0, 1.0), 200.0, ECOLOGY, ctx)
    ample_prey = _trophic_step((200.0, 60.0, 1.0), 200.0, ECOLOGY, ctx)
    assert ample_prey[1] > scarce_prey[1], (
        "o herbívoro cresce igual com presa escassa e farta: o teto não morde"
    )


def test_the_predator_is_capped_by_the_herbivore() -> None:
    ctx = _ctx()
    scarce = _trophic_step((200.0, 2.0, 5.0), 300.0, ECOLOGY, ctx)
    ample = _trophic_step((200.0, 90.0, 5.0), 300.0, ECOLOGY, ctx)
    assert ample[2] > scarce[2], "o predador ignora a abundância de presa"


def test_the_producer_keeps_its_environmental_ceiling() -> None:
    """Q11 ESTENDE o teto; não o tira de quem já o tinha."""
    ctx = _ctx()
    roomy = _trophic_step((100.0, 0.0, 0.0), 500.0, ECOLOGY, ctx)
    packed = _trophic_step((495.0, 0.0, 0.0), 500.0, ECOLOGY, ctx)

    # Comparativo, e não um limiar absoluto: o passo carrega ruído demográfico
    # proporcional à população, então perto do teto o valor absoluto ainda sobe
    # um pouco. O que a capacidade governa é a FRAÇÃO de crescimento.
    assert (roomy[0] - 100.0) / 100.0 > (packed[0] - 495.0) / 495.0, (
        "o produtor cresce à mesma taxa vazio e cheio: ignorou a capacidade"
    )


# --- Conservação e forma da pirâmide ------------------------------------------


def test_the_capacity_term_does_not_create_biomass() -> None:
    """A renormalização segue amarrando a soma ao total da Evolution."""
    ctx = _ctx()
    levels = _trophic_step((120.0, 40.0, 8.0), 300.0, ECOLOGY, ctx)
    renormalised = _renormalised(levels, 168.0, ECOLOGY)
    assert sum(renormalised) == pytest.approx(168.0, abs=1e-9)


def test_the_pyramid_keeps_three_levels_over_a_long_run() -> None:
    """A regressão que a forma plana causava: predador extinto por fome.

    É o teste que distingue as duas formas de teto — a plana passava em todos os
    testes de unidade acima e matava o topo da cadeia no planeta.
    """
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("pyramid", 2027), PARAMS))
    for _ in range(400):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    ecology = snapshot.ecology
    assert ecology.producer_biomass > 0.0
    assert ecology.herbivore_biomass > 0.0
    assert ecology.predator_biomass > 0.0, (
        "os predadores se extinguiram: o teto está estrangulando o topo da cadeia"
    )


def test_the_pyramid_does_not_invert() -> None:
    """Elton (1927): cada nível carrega menos biomassa que o de baixo."""
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("pyramid", 2027), PARAMS))
    for _ in range(400):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    e = snapshot.ecology
    assert e.producer_biomass > e.herbivore_biomass > e.predator_biomass, (
        f"pirâmide invertida: {e.producer_biomass:.1f} / {e.herbivore_biomass:.1f} "
        f"/ {e.predator_biomass:.1f}"
    )


def test_the_share_is_versioned_data_not_a_constant() -> None:
    assert 0.0 < ECOLOGY.consumer_capacity_share <= 1.0
    tightened = replace(ECOLOGY, consumer_capacity_share=0.1)
    ctx = _ctx()
    loose = _trophic_step((100.0, 40.0, 2.0), 300.0, ECOLOGY, ctx)
    tight = _trophic_step((100.0, 40.0, 2.0), 300.0, tightened, ctx)
    assert tight[1] < loose[1], "o parâmetro não governa o teto"
