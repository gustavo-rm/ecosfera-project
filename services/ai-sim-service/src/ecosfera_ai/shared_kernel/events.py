"""Envelope comum de Domain Event (Canal B — Spec §4, ADR-ARCH-0002).

Todo evento significativo responde, como DADO: o quê, quando, onde, quem, sob
quais fatores ambientais, quais genes, quais recursos, por qual causa e com
quais consequências. Explicabilidade é **requisito de esquema** — é o que
permite ao Tutor narrar o fenômeno sem recalcular ciência.

Duas regras estruturais valem para todos:

* **`cause_code` é enum, nunca prosa.** A frase pedagógica é do consumidor
  (Education/AI Tutor), não do Engine científico (ADR-ARCH-0002, Correção 1).
* **Identificadores são derivados, não sorteados.** `uuid4()` dentro do loop
  quebraria o replay bit-a-bit: a mesma semente produziria ids diferentes. Aqui
  os ids saem de `uuid5` sobre (semente, era, tick, engine, tipo, sequência),
  então a mesma trajetória gera exatamente os mesmos identificadores (RF-023).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

# Namespace fixo do ECOSFERA para derivação determinística de identificadores.
# Constante: mudá-lo invalidaria os ids de todos os eventos já gravados.
EVENT_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


class CauseCodeEnum(StrEnum):
    """Base extensível dos códigos de causa.

    Sem membros de propósito: em Python só se pode herdar de um Enum vazio, e é
    exatamente isso que permite a cada Engine declarar o próprio vocabulário
    (`class ClimateCauseCode(CauseCodeEnum): ...`) sem que o envelope precise
    conhecer todos eles.
    """


class CoreCauseCode(CauseCodeEnum):
    """Causas universais da moldura — nenhuma delas é científica."""

    TICK_CLOSED = "TICK_CLOSED"
    ERA_CLOSED = "ERA_CLOSED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    INVARIANT_BREACH = "INVARIANT_BREACH"
    ENGINE_HEARTBEAT = "ENGINE_HEARTBEAT"


class Granularity(StrEnum):
    """Nível de detalhe do evento (ADR-ARCH-0002, Correção 2).

    `AGGREGATE` é o padrão: eventos por organismo por tick explodem o Event
    Store e passam a ser o próprio gargalo. `PER_ORGANISM` existe para
    investigação pontual, sob flag ou amostragem.
    """

    AGGREGATE = "aggregate"
    PER_ORGANISM = "per_organism"


# Tipo de evento reservado ao Canal B técnico (orçamento estourado, invariante
# recortada). É diagnóstico, não ciência: nunca realimenta a simulação.
DIAGNOSTIC_EVENT_TYPE = "DiagnosticRaised"


@dataclass(frozen=True, slots=True)
class SimulationTime:
    """QUANDO, em tempo de simulação — determinístico, não relógio de parede."""

    tick: int
    era: int


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Envelope único de evento de domínio (Spec §4, campo a campo)."""

    event_id: str
    event_type: str
    engine_id: str
    occurred_at: SimulationTime
    seed: int
    cause_code: CauseCodeEnum
    correlation_id: str
    causation_id: str | None = None
    location: Mapping[str, str] = field(default_factory=dict)
    participants: tuple[str, ...] = ()
    environmental_factors: tuple[str, ...] = ()
    genes: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    cause_detail: Mapping[str, float | int | str] = field(default_factory=dict)
    consequences: tuple[str, ...] = ()
    granularity: Granularity = Granularity.AGGREGATE

    def __post_init__(self) -> None:
        if not isinstance(self.cause_code, CauseCodeEnum):
            raise TypeError(
                "cause_code precisa ser um CauseCodeEnum (causa estruturada); "
                "prosa pedagógica é responsabilidade do consumidor"
            )
        object.__setattr__(self, "location", MappingProxyType(dict(self.location)))
        object.__setattr__(self, "cause_detail", MappingProxyType(dict(self.cause_detail)))

    @property
    def is_diagnostic(self) -> bool:
        """Distingue a visão técnica da científica sem um segundo envelope."""
        return self.event_type == DIAGNOSTIC_EVENT_TYPE


def deterministic_id(*parts: object) -> str:
    """Deriva um UUID estável a partir das partes — mesma entrada, mesmo id."""
    return str(uuid.uuid5(EVENT_NAMESPACE, "|".join(str(part) for part in parts)))


def correlation_id_for(seed: int, era: int, tick: int) -> str:
    """Correlação de um tick inteiro: agrupa a cadeia causal daquele instante."""
    return deterministic_id("correlation", seed, era, tick)


@dataclass(slots=True)
class EventEmitter:
    """Fábrica de eventos de um Engine em um tick — ids determinísticos.

    O contador interno entra na derivação do `event_id`, garantindo unicidade
    sem aleatoriedade: o n-ésimo evento daquele Engine naquele tick tem sempre o
    mesmo identificador.
    """

    engine_id: str
    seed: int
    tick: int
    era: int
    _sequence: int = field(default=0, init=False)

    @property
    def correlation_id(self) -> str:
        return correlation_id_for(self.seed, self.era, self.tick)

    @property
    def emitted(self) -> int:
        """Quantos eventos já saíram — alimenta o orçamento por tick (Spec §6)."""
        return self._sequence

    def emit(
        self,
        event_type: str,
        cause_code: CauseCodeEnum,
        *,
        location: Mapping[str, str] | None = None,
        participants: Sequence[str] = (),
        environmental_factors: Sequence[str] = (),
        genes: Sequence[str] = (),
        resources: Sequence[str] = (),
        cause_detail: Mapping[str, float | int | str] | None = None,
        consequences: Sequence[str] = (),
        causation_id: str | None = None,
        granularity: Granularity = Granularity.AGGREGATE,
    ) -> DomainEvent:
        """Monta um evento completo no envelope §4 e avança a sequência."""
        self._sequence += 1
        return DomainEvent(
            event_id=deterministic_id(
                self.seed, self.era, self.tick, self.engine_id, event_type, self._sequence
            ),
            event_type=event_type,
            engine_id=self.engine_id,
            occurred_at=SimulationTime(tick=self.tick, era=self.era),
            seed=self.seed,
            cause_code=cause_code,
            correlation_id=self.correlation_id,
            causation_id=causation_id,
            location=location or {},
            participants=tuple(participants),
            environmental_factors=tuple(environmental_factors),
            genes=tuple(genes),
            resources=tuple(resources),
            cause_detail=cause_detail or {},
            consequences=tuple(consequences),
            granularity=granularity,
        )


def diagnostic_event(
    emitter: EventEmitter,
    cause_code: CauseCodeEnum,
    detail: Mapping[str, float | int | str],
    *,
    causation_id: str | None = None,
) -> DomainEvent:
    """Evento da visão técnica (orçamento, invariante) — mesmo envelope §4.

    Um segundo tipo de envelope violaria a fonte única de verdade do
    ADR-ARCH-0002: o Event Store guarda um só formato, e a visão técnica é uma
    PROJEÇÃO filtrada por `event_type`.
    """
    return emitter.emit(
        DIAGNOSTIC_EVENT_TYPE,
        cause_code,
        cause_detail=detail,
        causation_id=causation_id,
    )
