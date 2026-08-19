"""A predação generalista de fábrica NÃO piora a estabilidade de longo prazo.

O M4 ensinou que passar em todo teste POR TICK não basta: a instabilidade de
carbono só apareceu além de ~600 ticks (ADR 0020). A onivoria muda a
`predation_pressure`, que a Evolution lê defasada, que governa a biomassa, que
alimenta o sumidouro de carbono — logo é candidata a reabrir essa deriva.

## O que a medição mostrou (ADR 0030 §"Dependência entre fases")

A onivoria é **cientificamente correta** mas AMPLIFICA a dívida de carbono já
conhecida (ADR 0020): em força plena empurra a amplitude de CO₂ de algumas
sementes acima do teto de 60 ppm (a semente 5 vira em peso ≥ 0,04) e, no
horizonte da dívida, acelera o colapso da biosfera onde a cadeia estrita a
mantinha viva (semente 99, 3000 ticks). Amplificar uma dívida conhecida além do
teto aceito NÃO é aceitável como comportamento default, mesmo sendo correto.

Decisão do arquiteto (mesmo padrão do M1 e do M3): a MAGNITUDE da onivoria é
versionada e o default de fábrica é **conservador** (peso do produtor 0,02),
MEDIDO como não-amplificante em 16 sementes. A força plena (0,30) fica represada
até a Fase 3 pagar a dívida de carbono. Este arquivo trava as duas coisas:

* o default conservador fica sob o teto de 60 ppm nas sementes da baseline; e
* a força plena reproduz o achado (amplitude > 60, colapso da semente 99),
  marcada `xfail` — resultado ESPERADO e BLOQUEADO pela Fase 3, não um bug.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import EcologyEngine
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
# Configurações de dieta comparadas, todas na MESMA composição de engines.
DEFAULT = ecology_params()  # de fábrica: magnitude conservadora (produtor 0,02)
STRICT = replace(DEFAULT, predator_diet_herbivore=1.0, predator_diet_producer=0.0)
FULL_STRENGTH = replace(DEFAULT, predator_diet_herbivore=0.70, predator_diet_producer=0.30)

# Espelham `test_baseline_is_physics.py` (ADR 0020): horizonte de jogo válido
# MEDIDO em 500 ticks; o teto de 60 ppm vale para ESTAS sementes escolhidas — a
# população ampla de sementes já viola 60 na cadeia estrita (dívida do ADR 0020).
VALID_GAME_HORIZON = 500
BASELINE_SEEDS = (2027, 99, 11, 5)
CO2_AMPLITUDE_BOUND = 60.0
# Piso de viabilidade: uma biomassa que decai a ~1e-26 está EXTINTA na prática,
# ainda que o floor numérico deixe um resíduo tecnicamente > 0. Comparar contra
# este piso, e não contra 0, é o que separa "biosfera viva" de "colapsada".
VIABLE_BIOMASS = 1.0
ERA_LENGTH = PARAMS.timeline.era_length


def _advancing_trail(diet: object, *, ticks: int, seed: int) -> list[WorldStateSnapshot]:
    """Trajetória do JOGO REAL: as eras avançam a cada `era_length` ticks.

    A onivoria só é exercida quando as eras avançam (destrava na era 6); a
    baseline física do M4 fica na era 0 de propósito, para isolar a física.
    """
    planet: PlanetEngine = build_quiet_planet(
        ecology=EcologyEngine(params=diet)  # type: ignore[arg-type]
    )
    snapshot = snapshot_of(initial_state(PlanetSeed("horizon", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        if snapshot.tick % ERA_LENGTH == 0:
            snapshot = planet.open_next_era(snapshot)
        trail.append(snapshot)
    return trail


def _settled_co2_amplitude(trail: list[WorldStateSnapshot]) -> float:
    settled = trail[len(trail) // 2 :]
    co2 = [s.atmosphere.co2 for s in settled]
    return max(co2) - min(co2)


# --- O default CONSERVADOR fica sob o teto ------------------------------------


@pytest.mark.parametrize("seed", BASELINE_SEEDS)
def test_conservative_default_stays_under_the_60ppm_bound(seed: int) -> None:
    """De fábrica, a onivoria mantém a amplitude de CO₂ sob 60 ppm nas sementes da baseline.

    Este é o teste que o arquiteto pediu: o default (produtor 0,02) verificado
    contra o mesmo teto do M4, no regime de eras onde a onivoria é exercida,
    incluindo as sementes 5 e 99 nomeadas.
    """
    trail = _advancing_trail(DEFAULT, ticks=VALID_GAME_HORIZON, seed=seed)
    amplitude = _settled_co2_amplitude(trail)
    assert amplitude < CO2_AMPLITUDE_BOUND, (
        f"o default conservador ultrapassou o teto (semente {seed}): {amplitude:.1f} ppm"
    )
    assert trail[-1].biota.biomass > 0.0, "a biosfera colapsou no horizonte válido"


@pytest.mark.parametrize("seed", BASELINE_SEEDS)
def test_conservative_default_adds_no_new_carbon_amplification(seed: int) -> None:
    """A magnitude 0,02 é MEDIDA como não-amplificante: idêntica à cadeia estrita.

    Compara, semente a semente, contra o mesmo regime SEM onivoria: a amplitude do
    default não pode superar a estrita além de ruído — é o que "conservador"
    significa aqui, e o que garante margem para o ECO-002 somar sua parte depois.
    """
    default = _settled_co2_amplitude(_advancing_trail(DEFAULT, ticks=VALID_GAME_HORIZON, seed=seed))
    strict = _settled_co2_amplitude(_advancing_trail(STRICT, ticks=VALID_GAME_HORIZON, seed=seed))
    assert default <= strict + 1.0, (
        f"a onivoria de fábrica amplificou o carbono (semente {seed}): "
        f"estrito {strict:.1f} -> default {default:.1f} ppm"
    )


def test_the_default_pyramid_establishes_across_the_valid_horizon() -> None:
    """No jogo real, os três níveis se estabelecem sob a onivoria de fábrica.

    O predador é o nível menor e mais volátil: oscila perto de zero mesmo na
    cadeia estrita. Afirma-se o ESTABELECIMENTO — que em algum momento os três
    coexistem sem inverter a pirâmide —, não um valor num tick específico.
    """
    trail = _advancing_trail(DEFAULT, ticks=VALID_GAME_HORIZON, seed=2027)
    assert max(s.ecology.predator_biomass for s in trail) > 0.5, "o topo nunca se estabeleceu"
    established = [
        s.ecology
        for s in trail
        if s.ecology.producer_biomass > 0.0
        and s.ecology.herbivore_biomass > 0.0
        and s.ecology.predator_biomass > 0.0
    ]
    assert established, "os três níveis nunca coexistiram"
    for e in established:
        assert e.producer_biomass > e.predator_biomass, "pirâmide invertida sob onivoria"


# --- O achado da FORÇA PLENA, preservado e explicado (bloqueado pela Fase 3) --
#
# NÃO apagar: é a evidência de que a força plena está BLOQUEADA por uma
# dependência não resolvida (a correção de carbono da Fase 3), não de que está
# errada. Quando a Fase 3 pagar a dívida (ADR 0020), estes viram `xpass` e o
# relatório avisa sozinho que a força plena foi destravada — o mesmo mecanismo de
# `test_carbon_stable_long_horizon`.


@pytest.mark.xfail(
    reason=(
        "DÍVIDA CRUZADA (ADR 0030): a onivoria de FORÇA PLENA (produtor 0,30) "
        "amplifica a dívida de carbono de longo prazo do ADR 0020 e empurra a "
        "amplitude de CO₂ da semente 5 acima de 60 ppm. Correto na dinâmica, "
        "BLOQUEADO pela correção de carbono da Fase 3. Vira xpass quando ela landar."
    ),
    strict=False,
)
def test_full_strength_omnivory_stays_under_the_bound_pending_fase3() -> None:
    """Reproduz o achado da força plena: amplitude > 60 ppm na semente 5."""
    amplitude = _settled_co2_amplitude(
        _advancing_trail(FULL_STRENGTH, ticks=VALID_GAME_HORIZON, seed=5)
    )
    assert amplitude < CO2_AMPLITUDE_BOUND, (
        f"força plena amplificou o CO₂ da semente 5: {amplitude:.1f} ppm (esperado até a Fase 3)"
    )


@pytest.mark.xfail(
    reason=(
        "DÍVIDA CRUZADA (ADR 0030): no horizonte da dívida (3000 ticks), a "
        "onivoria de FORÇA PLENA RESHUFFLE o colapso caótico do ADR 0020 — em "
        "peso 0,30 a biomassa da semente 5 decai a ~3,6e-26 (extinta), onde a "
        "cadeia estrita a mantinha em ~28,8; em 0,15 a semente afetada era a 99. "
        "QUAL semente cai depende do peso, típico do regime caótico sem "
        "termostato de carbono. BLOQUEADO pela Fase 3. Vira xpass quando ela landar."
    ),
    strict=False,
)
def test_full_strength_biosphere_survives_the_debt_horizon_pending_fase3() -> None:
    """Reproduz o achado: a força plena colapsa uma biosfera que a estrita mantém.

    Em peso 0,30 a semente afetada é a 5 (estrita ~28,8 → plena ~3,6e-26, extinta
    na prática). Compara-se contra o PISO DE VIABILIDADE, não contra 0: o floor
    numérico deixa um resíduo tecnicamente positivo que não é uma biosfera viva.
    Não é agravamento sistemático e sim um RESHUFFLE do colapso caótico já
    conhecido do ADR 0020 — ver o `reason` e o ADR 0030 para o padrão por peso.
    """
    trail = _advancing_trail(FULL_STRENGTH, ticks=3000, seed=5)
    assert trail[-1].biota.biomass > VIABLE_BIOMASS, (
        "força plena colapsou a biosfera da semente 5 (esperado até a Fase 3)"
    )
