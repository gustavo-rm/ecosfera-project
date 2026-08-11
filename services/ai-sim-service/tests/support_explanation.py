"""Montagem do renderizador de explicação para os testes — um lugar só.

O renderizador é sempre o MESMO que a produção usa, carregado do mesmo YAML
versionado. Um conjunto de templates sintético para teste provaria que o
mecanismo funciona e não provaria nada sobre a prosa que a criança lê — e é a
prosa que este marco existe para garantir.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.consumers.templates import TemplateSet, load_templates
from ecosfera_ai.shared_kernel.events import DomainEvent

TEMPLATES_PATH = Path("configs/explanation_templates.yaml")
RENDERER_SOURCE = Path("src/ecosfera_ai/application/consumers/render_explanation.py")


def templates() -> TemplateSet:
    return load_templates(TEMPLATES_PATH)


def renderer() -> ExplanationRenderer:
    return ExplanationRenderer(templates())


def context_of(
    events: list[DomainEvent], *, planet_id: str = "planet-m61", era: int = 1
) -> FactualContext:
    return FactualContext.of(planet_id, ContextSlice.of_era(era), tuple(events))


def explain(
    events: list[DomainEvent],
    *,
    register: Register = Register.STANDARD,
    era: int = 1,
) -> Explanation:
    return renderer().render(context_of(events, era=era), register)


def text_of(explanation: Explanation) -> str:
    return explanation.summary.lower()
