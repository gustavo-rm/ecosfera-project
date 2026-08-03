"""O Tutor DISTINGUE extinção catastrófica de ecológica (Q8, ADR 0019).

Este é o teste que fecha o laço do defeito corrigido em `22f8e10`. Lá, a cadeia
causal de uma extinção catastrófica apontava para o `TemperatureShift`; o
`cause_code` dizia "catástrofe" e a trilha dizia "não tolerou a temperatura".

Corrigir a cadeia no motor foi metade. A outra metade é aqui: **o consumidor tem
de narrar as duas de forma diferente**. Sem este teste, o motor poderia estar
certo e o aluno ainda ouviria "a espécie não se adaptou" depois de um meteoro —
porque a explicação é gerada por regras que casam por VARIÁVEL, e as duas
extinções produziam a mesma.

O Tutor não tem LLM: as frases saem do motor de regras determinístico. O Engine
emite `cause_code` NEUTRO; a prosa é do consumidor (ADR-ARCH-0002, Correção 1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.application.feedback.explain_from_events import load_translation
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.evolution.events import EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import (
    DomainEvent,
    Granularity,
    SimulationTime,
)

TRANSLATION = load_translation(Path("configs/event_observations.yaml"))
ENGINE = build_engine(Path("configs/causal_rules.yaml"))

# Regras que atribuem a perda a ADAPTAÇÃO/ambiente. Se alguma delas explicar a
# PRIMEIRA travessia de uma extinção catastrófica, o Tutor está culpando a
# espécie por uma morte que veio de fora.
#
# A verificação é por `rule_id`, e não por varredura de texto: a frase correta da
# catástrofe contém a palavra "adaptada" ("por mais bem adaptada que fosse"), que
# é justamente a lição — uma busca literal a acusaria. E os passos SEGUINTES da
# cadeia narram consequências físicas legítimas (CO₂ → temperatura), que não são
# atribuição de causa da extinção.
ECOLOGICAL_RULES = {"R-TEMP-EXTINCTION", "R-EXTINCTION-BIODIVERSITY", "R-WATER-BIODIVERSITY"}
CATASTROPHE_RULES = {"R-CATASTROPHE-EXTINCTION", "R-CATASTROPHE-BIOMASS"}


def _extinction(cause: EvolutionCauseCode, *, before: float = 40.0) -> DomainEvent:
    return DomainEvent(
        event_id="evt-extinction",
        event_type="SpeciesExtinct",
        engine_id="evolution",
        occurred_at=SimulationTime(tick=120, era=3),
        seed=2027,
        cause_code=cause,
        correlation_id="corr-1",
        causation_id="evt-meteor",
        cause_detail={"biomass": 0.0, "biomass_before": before},
        granularity=Granularity.AGGREGATE,
    )


def _explain(event: DomainEvent) -> str:
    """Texto COMPLETO da cadeia — inclusive as consequências encadeadas."""
    return " ".join(step.explanation for step in _chain(event)).lower()


def _chain(event: DomainEvent) -> list[object]:
    observations = TRANSLATION.observations([event])
    assert observations, f"{event.cause_code} não produziu observação alguma"
    return list(ENGINE.explain("planet-test", observations).chain)


def _attributing_rules(event: DomainEvent) -> set[str]:
    """Regras que explicam a PERDA em si — o primeiro elo, não as consequências."""
    variable = TRANSLATION.observations([event])[0].variable
    return {step.rule_id for step in _chain(event) if step.cause == variable}


# --- A tradução distingue as duas famílias ------------------------------------


def test_the_two_families_produce_different_observations() -> None:
    """A distinção começa na tradução: variáveis diferentes, regras diferentes."""
    catastrophic = TRANSLATION.observations([_extinction(EvolutionCauseCode.CATASTROPHIC_EVENT)])
    ecological = TRANSLATION.observations([_extinction(EvolutionCauseCode.THERMAL_INTOLERANCE)])

    assert catastrophic[0].variable != ecological[0].variable, (
        "as duas extinções viram a MESMA observação: o Tutor não tem como "
        "distingui-las e narrará as duas como falha de adaptação"
    )
    assert catastrophic[0].variable == "catastrophic_loss"


# --- O que o aluno ouve -------------------------------------------------------


def test_a_catastrophic_extinction_is_not_explained_as_a_failure_to_adapt() -> None:
    """O coração pedagógico: nenhuma regra de adaptação explica a catástrofe."""
    fired = _attributing_rules(_extinction(EvolutionCauseCode.CATASTROPHIC_EVENT))
    assert fired, "a extinção catastrófica não gerou explicação alguma"

    blaming = fired & ECOLOGICAL_RULES
    assert not blaming, (
        f"a extinção CATASTRÓFICA foi explicada por {blaming} — o Tutor está "
        "culpando a espécie por uma morte que veio de fora"
    )
    assert fired & CATASTROPHE_RULES, f"nenhuma regra de catástrofe disparou: {fired}"


def test_a_catastrophic_extinction_names_the_extreme_event() -> None:
    """E diz o que de fato aconteceu, em vez de só omitir a adaptação."""
    text = _explain(_extinction(EvolutionCauseCode.CATASTROPHIC_EVENT))
    assert "evento extremo" in text, f"a explicação não nomeia o evento: {text!r}"


def test_a_catastrophic_extinction_says_adaptation_would_not_have_saved_it() -> None:
    """A frase carrega a lição inteira: "por mais bem adaptada que fosse"."""
    text = _explain(_extinction(EvolutionCauseCode.CATASTROPHIC_EVENT))
    assert "por mais bem adaptada" in text, (
        f"a explicação omite que a adaptação não teria salvado a espécie: {text!r}"
    )


@pytest.mark.parametrize(
    "cause",
    [
        EvolutionCauseCode.THERMAL_INTOLERANCE,
        EvolutionCauseCode.RESOURCE_SCARCITY,
        EvolutionCauseCode.PREDATION_PRESSURE,
    ],
)
def test_an_ecological_extinction_is_still_explained_ecologically(
    cause: EvolutionCauseCode,
) -> None:
    """A contraprova. Sem ela, o teste acima passaria com o Tutor mudo.

    A extinção ecológica DEVE falar de ambiente e adaptação — é o que ela é. O
    defeito seria uniformizar as duas em qualquer direção.
    """
    fired = _attributing_rules(_extinction(cause))
    assert fired, f"{cause} não gerou explicação"
    assert not (fired & CATASTROPHE_RULES), (
        f"uma extinção ECOLÓGICA foi narrada como catástrofe: {fired}"
    )
    assert "evento extremo" not in _explain(_extinction(cause))


def test_the_engine_emits_a_neutral_cause_code_and_the_prose_is_the_consumers() -> None:
    """A fronteira do ADR-ARCH-0002: o evento traz código, não frase.

    Se o Engine escrevesse a prosa, mudar a linguagem para outra faixa etária
    exigiria tocar na simulação.
    """
    event = _extinction(EvolutionCauseCode.CATASTROPHIC_EVENT)
    assert isinstance(event.cause_code, EvolutionCauseCode)
    for value in event.cause_detail.values():
        assert not isinstance(value, str) or " " not in str(value), (
            "o cause_detail carrega prosa; a explicação é do consumidor"
        )
