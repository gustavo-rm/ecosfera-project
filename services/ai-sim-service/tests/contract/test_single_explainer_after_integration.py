"""Depois do M6.1 há UM narrador de eventos — o antigo evoluiu, não foi duplicado.

A decisão de projeto do M6.1, e a razão dela (ADR 0026).

`ExplainFromEventsUseCase` existe desde o M1 e já traduzia evento em prosa. A
tentação era deixá-lo em paz e escrever um segundo explicador ao lado: mais
rápido, e o custo apareceria depois — duas prosas para a mesma trilha, duas
correções de vocabulário a cada revisão pedagógica, e uma delas esquecida.

O que ele fazia era propagar VARIÁVEIS: `co2↑ ⇒ temperatura↑`, em largura, até a
profundidade três. Correto como ciência geral, e não derivável da trilha daquele
planeta — os saltos afirmam efeitos que o log pode não conter. Para `/ai/explain`
isso é o serviço prestado (o cliente manda observações, não há trilha). Para
narrar o que aconteceu é o defeito central.

Então: o motor de regras continua, no lugar em que projetar é o que se pede; a
narração de EVENTOS passou a ser uma só, e é a do renderizador por template.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.support_context import branching_cascade
from tests.support_explanation import RENDERER_SOURCE, renderer

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.feedback.explain_from_events import (
    ExplainFromEventsUseCase,
    load_translation,
)
from ecosfera_ai.domain.feedback.models import Observation
from ecosfera_ai.domain.feedback.rule_loader import build_engine

SRC = Path("src/ecosfera_ai")
CASCADE = branching_cascade()


def _use_case() -> ExplainFromEventsUseCase:
    return ExplainFromEventsUseCase(
        ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml"))),
        load_translation(Path("configs/event_observations.yaml")),
        renderer(),
    )


# --- O caso de uso antigo continua sendo A porta de entrada ------------------


def test_the_original_use_case_still_exists_and_still_narrates_events() -> None:
    """Evoluir significa que o chamador não precisou trocar de nome."""
    outcome = _use_case().execute("planet-m61", CASCADE)
    assert outcome.explanation.summary
    assert outcome.explanation.chain


def test_it_now_narrates_through_the_template_renderer() -> None:
    """E a prosa é a do M6.1: os ids do rastro são de TEMPLATE, não de regra."""
    outcome = _use_case().execute("planet-m61", CASCADE)
    fired = {step.rule_id for step in outcome.explanation.chain}

    assert fired, "a narração não produziu passo algum"
    assert all(rule_id.startswith("T-") for rule_id in fired), (
        f"algum passo ainda vem da propagação de variáveis: {fired}"
    )


def test_the_rendered_explanation_travels_alongside_the_old_contract() -> None:
    """O contrato de saída não mudou, e a ancoragem nova viaja junto."""
    outcome = _use_case().execute("planet-m61", CASCADE)
    assert outcome.rendered is not None
    assert outcome.explanation.summary == outcome.rendered.summary
    assert outcome.explanation.source == "rules"
    assert outcome.explanation.grounded is True


def test_the_trace_still_accompanies_the_explanation() -> None:
    """O rastro por `causation_id` continua sendo entregue (auditabilidade)."""
    assert _use_case().execute("planet-m61", CASCADE).trace


# --- E há um só narrador de eventos ------------------------------------------


def _modules_that_render_event_prose() -> set[str]:
    """Quem transforma evento em frase para o aluno, no código de produção.

    O critério é importar o renderizador de templates OU o motor de regras. Um
    terceiro caminho — alguém formatando frase à mão a partir de `DomainEvent` —
    apareceria como módulo que casa nenhum dos dois e ainda assim escreve prosa;
    é o que `test_no_module_builds_student_prose_by_hand` procura.
    """
    found: set[str] = set()
    for source in sorted(SRC.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        if any("consumers.narration" in m or "consumers.templates" in m for m in imported):
            found.add(str(source.relative_to(SRC)))
    return found


def test_only_the_designated_modules_render_event_prose() -> None:
    """Uma lista curta e explícita — crescer aqui é sinal de duplicação."""
    assert _modules_that_render_event_prose() <= {
        "domain/consumers/narration.py",
        "domain/consumers/__init__.py",
        "application/consumers/render_explanation.py",
        "interfaces/http/deps.py",
    }


def test_no_module_builds_student_prose_by_hand() -> None:
    """Nenhum módulo escreve frase pedagógica fora dos arquivos versionados.

    A varredura procura o sinal mais barato e mais confiável: literais longos em
    português com "porque"/"por mais" dentro do código-fonte. A prosa vive em
    YAML; um parágrafo hardcoded seria um segundo narrador nascendo.
    """
    marks = ("porque a comunidade", "por mais bem adaptada", "ancestral comum e seguem")
    for source in sorted(SRC.rglob("*.py")):
        text = source.read_text(encoding="utf-8")
        for mark in marks:
            assert mark not in text, (
                f"{source} carrega prosa de aluno no código — ela pertence ao YAML versionado"
            )


def test_the_rules_engine_is_still_reachable_where_projection_is_the_service() -> None:
    """`/ai/explain` continua projetando: lá não há trilha, e projetar é o pedido.

    Este teste é o outro lado da decisão. Sem ele, "um só narrador" poderia ser
    lido como "o motor de regras foi removido" — e removê-lo teria quebrado um
    endpoint que não tem nada a ver com narrar eventos.
    """
    explanation = ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml"))).execute(
        "planet-m61", [Observation(variable="co2", delta=0.3)]
    )
    assert explanation.chain
    assert all(step.rule_id.startswith("R-") for step in explanation.chain)


def test_the_renderer_lives_in_one_place() -> None:
    """Guarda contra um segundo renderizador aparecer com outro nome."""
    assert RENDERER_SOURCE.is_file()
    matches = [p for p in SRC.rglob("*.py") if "ExplanationRenderer" in p.read_text("utf-8")]
    defining = [p for p in matches if "class ExplanationRenderer" in p.read_text("utf-8")]
    assert len(defining) == 1, f"há mais de um renderizador definido: {defining}"
