"""A predação generalista REDISTRIBUI biomassa; nunca a cria.

Estende a garantia do M3 (`test_ecology_conserves_biomass`) ao caminho de
múltiplos poços: agora o predador drena produtor E herbívoro no mesmo passo, e a
soma das capturas continua sem poder exceder o que existe. Duas propriedades:

1. **No fecho do tick** a soma dos três níveis é EXATAMENTE a biomassa que a
   Evolution publicou (ADR 0016) — a Ecology reparte a forma, não escreve total.
2. **No passo trófico**, sem produção primária, o total só pode cair: a conversão
   dissipa (`conversão < 1`) e a mortalidade remove. Vale mesmo no pior caso —
   conversão 1, mortalidade 0 — em que a predação apenas MOVE biomassa.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import EcologyEngine, _trophic_step
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot
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
    snapshot = snapshot_of(initial_state(PlanetSeed("cons", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


def _snapshot_with(biomass: float, split: tuple[float, float, float]) -> WorldStateSnapshot:
    """Um mundo com biomassa e repartição trófica escolhidas, na era plena."""
    base = snapshot_of(initial_state(PlanetSeed("cons", 2027), PARAMS))
    return replace(
        base,
        era=0,  # com unlock=full=0 a onivoria já é plena na era 0
        biota=replace(base.biota, biomass=biomass),
        ecology=replace(
            base.ecology,
            producer_biomass=split[0],
            herbivore_biomass=split[1],
            predator_biomass=split[2],
        ),
    )


@pytest.mark.parametrize(
    ("biomass", "split"),
    [
        (168.0, (120.0, 40.0, 8.0)),
        (90.0, (60.0, 22.0, 8.0)),
        (240.0, (150.0, 70.0, 20.0)),
        (40.0, (30.0, 8.0, 2.0)),
    ],
)
def test_the_tick_pins_the_total_to_the_evolution_biomass(
    biomass: float, split: tuple[float, float, float]
) -> None:
    """Com onivoria plena, a soma dos níveis ainda é a biomassa da Evolution.

    Roda o Engine inteiro (com renormalização) e confere a identidade contábil do
    ADR 0016 — a Ecology decide a FORMA, o tamanho é da Evolution.
    """
    engine = EcologyEngine(params=GENERALIST)
    snapshot = _snapshot_with(biomass, split)
    ctx = TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=PARAMS.engine_budget,
    )
    values = engine.tick(ctx).delta.values
    new_levels = (
        snapshot.ecology.producer_biomass + values["producer_biomass"],
        snapshot.ecology.herbivore_biomass + values["herbivore_biomass"],
        snapshot.ecology.predator_biomass + values["predator_biomass"],
    )
    assert sum(new_levels) == pytest.approx(biomass, abs=1e-9), (
        f"a soma dos níveis descolou da biomassa: {sum(new_levels)} vs {biomass}"
    )


def test_a_generalist_step_without_production_never_creates_biomass() -> None:
    """Sem produção primária, o passo generalista (dois poços) só perde total."""
    params = replace(GENERALIST, growth_rate=0.0, demographic_noise=0.0, min_viable_population=0.0)
    levels = (100.0, 30.0, 12.0)
    out = _trophic_step(levels, 1000.0, params, _ctx(era=0))
    assert sum(out) <= sum(levels) + TOLERANCE, (
        f"a predação generalista criou biomassa: {sum(levels)} -> {sum(out)}"
    )


def test_worst_case_generalist_predation_only_moves_biomass() -> None:
    """Conversão 1, mortalidade 0: a predação de dois poços MOVE, não cria.

    É o pior caso do vazamento — nada se dissipa na conversão, então a única
    barreira contra criar biomassa é o teto de captura por poço. Ele segura.
    """
    params = replace(
        GENERALIST,
        growth_rate=0.0,
        demographic_noise=0.0,
        mortality_rate=0.0,
        conversion_efficiency=1.0,
        predation_rate=3.0,  # fome absurda: a demanda excede os estoques com folga
        min_viable_population=0.0,
    )
    levels = (50.0, 40.0, 20.0)
    out = _trophic_step(levels, 1000.0, params, _ctx(era=0))
    assert all(v >= -TOLERANCE for v in out), "algum nível ficou negativo"
    assert sum(out) <= sum(levels) + TOLERANCE, (
        f"a soma das capturas excedeu os estoques e virou biomassa: {sum(levels)} -> {sum(out)}"
    )
