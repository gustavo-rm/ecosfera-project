"""A dieta generalista só aparece por PROGRESSÃO DE ERA.

PED-001 e o compromisso da Tássia (Div. 3): cadeias nas eras iniciais, poucos
onívoros no meio, teias nas avançadas. A onivoria não é um modelo global fixo —
é um parâmetro contínuo (`generalist_strength`) que a era desloca, de 0 (cadeia)
a 1 (dieta plena). Estes testes fixam a rampa, sua ancoragem em DADO versionado
(não um número no código), e que o portão de fato muda o comportamento.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import (
    _trophic_step,
    generalist_strength,
    predator_diet,
)
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

ECOLOGY = ecology_params()  # unlock_era=6, full_era=12, produtor=0.02 (conservador)
PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _ctx(era: int, *, tick: int = 5, seed: int = 2027) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("era", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


def test_strength_is_zero_before_unlock_and_full_after() -> None:
    for era in range(0, ECOLOGY.generalist_unlock_era + 1):
        assert generalist_strength(era, ECOLOGY) == 0.0, f"era {era} destravou cedo"
    assert generalist_strength(ECOLOGY.generalist_full_era, ECOLOGY) == 1.0
    assert generalist_strength(ECOLOGY.generalist_full_era + 20, ECOLOGY) == 1.0


def test_strength_ramps_monotonically_between_unlock_and_full() -> None:
    strengths = [generalist_strength(era, ECOLOGY) for era in range(0, 20)]
    assert strengths == sorted(strengths), "a força da onivoria não é monótona na era"
    mid = (
        ECOLOGY.generalist_unlock_era
        + (ECOLOGY.generalist_full_era - ECOLOGY.generalist_unlock_era) // 2
    )
    assert 0.0 < generalist_strength(mid, ECOLOGY) < 1.0, (
        "sem estágio intermediário (poucos onívoros)"
    )


def test_the_diet_opens_the_off_chain_source_gradually() -> None:
    """O peso do produtor na dieta cresce de 0 (cadeia) ao valor pleno (teia)."""
    assert predator_diet(0, ECOLOGY) == (1.0, 0.0)
    early = predator_diet(ECOLOGY.generalist_unlock_era + 1, ECOLOGY)
    full = predator_diet(ECOLOGY.generalist_full_era, ECOLOGY)
    assert 0.0 < early[1] < full[1], "a onivoria não abre gradualmente"
    assert full[1] == pytest.approx(ECOLOGY.predator_diet_producer)
    assert full[0] + full[1] == pytest.approx(1.0), "os pesos deixaram de somar 1"


def test_the_gate_is_versioned_data_not_a_hardcoded_constant() -> None:
    """Mudar o parâmetro muda quando a onivoria liga — não há era colada no código."""
    early_unlock = replace(ECOLOGY, generalist_unlock_era=0, generalist_full_era=0)
    assert generalist_strength(0, early_unlock) == 1.0, "o unlock não é governado pelo parâmetro"

    later_unlock = replace(ECOLOGY, generalist_unlock_era=30, generalist_full_era=40)
    assert generalist_strength(20, later_unlock) == 0.0, "o unlock não respondeu ao parâmetro"


def test_the_era_gate_actually_changes_trophic_behaviour() -> None:
    """Portão comportamental: o mesmo mundo evolui diferente na era estrita e na plena.

    Sem isto, a progressão seria só um número num relatório. Aqui o produtor e o
    predador terminam o passo em valores distintos porque a onivoria entrou.
    """
    # Peso forte para tornar o efeito do portão inequívoco — a MAGNITUDE de
    # fábrica é conservadora (0,02) de propósito; o que se testa aqui é que a era
    # ALTERA o comportamento, não a calibração default.
    params = replace(
        ECOLOGY, demographic_noise=0.0, predator_diet_herbivore=0.70, predator_diet_producer=0.30
    )
    levels = (150.0, 40.0, 15.0)
    strict = _trophic_step(levels, 300.0, params, _ctx(era=0))
    web = _trophic_step(levels, 300.0, params, _ctx(era=params.generalist_full_era))

    assert web != strict, "a era não alterou a dinâmica trófica"
    assert web[0] < strict[0], "na teia, o produtor deveria perder mais (onivoria)"
    assert web[2] > strict[2], "na teia, o predador deveria ganhar da segunda fonte"
