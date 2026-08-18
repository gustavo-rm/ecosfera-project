"""Um predador de nível único se comporta EXATAMENTE como antes desta fase.

A generalização tem de ser estrita: com a dieta `(herbívoro=1, produtor=0)` — o
que vale em toda era anterior a `unlock_era`, e portanto na era 0 de toda a linha
de base — o passo trófico precisa reproduzir bit a bit o do M4. O oráculo abaixo
é a fórmula do M4 transcrita; o teste exige igualdade EXATA (`==`), não
aproximada, sobre uma grade que inclui os casos em que o teto de captura morde.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import EcologyEngineParams
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import _room, _trophic_step, predator_diet
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

ECOLOGY = ecology_params()
PARAMS = load_params(Path("configs/simulation_params.yaml"))
_EPS = 1e-9


def _ctx(era: int, *, tick: int, seed: int) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("compat", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


def _legacy_step(
    levels: tuple[float, float, float],
    capacity: float,
    params: EcologyEngineParams,
    ctx: TickContext,
) -> tuple[float, float, float]:
    """A fórmula do M4, ANTES de ECO-001: cadeia estrita, teto por `min`."""
    producer, herbivore, predator = levels
    grazed = min(producer, params.predation_rate * herbivore * producer)
    hunted = min(herbivore, params.predation_rate * predator * herbivore)
    if capacity > _EPS:
        growth = params.growth_rate * producer * (1.0 - producer / capacity)
    else:
        growth = -params.mortality_rate * producer
    noise = float(ctx.rng.normal(0.0, params.demographic_noise))
    new_producer = producer + growth - grazed + noise * producer
    ceiling = capacity * params.consumer_capacity_share
    new_herbivore = herbivore + params.conversion_efficiency * grazed * _room(herbivore, ceiling)
    new_herbivore -= params.mortality_rate * herbivore + hunted
    new_predator = predator + params.conversion_efficiency * hunted * _room(predator, ceiling)
    new_predator -= params.mortality_rate * predator
    return tuple(  # type: ignore[return-value]
        0.0 if v < params.min_viable_population else v
        for v in (max(0.0, new_producer), max(0.0, new_herbivore), max(0.0, new_predator))
    )


# Grade que inclui casos de teto: herbívoro/predador grandes fazem a demanda de
# captura exceder o estoque, exercitando o ramo de racionamento do `_ration_pool`
# — onde um erro de 1 ULP contra o antigo `min` apareceria.
_LEVELS = [
    (100.0, 30.0, 10.0),
    (10.0, 90.0, 5.0),  # herbívoro faminto: pastagem excede o produtor
    (200.0, 5.0, 90.0),  # predador faminto: caça excede o herbívoro
    (0.5, 80.0, 80.0),  # ambos os tetos mordem
    (60.0, 0.0, 8.0),  # sem herbívoro
    (0.0, 0.0, 0.0),  # mundo vazio
]
_CAPS = [0.0, 50.0, 300.0]


@pytest.mark.parametrize("levels", _LEVELS)
@pytest.mark.parametrize("capacity", _CAPS)
@pytest.mark.parametrize("seed", [1, 2027, 99])
def test_strict_diet_matches_the_pre_eco001_formula_bit_for_bit(
    levels: tuple[float, float, float], capacity: float, seed: int
) -> None:
    """Na era 0 (dieta estrita), o passo novo é IDÊNTICO ao do M4.

    Cada lado recebe um RNG semeado do mesmo jeito, então o único ruído sorteado
    é o mesmo dos dois; a igualdade exige que TODA a aritmética restante case.
    """
    tick = 5
    got = _trophic_step(levels, capacity, ECOLOGY, _ctx(era=0, tick=tick, seed=seed))
    want = _legacy_step(levels, capacity, ECOLOGY, _ctx(era=0, tick=tick, seed=seed))
    assert got == want, f"divergiu do M4 em levels={levels} cap={capacity} seed={seed}"


def test_the_default_diet_is_strict_below_the_unlock_era() -> None:
    """Antes de `unlock_era`, e portanto na era 0, a dieta é (1, 0)."""
    for era in range(0, ECOLOGY.generalist_unlock_era + 1):
        assert predator_diet(era, ECOLOGY) == (1.0, 0.0), f"era {era} não é cadeia estrita"


def test_a_strict_diet_config_stays_strict_at_every_era() -> None:
    """Config de nível único (produtor=0) ignora a era — sempre cadeia estrita.

    É a compatibilidade com um params v1 (sem bloco `generalist`): o carregador
    assume `producer=0`, e nenhuma era jamais destrava onivoria.
    """
    strict = replace(ECOLOGY, predator_diet_producer=0.0, predator_diet_herbivore=1.0)
    for era in (0, 5, 12, 40):
        assert predator_diet(era, strict) == (1.0, 0.0)
