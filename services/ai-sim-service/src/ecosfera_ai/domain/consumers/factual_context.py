"""O DOSSIÊ FACTUAL — o que de fato aconteceu, derivado só do Event Store.

Este é o alicerce anti-alucinação do M6. O princípio que vale para todo o marco:
**a verdade sobre o planeta do aluno é o Event Store**. Um consumidor está
correto quando o que ele afirma é DERIVÁVEL da trilha de eventos, e alucina
quando não é. O `FactualContext` é exatamente essa matéria-prima verificável —
construída aqui, e apenas REESCRITA pelas subetapas seguintes.

## A regra que dá sentido a tudo: aqui não há prosa

O dossiê não contém uma frase, não traduz um `cause_code`, não decide faixa
etária e não sabe o que é pedagogia. É fato estruturado e neutro. A tradução para
linguagem humana é do consumidor de CIMA (ADR-ARCH-0002, Correção 1: a Visão
Educacional é RENDERIZADA pelo consumidor, não emitida pelo Engine — e, pela
mesma razão, não fabricada por esta camada).

A ordem do M6 depende disso: o template (M6.1) e o LLM (M6.3) reescrevem o que
está aqui; nenhum dos dois decide o que aconteceu. Se este módulo começar a
narrar, a fronteira entre "fato" e "redação" some, e com ela some o único
critério de correção que este marco tem.

## Especiação: ancestral comum, por CONSTRUÇÃO

`SpeciationFact` não CONSEGUE expressar "a espécie A deu origem à espécie B" — a
forma do dado tem um ancestral e duas linhagens irmãs, e um `__post_init__` que
recusa qualquer outra combinação. A Fase 0 corrigiu o significado do evento
(BIO-001) antes de o Tutor existir justamente para que o dossiê nascesse deste
lado; travá-lo no tipo é o que impede a regressão de voltar pela porta do
consumidor.

## Extinção: as duas famílias continuam separadas

`ExtinctionNature` preserva a distinção do ADR 0019 como DADO: uma comunidade bem
adaptada morta por um meteoro (`CATASTROPHIC`) segue distinguível de um declínio
ecológico (`ECOLOGICAL`). Isto não é tradução — é classificação estrutural pela
família do `cause_code`. Quem transforma a distinção em frase é o M6.1/M6.3; o
que o dossiê garante é que a informação chegue lá intacta.

## O grão é a COMUNIDADE (ADR 0024)

O Tutor fala da comunidade, porque é disso que o modelo dá conta com honestidade.
A camada de espécies COM IDENTIDADE (catálogo, censo, filogenia simplificada) é
pós-M6, e o ponto de encaixe dela está marcado em `SpeciationFact.lineages` e em
`ExtinctionFact.participants`: hoje esses campos carregam identificadores de
linhagem e papéis; quando a camada existir, passam a carregar identidades de
espécie sem que o formato do dossiê mude.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ecosfera_ai.domain.consumers.causal_tree import (
    CausalNode,
    build_causal_forest,
    descendants_of,
)
from ecosfera_ai.domain.consumers.vocabulary import (
    ANCESTOR_LINEAGE_FIELD,
    ANCESTOR_ROLE,
    CATASTROPHIC_CAUSE_CODE,
    GENETIC_DISTANCE_FIELD,
    LINEAGE_A_FIELD,
    LINEAGE_B_FIELD,
    LINEAGE_ROLE,
    NOTABLE_TRANSITIONS,
    SPECIATION_OCCURRED,
    SPECIES_EXTINCT,
    roles_in,
)
from ecosfera_ai.shared_kernel.events import DomainEvent, SimulationTime, event_to_dict


class MalformedSpeciationError(ValueError):
    """Uma `SpeciationOccurred` que não se lê como ancestral comum + duas linhagens.

    Falha em vez de degradar, e a razão é o BIO-001. As duas degradações
    possíveis são piores que o erro: pular o evento em silêncio faz o Tutor nunca
    mencionar uma especiação que ocorreu; aceitá-lo com uma linhagem só o faz
    narrar que uma espécie gerou outra — que é a escada de progresso que a
    plataforma existe para desfazer.
    """


class SliceKind(StrEnum):
    """Os três recortes que o M6.0 sabe montar."""

    ERA = "era"
    TICKS = "ticks"
    EVENT = "event"


@dataclass(frozen=True, slots=True)
class ContextSlice:
    """O QUE foi pedido — parte do dossiê, e não só argumento da consulta.

    Guardar o recorte junto do resultado é o que torna um dossiê auditável: quem
    o receber depois (o template, o LLM, uma avaliação adversarial do M6.4) sabe
    de que fatia ele fala, e um dossiê vazio de uma era vazia deixa de ser
    indistinguível de um dossiê que ninguém preencheu.
    """

    kind: SliceKind
    era: int | None = None
    from_tick: int | None = None
    to_tick: int | None = None
    event_id: str | None = None

    def __post_init__(self) -> None:
        required = {
            SliceKind.ERA: self.era is not None,
            SliceKind.TICKS: self.from_tick is not None and self.to_tick is not None,
            SliceKind.EVENT: self.event_id is not None,
        }
        if not required[self.kind]:
            raise ValueError(f"recorte {self.kind.value!r} sem os campos que o definem")
        if self.kind is SliceKind.TICKS and int(self.from_tick or 0) > int(self.to_tick or 0):
            raise ValueError("janela de ticks invertida: from_tick > to_tick")

    @classmethod
    def of_era(cls, era: int) -> ContextSlice:
        return cls(kind=SliceKind.ERA, era=era)

    @classmethod
    def of_ticks(cls, from_tick: int, to_tick: int) -> ContextSlice:
        return cls(kind=SliceKind.TICKS, from_tick=from_tick, to_tick=to_tick)

    @classmethod
    def of_event(cls, event_id: str) -> ContextSlice:
        return cls(kind=SliceKind.EVENT, event_id=event_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "era": self.era,
            "from_tick": self.from_tick,
            "to_tick": self.to_tick,
            "event_id": self.event_id,
        }


class ExtinctionNature(StrEnum):
    """As duas famílias de extinção do ADR 0019, como DADO e não como frase.

    `CATASTROPHIC` é abrupta e INDEPENDENTE de aptidão — a fração removida não
    olha para o genoma, e uma comunidade no próprio ótimo morre igual.
    `ECOLOGICAL` é gradual e mediada por adaptação: a comunidade não se sustentou
    nas condições que encontrou.
    """

    CATASTROPHIC = "catastrophic"
    ECOLOGICAL = "ecological"


@dataclass(frozen=True, slots=True)
class SpeciationFact:
    """Uma especiação: UM ancestral, DUAS linhagens irmãs, e a causa da divisão.

    O tipo é a garantia. `lineages` é um par, `ancestor` não é nenhum dos dois, e
    a ordem entre as irmãs não expressa precedência alguma — não há progenitora
    viva a nomear, porque a população ancestral se dividiu e não sobreviveu como
    uma terceira parte.

    **Ponto de encaixe da camada de espécies (ADR 0024, pós-M6).** Hoje `ancestor`
    e `lineages` carregam identificadores de LINHAGEM derivados da semente, porque
    o modelo é de comunidade e não tem identidades de espécie. Quando a camada de
    coortes existir, os mesmos três campos passam a carregar identidades de
    espécie e o formato do dossiê não muda — o que muda é a montante.
    """

    event_id: str
    occurred_at: SimulationTime
    cause_code: str
    ancestor: str
    lineages: tuple[str, ...]
    genetic_distance: float | None = None

    def __post_init__(self) -> None:
        if len(self.lineages) != 2:
            raise MalformedSpeciationError(
                f"especiação {self.event_id} com {len(self.lineages)} linhagem(ns): "
                "o modelo de ancestral comum exige exatamente duas (BIO-001)"
            )
        if len(set(self.lineages)) != 2:
            raise MalformedSpeciationError(
                f"especiação {self.event_id} com duas linhagens idênticas — não houve divisão"
            )
        if self.ancestor in self.lineages:
            raise MalformedSpeciationError(
                f"especiação {self.event_id} nomeia o ancestral como uma das linhagens "
                "resultantes: isso é 'A deu origem a B', e não ancestral comum (BIO-001)"
            )

    @classmethod
    def from_event(cls, event: DomainEvent) -> SpeciationFact:
        """Lê a especiação do envelope §4, pelos papéis e pelo `cause_detail`.

        Os dois caminhos existem no evento e dizem a mesma coisa: `participants`
        traz `ancestor:` / `lineage:` e `cause_detail` traz os três ids nomeados.
        Prefere-se `participants` porque é campo do envelope comum — o
        `cause_detail` é vocabulário do Engine, e um consumidor que dependesse só
        dele se acoplaria a quem emitiu.
        """
        ancestors = roles_in(event.participants, ANCESTOR_ROLE)
        lineages = roles_in(event.participants, LINEAGE_ROLE)
        if not ancestors:
            ancestors = (str(event.cause_detail[ANCESTOR_LINEAGE_FIELD]),)
        if not lineages:
            lineages = (
                str(event.cause_detail[LINEAGE_A_FIELD]),
                str(event.cause_detail[LINEAGE_B_FIELD]),
            )
        if len(ancestors) != 1:
            raise MalformedSpeciationError(
                f"especiação {event.event_id} com {len(ancestors)} ancestrais: "
                "uma divisão tem um ancestral comum e só um (BIO-001)"
            )
        distance = event.cause_detail.get(GENETIC_DISTANCE_FIELD)
        return cls(
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            cause_code=str(event.cause_code.value),
            ancestor=ancestors[0],
            lineages=tuple(lineages),
            genetic_distance=None if distance is None else float(distance),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tick": self.occurred_at.tick,
            "era": self.occurred_at.era,
            "cause_code": self.cause_code,
            "ancestor": self.ancestor,
            "lineages": list(self.lineages),
            "genetic_distance": self.genetic_distance,
        }


@dataclass(frozen=True, slots=True)
class ExtinctionFact:
    """Uma extinção, com a família da causa PRESERVADA para quem vai traduzir.

    `triggered_by` é o `causation_id`, e numa extinção catastrófica ele aponta
    para o EVENTO gatilho — o meteoro —, e não para o `TemperatureShift` que por
    acaso ocorreu no mesmo tick. Isso foi um defeito real do M4, encontrado pelo
    teste de cadeia e corrigido (ADR 0019, decisão 4); o dossiê o carrega adiante
    porque é o elo que separa "morreu porque um meteoro caiu" de "morreu porque
    esfriou".
    """

    event_id: str
    occurred_at: SimulationTime
    cause_code: str
    nature: ExtinctionNature
    participants: tuple[str, ...] = ()
    triggered_by: str | None = None

    @classmethod
    def from_event(cls, event: DomainEvent) -> ExtinctionFact:
        code = str(event.cause_code.value)
        return cls(
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            cause_code=code,
            nature=(
                ExtinctionNature.CATASTROPHIC
                if code == CATASTROPHIC_CAUSE_CODE
                else ExtinctionNature.ECOLOGICAL
            ),
            participants=tuple(event.participants),
            triggered_by=event.causation_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tick": self.occurred_at.tick,
            "era": self.occurred_at.era,
            "cause_code": self.cause_code,
            "nature": self.nature.value,
            "participants": list(self.participants),
            "triggered_by": self.triggered_by,
        }


@dataclass(frozen=True, slots=True)
class EraMarker:
    """Âncora temporal: onde o planeta mudou de estado qualitativo.

    Marcador é REFERÊNCIA, não destaque pedagógico. Ele diz "a vida surgiu no
    tick 312 da era 2"; se isso merece abrir a explicação é decisão do consumidor
    de cima.
    """

    era: int
    tick: int
    event_id: str
    event_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "era": self.era,
            "tick": self.tick,
            "event_id": self.event_id,
            "event_type": self.event_type,
        }


@dataclass(frozen=True, slots=True)
class FactualContext:
    """O dossiê: fato estruturado de um planeta, num recorte, e nada além disso.

    Todos os campos são DERIVADOS dos eventos. Nenhum vem do world-state, nenhum
    recalcula ciência, nenhum é prosa. Construa por `of()` — o construtor direto
    existe para o caso vazio e para a desserialização.
    """

    planet_id: str
    slice: ContextSlice
    events: tuple[DomainEvent, ...] = ()
    causal_roots: tuple[CausalNode, ...] = ()
    # Cadeia ASCENDENTE (efeito → raiz) do evento em foco, tal como o contrato de
    # query do M5 a devolve. Só o recorte por evento a preenche: nas fatias por
    # era e por ticks não há um "foco" de que subir.
    ancestry: tuple[DomainEvent, ...] = ()
    speciations: tuple[SpeciationFact, ...] = ()
    extinctions: tuple[ExtinctionFact, ...] = ()
    markers: tuple[EraMarker, ...] = ()
    _index: dict[str, DomainEvent] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def empty(cls, planet_id: str, context_slice: ContextSlice) -> FactualContext:
        """Nada aconteceu na fatia — e isso é um FATO, não um erro.

        O caso é comum e esperado. Especiação, por exemplo, é praticamente
        inalcançável no modelo atual (~6 σ de um passo de mutação; medido: zero
        especiações em 200 ticks nas sementes 2027 e 99 — `docs/decisions/
        deferred.md`). Uma era sem especiação alguma é o comportamento NORMAL, e
        um consumidor que tratasse a ausência como falha transformaria o normal em
        exceção — e, pior, empurraria quem for depurar a caçar um defeito que não
        existe.
        """
        return cls(planet_id=planet_id, slice=context_slice)

    @classmethod
    def of(
        cls,
        planet_id: str,
        context_slice: ContextSlice,
        events: tuple[DomainEvent, ...],
        *,
        ancestry: tuple[DomainEvent, ...] = (),
    ) -> FactualContext:
        """Projeta o dossiê sobre a trilha JÁ escopada no planeta.

        Puro e total: mesma entrada, mesma saída, sem I/O e sem relógio. Quem lê
        o Event Store é o `ContextAssembler`; aqui só se deriva.
        """
        ordered = tuple(
            sorted(events, key=lambda e: (e.occurred_at.era, e.occurred_at.tick, e.event_id))
        )
        return cls(
            planet_id=planet_id,
            slice=context_slice,
            events=ordered,
            causal_roots=build_causal_forest(ordered),
            ancestry=ancestry,
            speciations=tuple(
                SpeciationFact.from_event(e) for e in ordered if e.event_type == SPECIATION_OCCURRED
            ),
            extinctions=tuple(
                ExtinctionFact.from_event(e) for e in ordered if e.event_type == SPECIES_EXTINCT
            ),
            markers=tuple(
                EraMarker(
                    era=e.occurred_at.era,
                    tick=e.occurred_at.tick,
                    event_id=e.event_id,
                    event_type=e.event_type,
                )
                for e in ordered
                if e.event_type in NOTABLE_TRANSITIONS
            ),
            _index={e.event_id: e for e in ordered},
        )

    @property
    def is_empty(self) -> bool:
        """Sem eventos na fatia. Explícito, e não uma ausência a ser inferida."""
        return not self.events

    def event(self, event_id: str) -> DomainEvent | None:
        """O evento pelo id, dentro do dossiê."""
        return self._index.get(event_id)

    def cause_of(self, event_id: str) -> DomainEvent | None:
        """Um passo ASCENDENTE: o evento que causou este, se está no dossiê.

        Um passo, e não uma travessia. A subida completa é
        `walk_causal_chain`, do contrato de query — reimplementá-la aqui daria
        duas cópias da mesma regra, que é como esta base já se machucou antes.
        """
        current = self._index.get(event_id)
        if current is None or current.causation_id is None:
            return None
        return self._index.get(current.causation_id)

    def consequences_of(self, event_id: str) -> tuple[DomainEvent, ...]:
        """Travessia DESCENDENTE completa: tudo o que decorreu do evento."""
        return descendants_of(self.events, event_id)

    def to_dict(self) -> dict[str, Any]:
        """Dossiê inteiro como dado portável — o JSON que um humano inspeciona.

        Nem uma linha de prosa sai daqui: `cause_code` continua enum, os fatos
        continuam estruturados, e a frase é de quem consome.
        """
        return {
            "planet_id": self.planet_id,
            "slice": self.slice.to_dict(),
            "is_empty": self.is_empty,
            "events": [event_to_dict(e) for e in self.events],
            "causal_roots": [node.to_dict() for node in self.causal_roots],
            "ancestry": [event_to_dict(e) for e in self.ancestry],
            "speciations": [fact.to_dict() for fact in self.speciations],
            "extinctions": [fact.to_dict() for fact in self.extinctions],
            "markers": [marker.to_dict() for marker in self.markers],
        }


__all__ = [
    "ContextSlice",
    "EraMarker",
    "ExtinctionFact",
    "ExtinctionNature",
    "FactualContext",
    "MalformedSpeciationError",
    "SliceKind",
    "SpeciationFact",
]
