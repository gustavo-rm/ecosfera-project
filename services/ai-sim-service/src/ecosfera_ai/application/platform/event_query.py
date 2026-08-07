"""Contrato de LEITURA do Event Store — o que o M6 vai assinar.

O ADR-ARCH-0002 fala em "três públicos, uma fonte de verdade": científico,
técnico e educacional leem a MESMA trilha por projeções diferentes. Este módulo
entrega o contrato de consulta e duas projeções; a educacional é do M6 e NÃO é
implementada aqui — o que se garante é que o envelope carrega tudo de que ela
precisará.

## Por que um contrato, e não consumidores

Implementar consumidores agora fixaria decisões de produto que ainda não foram
tomadas (o que `/species` significa, por exemplo — `docs/decisions/pending.md`).
O que o M5 deve entregar é a SUPERFÍCIE: era, janela de ticks, correlação,
causação, causa, Engine e tipo. O M6 assina isso sem renegociar o formato.

## O planeta é dimensão de ARMAZENAMENTO, não campo do evento

O recorte por planeta NÃO é um predicado sobre o evento — é escopo da porta. Um
"erupção no tick 1200" é o mesmo fato em qualquer planeta; em QUAL planeta ele
está é onde está guardado, não o que ele é. A Spec §4 deixa planeta fora do
envelope de propósito, e esta é a consequência coerente disso (ADR 0023).

Por isso `planet_id` é parâmetro de `query`/`causal_chain`, aplicado ANTES do
predicado, e não um campo de `EventQuery`. O M5 declarava-o como campo e nunca o
aplicava — um filtro que aparenta filtrar e não filtra entregaria ao Tutor a
trilha de dois planetas parecendo recortada, e ele narraria a catástrofe do
planeta de outro aluno citando eventos reais. Ancorado no Event Store e
inteiramente errado, que é a alucinação mais difícil de detectar que este
desenho admite.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from ecosfera_ai.shared_kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class EventQuery:
    """Predicado sobre o EVENTO. Campos ausentes não restringem.

    Todo campo daqui é aplicado em `matches()` e exercitado por teste — a
    varredura que originou o ADR 0023 encontrou um campo decorativo e três
    aplicados sem cobertura, e `test_no_phantom_filters` existe para que a
    combinação não volte.

    O planeta NÃO está aqui: é escopo de armazenamento, parâmetro da porta.
    """

    era: int | None = None
    from_tick: int | None = None
    to_tick: int | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    cause_codes: frozenset[str] = field(default_factory=frozenset)
    event_types: frozenset[str] = field(default_factory=frozenset)
    engine_ids: frozenset[str] = field(default_factory=frozenset)
    # Diagnóstico técnico fica FORA por padrão: a visão científica não deve ver
    # estouro de orçamento como se fosse fenômeno do planeta (ADR-ARCH-0002).
    include_diagnostics: bool = False

    def matches(self, event: DomainEvent) -> bool:
        if not self.include_diagnostics and event.is_diagnostic:
            return False
        if self.era is not None and event.occurred_at.era != self.era:
            return False
        if self.from_tick is not None and event.occurred_at.tick < self.from_tick:
            return False
        if self.to_tick is not None and event.occurred_at.tick > self.to_tick:
            return False
        if self.correlation_id is not None and event.correlation_id != self.correlation_id:
            return False
        if self.causation_id is not None and event.causation_id != self.causation_id:
            return False
        if self.cause_codes and str(event.cause_code.value) not in self.cause_codes:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        return not self.engine_ids or event.engine_id in self.engine_ids


class EventStoreQuery(Protocol):
    """Porta de leitura. O M6 depende DESTA assinatura, não de um adaptador.

    `planet_id` vem PRIMEIRO em ambos os métodos, e não tem default: escopar o
    planeta é obrigatório, e um default silencioso reintroduziria exatamente o
    vazamento que o ADR 0023 corrige.

    ## Por que assíncrona, mesmo doendo na implementação em memória

    O M5 declarou a porta síncrona porque só existia a implementação em memória.
    O Event Store de verdade é o Postgres, e ele é async como todas as outras
    portas de persistência deste serviço.

    Uma porta síncrona forçaria uma destas saídas: o adaptador Postgres carregar
    tudo por fora e não implementar a porta (e aí não há paridade — a
    implementação de referência seria a única a implementar o contrato), ou
    bloquear o event loop numa chamada de I/O. As duas trocam um desconforto de
    teste por um defeito de produção.

    Assim as DUAS implementações satisfazem o mesmo contrato e passam os MESMOS
    testes — que é o único jeito de a implementação em memória valer como
    referência do que o adaptador faz.
    """

    async def query(self, planet_id: str, spec: EventQuery) -> Sequence[DomainEvent]: ...

    async def causal_chain(self, planet_id: str, event_id: str) -> Sequence[DomainEvent]: ...


def walk_causal_chain(events: Sequence[DomainEvent], event_id: str) -> tuple[DomainEvent, ...]:
    """Sobe a cadeia pelo `causation_id`, do efeito até a raiz.

    É a operação que o Tutor usa para responder "por que isso aconteceu?", e a
    que reconstrói `MeteorImpact → … → SpeciesExtinct`. O corte por ciclo não é
    defensivo por precaução: uma trilha corrompida por import não pode travar o
    consumidor.

    Vive como função e não como método porque as DUAS implementações da porta a
    usam sobre a trilha já escopada num planeta. Duplicá-la seria repetir o erro
    que este módulo acabou de pagar — a mesma regra escrita em dois lugares, e
    uma delas envelhecendo sozinha.
    """
    index = {event.event_id: event for event in events}
    current = index.get(event_id)
    if current is None:
        return ()

    chain: list[DomainEvent] = [current]
    seen = {current.event_id}
    while current.causation_id and current.causation_id in index:
        parent = index[current.causation_id]
        if parent.event_id in seen:
            break
        chain.append(parent)
        seen.add(parent.event_id)
        current = parent
    return tuple(chain)


@dataclass(frozen=True, slots=True)
class InMemoryEventQuery:
    """Trilhas em memória, POR PLANETA — a implementação de referência.

    O mapa por planeta não é ergonomia: é o que dá PARIDADE com o adaptador
    persistente. Uma implementação em memória que guardasse uma lista só não
    conseguiria sequer expressar o vazamento entre planetas, e o teste de
    isolamento passaria por não haver o que vazar.
    """

    trails: Mapping[str, Sequence[DomainEvent]]

    @classmethod
    def of(cls, planet_id: str, events: Sequence[DomainEvent]) -> InMemoryEventQuery:
        """Atalho para o caso de um planeta só."""
        return cls({planet_id: tuple(events)})

    async def query(self, planet_id: str, spec: EventQuery) -> Sequence[DomainEvent]:
        scoped = self.trails.get(planet_id, ())
        return tuple(event for event in scoped if spec.matches(event))

    async def causal_chain(self, planet_id: str, event_id: str) -> Sequence[DomainEvent]:
        return walk_causal_chain(self.trails.get(planet_id, ()), event_id)


# --- As projeções (ADR-ARCH-0002, "três públicos") ----------------------------


@dataclass(frozen=True, slots=True)
class ScientificProjection:
    """Visão CIENTÍFICA: o fenômeno, sem o ruído técnico.

    Para pesquisa, replay e professor avançado. Filtra o diagnóstico e ordena por
    tempo de simulação — não por ordem de chegada, que é acidente de execução.
    """

    events: Sequence[DomainEvent]

    def of(self, era: int | None = None) -> list[DomainEvent]:
        spec = EventQuery(era=era, include_diagnostics=False)
        return sorted(
            (e for e in self.events if spec.matches(e)),
            key=lambda e: (e.occurred_at.era, e.occurred_at.tick, e.event_id),
        )

    def by_cause(self) -> dict[str, int]:
        """Quantas vezes cada mecanismo ocorreu — o mapa que a pesquisa quer."""
        counts: dict[str, int] = {}
        for event in self.of():
            key = str(event.cause_code.value)
            counts[key] = counts.get(key, 0) + 1
        return counts


@dataclass(frozen=True, slots=True)
class TechnicalProjection:
    """Visão TÉCNICA: só o diagnóstico — orçamento estourado, invariante violada.

    O inverso exato da científica. Um operador quer ver o que o motor reclamou;
    misturar isso ao fenômeno faria o pesquisador tratar um estouro de orçamento
    como evento do planeta.
    """

    events: Sequence[DomainEvent]

    def diagnostics(self) -> list[DomainEvent]:
        return [event for event in self.events if event.is_diagnostic]

    def by_engine(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.diagnostics():
            engine = str(event.cause_detail.get("engine", event.engine_id))
            counts[engine] = counts.get(engine, 0) + 1
        return counts


def educational_payload_is_complete(events: Iterable[DomainEvent]) -> bool:
    """A visão EDUCACIONAL é do M6 — aqui só se confere que nada lhe falta.

    Ela precisará, de cada evento: o mecanismo (`cause_code`), o elo causal
    (`causation_id`), o instante (`occurred_at`) e os números que sustentam a
    frase (`cause_detail`). Se algum evento não os traz, o M6 descobriria tarde.
    """
    for event in events:
        if event.is_diagnostic:
            continue
        if not event.cause_code or not event.correlation_id:
            return False
        if not event.cause_detail and not event.participants:
            return False
    return True
