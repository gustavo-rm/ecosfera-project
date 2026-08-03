"""O TESTE PEDAGÓGICO CENTRAL DO M4 (Q8, ADR 0019).

A concepção equivocada que a plataforma existe para desfazer: *"quem se extingue
era inferior"*. Se toda extinção do simulador tiver causa ecológica — não tolerou
o calor, não achou recurso, foi predado —, o simulador ENSINA essa concepção,
por mais correta que seja cada peça isolada.

A correção é a extinção CATASTRÓFICA: um meteoro mata quem estava embaixo. Uma
comunidade no próprio ótimo térmico, com recurso de sobra e sem predador, pode
ser eliminada — e o `cause_code` tem de dizer isso.

Este arquivo exige que a mortalidade seja REALMENTE independente de aptidão. Não
basta existir um código de causa novo: se a catástrofe poupasse os bem adaptados,
ela seria seleção com outro nome, e a lição continuaria errada.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from tests.support import test_params as _production_params

from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.domain import LocalConditions, local_suitability
from ecosfera_ai.engines.evolution.events import EvolutionCauseCode
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    BiotaSlice,
    ClimateSlice,
    EventSlice,
    ResourceSlice,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.biology.genome import Genome

EVOLUTION = evolution_params()
PARAMS = _production_params()

# Uma comunidade EXEMPLARMENTE adaptada: no próprio ótimo térmico, tolerância
# larga, metabolismo e porte baratos. Se a catástrofe fosse seletiva, esta seria
# a última a morrer — e é exatamente por isso que ela é a cobaia certa.
WELL_ADAPTED = Genome(
    temp_optimum=20.0,
    temp_tolerance=20.0,
    water_need=0.1,
    size=0.5,
    metabolism=0.4,
    trophic_level=1.0,
).clamped()

POORLY_ADAPTED = Genome(
    temp_optimum=-30.0,  # num planeta a 20 C, muito longe do próprio ótimo
    temp_tolerance=3.0,  # especialista extremo
    water_need=0.9,
    size=2.5,
    metabolism=2.5,
    trophic_level=1.0,
).clamped()


def _snapshot(genome: Genome, *, biomass: float, catastrophe: float) -> WorldStateSnapshot:
    """Mundo generoso: 20 °C, água e energia de sobra, nenhum predador."""
    biota = BiotaSlice(
        biomass=biomass,
        species_richness=1.0,
        **{
            f"mean_{n}": float(getattr(genome, n))
            for n in (
                "temp_optimum",
                "temp_tolerance",
                "water_need",
                "size",
                "metabolism",
                "trophic_level",
            )
        },
    )
    return WorldStateSnapshot(
        planet_id="catastrophe",
        seed=2027,
        tick=10,
        era=0,
        climate=ClimateSlice(temperature=20.0),
        resource=ResourceSlice(
            water_available=0.9,
            nutrients_available=1.0,
            energy_available=0.2,
            carrying_capacity=500.0,
        ),
        biota=biota,
        event=EventSlice(catastrophic_mortality=catastrophe),
    )


def _tick(snapshot: WorldStateSnapshot) -> tuple[float, tuple[object, ...]]:
    engine = EvolutionEngine()
    ctx = TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, engine.engine_id, snapshot.tick),
        tick=snapshot.tick,
        era=0,
        budget=PARAMS.engine_budget,
    )
    result = engine.tick(ctx)
    return snapshot.biota.biomass + result.delta.values.get("biomass", 0.0), result.events


# --- A comunidade sob teste é, de fato, bem adaptada --------------------------


def test_the_control_group_really_is_well_adapted() -> None:
    """Sem isto, o teste principal seria vacuamente verdadeiro.

    Se a comunidade "bem adaptada" não fosse mesmo bem adaptada, matá-la não
    provaria nada sobre independência de aptidão.
    """
    conditions = LocalConditions(
        temperature=20.0,
        water_available=0.9,
        energy_available=0.2,
        carrying_capacity=500.0,
        occupied=50.0,
        predation_pressure=0.0,
    )
    good = local_suitability(WELL_ADAPTED, conditions, EVOLUTION)
    bad = local_suitability(POORLY_ADAPTED, conditions, EVOLUTION)

    assert good > 0.7, f"a coorte de controle não é bem adaptada (adequação {good:.2f})"
    assert good > bad * 3.0, "as duas coortes não são distinguíveis em adequação"


def test_the_well_adapted_community_thrives_without_a_catastrophe() -> None:
    """Contraprova: sem catástrofe, ela CRESCE. O que a mata é o evento."""
    after, events = _tick(_snapshot(WELL_ADAPTED, biomass=50.0, catastrophe=0.0))
    assert after > 50.0, "a coorte de controle deveria prosperar num mundo generoso"
    assert not [e for e in events if e.event_type == "SpeciesExtinct"]


# --- O coração: a catástrofe não olha para o genoma ---------------------------


def test_a_well_adapted_community_can_be_wiped_out_by_a_catastrophe() -> None:
    """Uma espécie ÓTIMA morre. É a correção da concepção equivocada."""
    after, events = _tick(_snapshot(WELL_ADAPTED, biomass=50.0, catastrophe=1.0))

    assert after == pytest.approx(0.0, abs=1e-9), (
        "a catástrofe poupou a comunidade bem adaptada — ela está sendo filtrada "
        "por aptidão, o que a torna seleção com outro nome"
    )
    extinct = [e for e in events if e.event_type == "SpeciesExtinct"]
    assert extinct, "a comunidade foi a zero mas nenhuma extinção foi registrada"
    assert extinct[0].cause_code is EvolutionCauseCode.CATASTROPHIC_EVENT, (
        f"extinção catastrófica reportada como {extinct[0].cause_code} — o Tutor "
        "explicaria como falha de adaptação"
    )


def test_the_catastrophe_removes_the_same_fraction_regardless_of_adaptation() -> None:
    """A prova QUANTITATIVA da independência: a fração removida é a MESMA.

    Se a mortalidade fosse mesmo levemente seletiva, a coorte bem adaptada
    perderia uma fração menor que a mal adaptada. Comparar as duas frações no
    mesmo mundo é o que detecta isso — e é mais forte do que só verificar que
    ambas morrem.
    """
    fractions = {}
    for name, genome in (("bem", WELL_ADAPTED), ("mal", POORLY_ADAPTED)):
        without, _ = _tick(_snapshot(genome, biomass=100.0, catastrophe=0.0))
        with_it, _ = _tick(_snapshot(genome, biomass=100.0, catastrophe=0.5))
        fractions[name] = 1.0 - (with_it / without)

    assert fractions["bem"] == pytest.approx(fractions["mal"], abs=1e-9), (
        f"a catástrofe removeu {fractions['bem']:.4f} da coorte bem adaptada e "
        f"{fractions['mal']:.4f} da mal adaptada: ela está olhando para o genoma"
    )
    assert fractions["bem"] == pytest.approx(0.5, abs=1e-9), (
        "a fração removida não corresponde à severidade declarada"
    )


@pytest.mark.parametrize(
    "trait,value",
    [
        ("temp_optimum", -35.0),
        ("temp_tolerance", 2.0),
        ("water_need", 0.95),
        ("size", 2.8),
        ("metabolism", 2.8),
    ],
)
def test_no_single_trait_buys_protection_from_a_catastrophe(trait: str, value: float) -> None:
    """Nenhum traço, isolado, muda o que a catástrofe leva.

    Varre o genoma traço a traço. Se QUALQUER um deles alterasse a fração
    removida, a catástrofe seria seletiva naquele eixo — e a lição vazaria por
    ali.
    """
    variant = replace(WELL_ADAPTED, **{trait: value}).clamped()

    base_without, _ = _tick(_snapshot(WELL_ADAPTED, biomass=100.0, catastrophe=0.0))
    base_with, _ = _tick(_snapshot(WELL_ADAPTED, biomass=100.0, catastrophe=0.4))
    var_without, _ = _tick(_snapshot(variant, biomass=100.0, catastrophe=0.0))
    var_with, _ = _tick(_snapshot(variant, biomass=100.0, catastrophe=0.4))

    assert (1.0 - base_with / base_without) == pytest.approx(
        1.0 - var_with / var_without, abs=1e-9
    ), f"variar `{trait}` mudou a mortalidade catastrófica"


def test_the_catastrophe_is_not_an_ecological_pressure_in_disguise() -> None:
    """A catástrofe NÃO entra na adequação local — ela não é um fator ambiental.

    Se `catastrophe` alterasse `local_suitability`, a comunidade "sentiria" o
    meteoro como sente o calor, e a morte voltaria a ser mediada por adaptação.
    """
    conditions = LocalConditions(
        temperature=20.0,
        water_available=0.9,
        energy_available=0.2,
        carrying_capacity=500.0,
        occupied=50.0,
        predation_pressure=0.0,
    )
    calm = local_suitability(WELL_ADAPTED, conditions, EVOLUTION)
    struck = local_suitability(WELL_ADAPTED, replace(conditions, catastrophe=1.0), EVOLUTION)
    assert calm == pytest.approx(struck), (
        "a catástrofe mudou a adequação local: virou pressão ecológica"
    )
