"""Montagem do renderizador de explicação para os testes — um lugar só.

O renderizador é sempre o MESMO que a produção usa, carregado do mesmo YAML
versionado. Um conjunto de templates sintético para teste provaria que o
mecanismo funciona e não provaria nada sobre a prosa que a criança lê — e é a
prosa que este marco existe para garantir.
"""

from __future__ import annotations

from dataclasses import replace
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


def rotated_templates(offset: int) -> TemplateSet:
    """O mesmo conjunto, com as formas de cada template giradas de `offset`.

    É o que torna "a fundamentação não depende da forma" uma afirmação
    verificável em vez de uma esperança. O renderizador escolhe a forma pela
    POSIÇÃO da frase, então na prática cada template aparece com uma forma só por
    dossiê; girar o conjunto exercita as outras contra o mesmo dossiê, e permite
    comparar fato a fato o que deveria ser idêntico — tudo, menos o texto.

    Um template de forma única gira para si mesmo, e é isso que faz o giro ser
    seguro para o arquivo inteiro em vez de só para a família da cascata.
    """
    loaded = templates()
    return replace(
        loaded,
        templates={
            key: tuple(forms[(index + offset) % len(forms)] for index in range(len(forms)))
            for key, forms in loaded.templates.items()
        },
    )


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
