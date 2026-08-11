"""Feedback causal derivado do Event Store, não do world-state (ADR 0011).

Fecha o embrião do AI Tutor previsto no ADR-ARCH-0001: um consumidor read-side
que explica o fenômeno **sem recalcular ciência** e **sem inspecionar memória de
Engine**. Não há LLM aqui — isso é o M6.3.

Duas fronteiras que este módulo respeita de propósito:

* **Não importa nenhum Engine.** Conhece o vocabulário dos eventos (nomes de
  tipo e campos de `cause_detail`), que vem de `configs/event_observations.yaml`.
  Um Engine pode ser reescrito inteiro sem tocar aqui, desde que continue
  emitindo o mesmo envelope §4.
* **Não escreve prosa científica.** O evento traz `cause_code` estruturado; a
  frase é do consumidor. É a Correção 1 do ADR-ARCH-0002 aplicada na prática.

## O que o M6.1 mudou aqui, e por quê

Até o M6.0 este caso de uso narrava assim: evento → observação `(variável,
delta)` → motor de regras → prosa. O motor de regras é um PROPAGADOR: a partir
de `co2↑` ele deriva `temperatura↑`, e daí `gelo↓`, em busca em largura até a
profundidade três.

Isso é correto como ciência geral e é exatamente o que `/ai/explain` precisa —
lá o cliente manda observações, não existe trilha, e projetar para a frente é o
serviço prestado. Mas para NARRAR O QUE ACONTECEU num planeta é o defeito
central: a observação descarta a identidade do evento (qual meteoro, qual tick,
quais linhagens), e os saltos seguintes afirmam efeitos que o log pode não
conter. Uma frase verdadeira como ciência e não derivável daquela trilha é
precisamente a alucinação que o M6 existe para impedir — e ela não precisa de um
LLM para acontecer.

Desde o M6.1 a narração vem do `ExplanationRenderer`, que lê o `FactualContext`
e preenche templates com campos do dossiê, com a atribuição causal saindo do
`causation_id` REAL. Há UM narrador de eventos, e é ele.

O motor de regras continua vivo e no lugar certo: `/ai/explain` (observações do
cliente) e o recuo por delta agregado do `AdvanceEraUseCase`, que ocorre quando
não há evento algum a narrar. Nenhum dos dois é narração de trilha.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.domain.consumers.explanation import ExplainedFact, Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.feedback.models import (
    CausalExplanation,
    CausalStep,
    Direction,
    Observation,
)
from ecosfera_ai.shared_kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class EventMapping:
    """Como um tipo de evento vira uma observação do motor de regras."""

    event_type: str
    variable: str
    field: str | None = None
    minuend: str | None = None
    subtrahend: str | None = None
    # Quando presente, esta entrada só vale para o `cause_code` nomeado. É o que
    # permite ao MESMO tipo de evento virar observações DIFERENTES conforme o
    # mecanismo — a distinção entre extinção catastrófica e ecológica (ADR 0019).
    #
    # Sem isso, `SpeciesExtinct` viraria sempre a mesma observação, o motor de
    # regras dispararia as mesmas regras, e o aluno ouviria "a espécie não
    # tolerou o ambiente" mesmo quando um meteoro a matou.
    cause_code: str | None = None

    def delta_of(self, detail: Mapping[str, Any]) -> float | None:
        """Extrai a magnitude do `cause_detail`, ou None se o evento não a traz."""
        if self.field is not None:
            value = detail.get(self.field)
            return None if value is None else float(value)
        if self.minuend is not None and self.subtrahend is not None:
            after, before = detail.get(self.minuend), detail.get(self.subtrahend)
            if after is None or before is None:
                return None
            return float(after) - float(before)
        return None


@dataclass(frozen=True, slots=True)
class EventTranslation:
    """Tabela versionada de tradução evento -> observação."""

    version: int
    mappings: Mapping[str, EventMapping]
    # Entradas especializadas por (tipo, cause_code). Consultadas ANTES das
    # genéricas: o específico ganha do geral.
    by_cause: Mapping[tuple[str, str], EventMapping] = field(default_factory=dict)

    def mapping_for(self, event: DomainEvent) -> EventMapping | None:
        """Escolhe a tradução: a especializada por causa, se houver."""
        specific = self.by_cause.get((event.event_type, str(event.cause_code)))
        return specific if specific is not None else self.mappings.get(event.event_type)

    def observations(self, events: Iterable[DomainEvent]) -> list[Observation]:
        """Traduz a trilha, ignorando diagnóstico técnico e tipos desconhecidos.

        Um evento sem tradução é silenciosamente pulado: o Event Store cresce com
        Engines novos, e o tutor não pode quebrar porque apareceu um tipo que ele
        ainda não sabe narrar.
        """
        result: list[Observation] = []
        for event in events:
            if event.is_diagnostic:
                continue
            mapping = self.mapping_for(event)
            if mapping is None:
                continue
            delta = mapping.delta_of(event.cause_detail)
            if delta is None or delta == 0.0:
                continue
            result.append(Observation(variable=mapping.variable, delta=delta))
        return result


def load_translation(path: Path) -> EventTranslation:
    """Lê a tabela do YAML versionado."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mappings: dict[str, EventMapping] = {}
    by_cause: dict[tuple[str, str], EventMapping] = {}
    for entry in raw.get("mappings", []):
        source = entry.get("delta_from", {})
        mapping = EventMapping(
            event_type=str(entry["event_type"]),
            variable=str(entry["variable"]),
            field=source.get("field"),
            minuend=source.get("minuend"),
            subtrahend=source.get("subtrahend"),
            cause_code=(None if entry.get("cause_code") is None else str(entry["cause_code"])),
        )
        if mapping.cause_code is None:
            mappings[mapping.event_type] = mapping
        else:
            by_cause[(mapping.event_type, mapping.cause_code)] = mapping
    return EventTranslation(
        version=int(raw.get("version", 1)), mappings=mappings, by_cause=by_cause
    )


