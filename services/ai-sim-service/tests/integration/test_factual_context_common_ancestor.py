"""BIO-001 no LADO DE LEITURA: quem reconstrói a cadeia lê ancestral comum.

**Estado do M6.0.** Não existe `FactualContext` neste repositório — o M6 não foi
iniciado. O consumidor read-side que existe hoje é
`ExplainFromEventsUseCase` + `causal_trace`, e é ele que o M6.0 vai estender:
mesma trilha, mesmo envelope, mesma reconstrução por `causation_id`. Guardar a
leitura AQUI é o que impede o M6.0 de nascer sobre o modelo "A→B" — que é
exatamente o risco que a Fase 0 existe para fechar, e que só apareceria depois,
já com o Tutor narrando ancestralidade errada com autoridade.

O que se afirma:

  1. o consumidor consegue extrair um ancestral e DUAS linhagens do evento, sem
     conhecer o Engine que o emitiu;
  2. a reconstrução por `causation_id` não transforma a especiação em
     "um evento gerou o outro" entre espécies;
  3. a explicação que chega ao aluno fala de ancestral comum e não afirma que uma
     espécie deu origem a outra.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from tests.support import speciation_event

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.feedback.explain_from_events import (
    ExplainFromEventsUseCase,
    causal_trace,
    load_translation,
)
from ecosfera_ai.domain.consumers.templates import load_templates
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.evolution.events import ANCESTOR_ROLE, LINEAGE_ROLE
from ecosfera_ai.shared_kernel.events import DomainEvent

TRANSLATION = load_translation(Path("configs/event_observations.yaml"))
USE_CASE = ExplainFromEventsUseCase(
    ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml"))),
    TRANSLATION,
    # Desde o M6.1 a narração de eventos sai do renderizador por template, e não
    # da propagação de variáveis do motor de regras (ADR 0026). O que este
    # arquivo guarda não mudou: a leitura de ancestral comum tem de sobreviver à
    # troca do narrador — se ela dependesse de qual motor escreve a frase, não
    # seria garantia nenhuma.
    ExplanationRenderer(load_templates(Path("configs/explanation_templates.yaml"))),
)

# As formulações proibidas ao consumidor (BIO-001). A regra dura: é proibido
# gerar texto que afirme que uma espécie deu origem a outra.
FORBIDDEN_ANCESTRY = (
    "deu origem",
    "deram origem",
    "originou a espécie",
    "gerou a espécie",
    "descende da espécie",
    "virou uma nova espécie",
)


def _read_roles(event: DomainEvent, role: str) -> list[str]:
    """Como um consumidor lê os papéis: pelo prefixo, sem conhecer o Engine."""
    return [p.removeprefix(f"{role}:") for p in event.participants if p.startswith(f"{role}:")]


# --- O consumidor extrai a ancestralidade correta -----------------------------


def test_a_consumer_reads_one_ancestor_and_two_lineages() -> None:
    event = speciation_event()
    assert len(_read_roles(event, ANCESTOR_ROLE)) == 1
    assert len(_read_roles(event, LINEAGE_ROLE)) == 2


def test_the_consumer_never_finds_a_parent_child_pair_of_current_species() -> None:
    """O que existe no evento é uma divisão, e uma divisão não tem progenitora viva."""
    event = speciation_event()
    ancestor = _read_roles(event, ANCESTOR_ROLE)[0]
    lineages = _read_roles(event, LINEAGE_ROLE)
    assert ancestor not in lineages
    assert len(set(lineages)) == 2


def test_the_causal_trace_does_not_turn_speciation_into_a_lineage_of_species() -> None:
    """`causal_trace` liga EVENTOS por `causation_id`, não espécies por descendência.

    Confundir as duas coisas é a leitura errada mais fácil de fazer: a cadeia
    `LifeEmerged → SpeciationOccurred` seria lida como "a espécie que surgiu
    gerou a que especiou". Os elos são entre `event_id`, e nunca entre linhagens.
    """
    speciation = speciation_event()
    ancestor_id = str(speciation.cause_detail["ancestor_lineage_id"])
    lineage_ids = {
        str(speciation.cause_detail["lineage_a_id"]),
        str(speciation.cause_detail["lineage_b_id"]),
    }

    for link in causal_trace([speciation]):
        assert link.cause_event != ancestor_id
        assert link.effect_event not in lineage_ids


def test_the_trace_still_reconstructs_the_chain_that_produced_the_speciation() -> None:
    """A leitura corrigida não custou a proveniência: o elo causa→efeito continua."""
    trigger = DomainEvent(
        event_id="evt-capacity",
        event_type="CarryingCapacityShift",
        engine_id="resource",
        occurred_at=speciation_event().occurred_at,
        seed=speciation_event().seed,
        cause_code=speciation_event().cause_code,
        correlation_id=speciation_event().correlation_id,
    )
    speciation = replace(speciation_event(), causation_id=trigger.event_id)
    links = causal_trace([trigger, speciation])
    assert [link.effect_type for link in links] == ["SpeciationOccurred"]
    assert links[0].cause_type == "CarryingCapacityShift"


# --- O que o aluno ouve -------------------------------------------------------


def test_the_explanation_speaks_of_a_common_ancestor() -> None:
    outcome = USE_CASE.execute("planet-fase0", [speciation_event()])
    text = outcome.explanation.summary.lower()
    assert "ancestral comum" in text, f"a especiação foi narrada sem ancestral comum: {text!r}"
    assert "duas linhagens" in text


def test_the_explanation_never_says_one_species_produced_another() -> None:
    outcome = USE_CASE.execute("planet-fase0", [speciation_event()])
    text = outcome.explanation.summary.lower()
    for phrase in FORBIDDEN_ANCESTRY:
        assert phrase not in text, f"a explicação afirma ancestralidade A→B: {phrase!r}"


def test_no_causal_rule_template_asserts_a_to_b_ancestry() -> None:
    """A proibição vale para o arquivo inteiro, e não só para a frase da especiação."""
    import yaml

    raw = yaml.safe_load(Path("configs/causal_rules.yaml").read_text(encoding="utf-8"))
    for rule in raw["rules"]:
        template = str(rule["template"]).lower()
        for phrase in FORBIDDEN_ANCESTRY:
            assert phrase not in template, (
                f"{rule['id']} afirma que uma espécie gerou outra ({phrase!r})"
            )


def test_the_speciation_event_is_not_silent_to_the_reader() -> None:
    """Antes da Fase 0 a observação de especiação não disparava regra alguma.

    Um evento que o consumidor traduz e ninguém narra é pior que ausência: o
    aluno vê a riqueza mudar e preenche o silêncio com a intuição espontânea.
    """
    outcome = USE_CASE.execute("planet-fase0", [speciation_event()])
    assert outcome.explanation.chain, "a especiação voltou a não produzir explicação alguma"
    assert outcome.explanation.source == "rules", "LLM só no M6"
