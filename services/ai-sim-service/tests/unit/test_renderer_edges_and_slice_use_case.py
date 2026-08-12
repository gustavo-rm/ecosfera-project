"""As bordas do renderizador: o que ele recusa, o que ele pula, e o caminho inteiro.

Três comportamentos que decidem o que acontece quando algo NÃO está previsto, e
em cada um a escolha entre falhar e degradar foi feita de propósito:

* **Template ausente → FALHA ALTO.** Pular o fato deixaria o Tutor mudo sobre um
  acontecimento do planeta, e ausência não se denuncia sozinha.
* **Slot ausente → FALHA ALTO.** Renderizar com o slot vazio, ou com um valor
  plausível qualquer, produziria uma frase bem formada afirmando algo que o
  Event Store não contém. É a alucinação por descuido.
* **Vocabulário ausente → PULA EM SILÊNCIO.** Um tipo de evento que o consumidor
  ainda não sabe nomear não pode quebrar a narração inteira: o Event Store cresce
  com Engines novos. O que ele não pode é ganhar um nome inventado.

A assimetria é deliberada. Nos dois primeiros o consumidor SABE que devia falar e
não consegue; no terceiro ele nem sabe do que se trata — e o teste de cobertura
de `cause_code` (`test_consumer_vocabulary_matches_engines`) é quem garante que o
silêncio seja exceção declarada, e não regra.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade, life_emerged
from tests.support_explanation import context_of, explain, renderer, templates

from ecosfera_ai.application.consumers.render_explanation import ExplainSliceUseCase
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice
from ecosfera_ai.domain.consumers.templates import (
    MissingSlotError,
    MissingTemplateError,
)
from ecosfera_ai.engines.ecology.events import TROPHIC_COLLAPSE, EcologyCauseCode
from ecosfera_ai.engines.evolution.events import MASS_MORTALITY, EvolutionCauseCode
from ecosfera_ai.shared_kernel.events import CoreCauseCode, EventEmitter

CASCADE = branching_cascade()
METEOR = CASCADE[0]


# --- Falhar alto onde o silêncio seria pior ----------------------------------


def test_an_unknown_template_id_fails_loudly() -> None:
    with pytest.raises(MissingTemplateError, match="sem narração"):
        templates().get("T-QUE-NAO-EXISTE", Register.STANDARD)


def test_a_template_rendered_without_its_slots_fails_loudly() -> None:
    """A frase com buraco nunca chega ao aluno — nem com o buraco preenchido."""
    template = templates().get("T-EXTINCTION-ECOLOGICAL", Register.STANDARD)
    with pytest.raises(MissingSlotError, match="mechanism"):
        template.render({"tick": "10"})


# --- Pular em silêncio o que não se sabe nomear ------------------------------


def test_an_event_type_without_a_noun_is_skipped_not_invented() -> None:
    """Um Engine futuro não quebra o Tutor, e também não ganha nome inventado."""
    unknown = EventEmitter(engine_id="futuro", seed=1, tick=5, era=1).emit(
        "AlgoQueAindaNaoExiste", CoreCauseCode.ENGINE_HEARTBEAT
    )
    explanation = explain([unknown, *CASCADE])

    narrated = {fact.grounding.event_id for fact in explanation.facts}
    assert unknown.event_id not in narrated
    assert "AlgoQueAindaNaoExiste" not in explanation.summary
    assert narrated, "pular o desconhecido não pode calar o resto da fatia"


def test_a_cause_code_without_a_mechanism_is_skipped_not_invented() -> None:
    """Mesma regra pela outra ponta: sem oração causal, não se narra o porquê."""
    orphan = EventEmitter(engine_id="evolution", seed=1, tick=6, era=1).emit(
        MASS_MORTALITY, CoreCauseCode.ENGINE_HEARTBEAT, cause_detail={"lost_fraction": 0.2}
    )
    explanation = explain([orphan])
    assert all(fact.grounding.event_id != orphan.event_id for fact in explanation.facts)


# --- As famílias que faltavam exercitar --------------------------------------


def test_a_trophic_collapse_is_narrated_as_a_broken_link() -> None:
    collapse = EventEmitter(engine_id="ecology", seed=1, tick=50, era=1).emit(
        TROPHIC_COLLAPSE, EcologyCauseCode.PREY_COLLAPSE, participants=["species:community"]
    )
    fact = explain([collapse]).facts[0]

    assert fact.template_id == "T-TROPHIC-COLLAPSE"
    assert "cadeia alimentar" in fact.text.lower()


def test_repeated_trophic_collapses_are_counted_not_repeated() -> None:
    collapses = [
        EventEmitter(engine_id="ecology", seed=1, tick=tick, era=1).emit(
            TROPHIC_COLLAPSE, EcologyCauseCode.PREY_COLLAPSE
        )
        for tick in (50, 51, 52)
    ]
    facts = explain(collapses).facts

    assert len(facts) == 1
    assert facts[0].template_id == "T-TROPHIC-COLLAPSE-REPEATED"
    assert facts[0].slots["occurrences"] == "3"


def test_a_catastrophic_mass_mortality_names_the_trigger() -> None:
    """Perda PARCIAL por catástrofe: a comunidade não desapareceu, e a frase diz."""
    mortality = EventEmitter(engine_id="evolution", seed=2027, tick=102, era=1).emit(
        MASS_MORTALITY,
        EvolutionCauseCode.CATASTROPHIC_EVENT,
        cause_detail={"lost_fraction": 0.6},
        causation_id=METEOR.event_id,
    )
    fact = explain([METEOR, mortality]).facts[-1]

    assert fact.template_id == "T-MASS-MORTALITY-CATASTROPHIC"
    assert "meteoro" in fact.text.lower()
    assert "não desapareceu" in fact.text.lower()


def test_repeated_mass_mortality_is_counted_not_repeated() -> None:
    """O defeito que a fumaça encontrou: 257 ocorrências viravam 257 parágrafos."""
    losses = [
        EventEmitter(engine_id="evolution", seed=1, tick=tick, era=1).emit(
            MASS_MORTALITY,
            EvolutionCauseCode.RESOURCE_SCARCITY,
            cause_detail={"lost_fraction": 0.2},
        )
        for tick in range(200, 260)
    ]
    facts = explain(losses).facts

    assert len(facts) == 1
    assert facts[0].template_id == "T-MASS-MORTALITY-REPEATED"
    assert facts[0].slots["occurrences"] == "60"


def test_a_repeated_catastrophic_mortality_keeps_the_trigger() -> None:
    losses = [
        EventEmitter(engine_id="evolution", seed=1, tick=tick, era=1).emit(
            MASS_MORTALITY,
            EvolutionCauseCode.CATASTROPHIC_EVENT,
            cause_detail={"lost_fraction": 0.4},
            causation_id=METEOR.event_id,
        )
        for tick in (102, 103)
    ]
    fact = explain([METEOR, *losses]).facts[-1]

    assert fact.template_id == "T-MASS-MORTALITY-CATASTROPHIC-REPEATED"
    assert "meteoro" in fact.text.lower()
    assert fact.slots["occurrences"] == "2"


def test_the_register_falls_back_to_standard_when_there_is_no_variant() -> None:
    """A costura de registro: o M6.3 acrescenta variantes linha a linha.

    Sem o recuo, acrescentar um registro novo exigiria escrever TODAS as
    variantes de uma vez — e a alternativa a isso seria improvisar a
    simplificação em tempo de execução, que é onde a frase erra.
    """
    simple = renderer().render(context_of([life_emerged(era=1, tick=40)]), Register.SIMPLE)
    fact = simple.facts[0]

    assert fact.template_id == "T-LIFE-EMERGED"
    assert fact.register is Register.STANDARD, "o recuo devia declarar o registro REAL usado"
    assert fact.text == explain([life_emerged(era=1, tick=40)]).facts[0].text


# --- O caminho inteiro: Event Store -> dossiê -> prosa ------------------------


async def test_the_slice_use_case_goes_from_the_event_store_to_the_prose() -> None:
    """As duas metades do M6 juntas, escopadas no planeta (ADR 0023)."""
    use_case = ExplainSliceUseCase(InMemoryEventQuery.of("planet-a", CASCADE), renderer())
    explanation = await use_case.execute("planet-a", ContextSlice.of_era(1))

    assert explanation.planet_id == "planet-a"
    assert explanation.facts
    assert "meteoro" in explanation.summary.lower()


async def test_the_slice_use_case_does_not_cross_planets() -> None:
    """O vazamento mais caro desta plataforma, agora com prosa em cima dele.

    Narrar ao aluno a catástrofe do planeta de outro aluno seria ancorado num
    event log e inteiramente errado — a alucinação mais difícil de detectar que
    este desenho admite (ADR 0023).
    """
    use_case = ExplainSliceUseCase(InMemoryEventQuery.of("planet-a", CASCADE), renderer())
    explanation = await use_case.execute("planet-b", ContextSlice.of_era(1))

    assert "meteoro" not in explanation.summary.lower()
    assert explanation.facts[0].template_id == "T-QUIET-PERIOD"


async def test_the_slice_use_case_honours_the_register() -> None:
    use_case = ExplainSliceUseCase(InMemoryEventQuery.of("planet-a", CASCADE), renderer())
    standard = await use_case.execute("planet-a", ContextSlice.of_era(1), Register.STANDARD)
    simple = await use_case.execute("planet-a", ContextSlice.of_era(1), Register.SIMPLE)

    assert standard.summary != simple.summary