@dataclass(frozen=True, slots=True)
class CausalLink:
    """Um elo do rastro causal, reconstruído por `causation_id`."""

    cause_event: str
    cause_type: str
    effect_event: str
    effect_type: str
    cause_code: str


@dataclass(frozen=True, slots=True)
class EventExplanation:
    """Explicação do tutor mais o rastro que a sustenta (auditabilidade).

    `rendered` é a explicação do M6.1 com a ancoragem campo a campo; `explanation`
    é a mesma coisa no contrato de saída de sempre, para que a API e o
    `AdvanceEraUseCase` não precisassem mudar junto.
    """

    explanation: CausalExplanation
    trace: tuple[CausalLink, ...] = ()
    rendered: Explanation | None = None


class ExplainFromEventsUseCase:
    """Narra a trilha de eventos, sem LLM — pelo renderizador do M6.1.

    `explain` (motor de regras) continua injetado porque o caso de uso segue
    servindo o caminho de OBSERVAÇÕES; o que ele não faz mais é narrar eventos
    por propagação de variáveis (ver a nota de módulo).
    """

    def __init__(
        self,
        explain: ExplainCausalUseCase,
        translation: EventTranslation,
        renderer: ExplanationRenderer,
    ) -> None:
        self._explain = explain
        self._translation = translation
        self._renderer = renderer

    def execute(
        self,
        planet_id: str,
        events: Sequence[DomainEvent],
        register: Register = Register.STANDARD,
    ) -> EventExplanation:
        """Monta o dossiê da trilha recebida e o narra.

        `FactualContext.of` é construtor PURO — nenhuma leitura de Event Store
        acontece aqui. Quem já tem a trilha em mãos (o `AdvanceEraUseCase`, que
        acabou de rodar a era) não precisa relê-la para ser narrado.
        """
        context = FactualContext.of(
            planet_id,
            ContextSlice.of_era(_era_of(events)),
            tuple(events),
        )
        rendered = self._renderer.render(context, register)
        return EventExplanation(
            explanation=self._as_causal_explanation(planet_id, rendered, context),
            trace=causal_trace(events),
            rendered=rendered,
        )

    def _as_causal_explanation(
        self, planet_id: str, rendered: Explanation, context: FactualContext
    ) -> CausalExplanation:
        """Adapta a explicação do M6.1 ao contrato de saída existente.

        O `CausalStep` nasceu para propagação de variáveis, e a narração por
        evento não tem exatamente essa forma. A adaptação usa a tradução do M1
        (`event_observations.yaml`) para recuperar a grandeza e o SINAL do
        evento — dado real do `cause_detail`, não convenção — e declara
        `Direction.NONE` quando o evento não mede grandeza alguma.
        """
        return CausalExplanation(
            planet_id=planet_id,
            summary=rendered.summary,
            chain=[self._step_for(fact, context) for fact in rendered.facts],
            grounded=True,
            source="rules",
        )

    def _step_for(self, fact: ExplainedFact, context: FactualContext) -> CausalStep:
        """Um passo do contrato antigo a partir de um fato narrado.

        `cause` é a grandeza do evento que CAUSOU este, quando o dossiê o contém;
        na ausência de causa registrada o passo é raiz e cause == effect. Nada
        aqui infere um elo que o `causation_id` não traga.
        """
        event = None if fact.grounding.event_id is None else context.event(fact.grounding.event_id)
        effect, direction = self._variable_of(event)
        cause = effect
        if event is not None:
            parent = context.cause_of(event.event_id)
            if parent is not None:
                cause, _ = self._variable_of(parent)
        return CausalStep(
            cause=cause,
            effect=effect,
            direction=direction,
            rule_id=fact.template_id,
            explanation=fact.text,
        )

    def _variable_of(self, event: DomainEvent | None) -> tuple[str, Direction]:
        """Grandeza e sentido do evento, quando a tradução do M1 os conhece."""
        if event is None:
            return "", Direction.NONE
        mapping = self._translation.mapping_for(event)
        if mapping is None:
            return event.event_type, Direction.NONE
        delta = mapping.delta_of(event.cause_detail)
        if delta is None:
            return mapping.variable, Direction.NONE
        return mapping.variable, (Direction.UP if delta >= 0 else Direction.DOWN)


def _era_of(events: Sequence[DomainEvent]) -> int:
    """A era da trilha recebida — a do primeiro evento, ou zero se não há trilha."""
    return events[0].occurred_at.era if events else 0


def causal_trace(events: Sequence[DomainEvent]) -> tuple[CausalLink, ...]:
    """Reconstrói os elos causa->efeito invertendo `causation_id`.

    Os Engines não preenchem `consequences` na emissão porque, no instante em que
    emitem, os efeitos ainda não aconteceram — inventá-los exigiria que um Engine
    soubesse o que os seguintes vão fazer. A ligação para a frente é PROJEÇÃO do
    Event Store, e é esta função.
    """
    by_id = {event.event_id: event for event in events}
    links: list[CausalLink] = []
    for event in events:
        parent = by_id.get(event.causation_id) if event.causation_id else None
        if parent is None:
            continue
        links.append(
            CausalLink(
                cause_event=parent.event_id,
                cause_type=parent.event_type,
                effect_event=event.event_id,
                effect_type=event.event_type,
                cause_code=str(event.cause_code),
            )
        )
    return tuple(links)
