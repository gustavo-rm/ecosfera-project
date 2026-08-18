"""Nenhum poço de presa perde mais do que tem — nem sob pressão combinada.

O teto global do M3 vira racionamento POR POÇO quando um generalista come do
mesmo estoque que outro consumidor. No modelo agregado, o poço do produtor sofre
duas pressões no mesmo tick: a pastagem do herbívoro e a onivoria do predador. A
soma das capturas não pode exceder o estoque, senão a diferença vira biomassa do
nada — exatamente o vazamento de 7,76% que o M3 fechou, agora sob mais de uma
fonte de demanda.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import _ration_pool, _trophic_step, predator_diet
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

ECOLOGY = ecology_params()
GENERALIST = replace(
    ECOLOGY,
    generalist_unlock_era=0,
    generalist_full_era=0,
    predator_diet_herbivore=0.70,
    predator_diet_producer=0.30,
)
PARAMS = load_params(Path("configs/simulation_params.yaml"))
TOLERANCE = 1e-9


def _ctx(era: int, *, tick: int = 5, seed: int = 2027) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("pool", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


# --- O racionador, isolado ----------------------------------------------------


def test_ration_pool_passes_through_when_demand_fits() -> None:
    assert _ration_pool(100.0, (30.0, 20.0)) == (30.0, 20.0)


def test_ration_pool_never_exceeds_the_stock() -> None:
    """Duas demandas famintas sobre um poço escasso: a soma iguala o estoque."""
    grazed, omnivored = _ration_pool(10.0, (60.0, 40.0))
    assert grazed + omnivored == pytest.approx(10.0, abs=TOLERANCE)
    assert grazed >= 0.0 and omnivored >= 0.0
    # Proporcional à demanda: 60:40 => 6:4.
    assert grazed == pytest.approx(6.0, abs=TOLERANCE)
    assert omnivored == pytest.approx(4.0, abs=TOLERANCE)


def test_ration_pool_reduces_to_min_for_a_single_consumer() -> None:
    """Um consumidor só: o teto exato do M3, sem erro de arredondamento."""
    assert _ration_pool(10.0, (60.0,)) == (10.0,)
    assert _ration_pool(10.0, (7.0,)) == (7.0,)


def test_ration_pool_handles_an_empty_stock() -> None:
    assert _ration_pool(0.0, (5.0, 3.0)) == (0.0, 0.0)


# --- O poço do produtor sob pressão combinada ---------------------------------


def test_the_producer_pool_survives_grazing_plus_omnivory() -> None:
    """Herbívoro faminto E predador onívoro sobre um produtor escasso.

    Recria a demanda dos DOIS consumidores como o passo trófico a compõe e
    confere que a captura somada não excede o produtor disponível.
    """
    hungry = replace(GENERALIST, predation_rate=0.05)
    producer, herbivore, predator = 2.0, 40.0, 30.0
    _, diet_producer = predator_diet(0, hungry)
    graze_demand = hungry.predation_rate * herbivore * producer
    omni_demand = hungry.predation_rate * predator * producer * diet_producer
    assert graze_demand + omni_demand > producer, "cenário fraco: a demanda nem excede o estoque"

    grazed, omnivored = _ration_pool(producer, (graze_demand, omni_demand))
    assert grazed + omnivored <= producer + TOLERANCE, "o poço do produtor foi sobre-predado"


def test_the_trophic_step_never_drives_the_producer_negative() -> None:
    """Predação absurda, produtor escasso: o produtor não fica negativo no passo."""
    params = replace(GENERALIST, predation_rate=5.0, growth_rate=0.0, demographic_noise=0.0)
    out = _trophic_step((1.0, 50.0, 40.0), 1000.0, params, _ctx(era=0))
    assert all(v >= 0.0 for v in out), f"algum nível ficou negativo: {out}"


def test_no_pool_is_over_predated_across_a_long_generalist_run() -> None:
    """Ao longo de muitos passos, nenhum nível cruza o zero por sobre-predação."""
    params = replace(GENERALIST, predation_rate=0.05)
    levels = (140.0, 60.0, 20.0)
    ctx = _ctx(era=0)
    for _ in range(60):
        levels = _trophic_step(levels, 300.0, params, ctx)
        assert all(v >= 0.0 for v in levels), f"nível negativo: {levels}"
