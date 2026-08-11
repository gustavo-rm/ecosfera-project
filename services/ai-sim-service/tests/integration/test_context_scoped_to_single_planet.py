"""O dossiê contém o planeta PEDIDO e nenhum outro — dois planetas, mesma semente.

Adversarial, e não caso feliz. Dois alunos com a mesma semente não é laboratório:
é uma turma a que se disse *"usem a semente 2027"*. E com a mesma semente os
identificadores COLIDEM byte a byte — `event_id` sai de
`uuid5(semente, era, tick, engine, tipo, sequência)` e não inclui planeta
(ADR 0023).

Contar não bastaria: com os ids colidindo, uma trilha vazada tem o mesmo tamanho
e os mesmos identificadores da certa. A marca `owner` em `cause_detail` — que não
entra na derivação do id — é o que permite afirmar que o dossiê trouxe o evento
do planeta CERTO, e não apenas a quantidade certa.

Por que este teste existe aqui, e não só no M5. O vazamento do M5 era um filtro
que não filtrava; o do M6.0 seria um consumidor que esquece de escopar. O
resultado seria o mesmo e é o pior defeito que esta plataforma admite: o Tutor
narra ao aluno, com total confiança e citando eventos REAIS, a catástrofe do
planeta de OUTRO aluno. Toda afirmação seria derivável de um event log. Só não do
dele — e nenhuma avaliação adversarial do M6.4 pegaria isso, porque a resposta
estaria ancorada. Apenas na trilha errada.
"""

from __future__ import annotations

from tests.support_events import OWNER, SHARED_SEED, cascade

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.factual_context import ContextSlice

ALICE, BOB = "planet-alice", "planet-bob"
ALICE_TRAIL = cascade(owner="alice")
BOB_TRAIL = cascade(owner="bob")


def _assembler() -> ContextAssembler:
    return ContextAssembler(InMemoryEventQuery({ALICE: ALICE_TRAIL, BOB: BOB_TRAIL}))


def _owners(context: object) -> set[str]:
    return {str(e.cause_detail.get(OWNER)) for e in context.events}  # type: ignore[attr-defined]


def test_the_scenario_is_adversarial_the_ids_really_do_collide() -> None:
    """Sem esta premissa o teste seria fácil demais para provar o que promete."""
    assert [e.event_id for e in ALICE_TRAIL] == [e.event_id for e in BOB_TRAIL]
    assert all(e.seed == SHARED_SEED for e in ALICE_TRAIL)


async def test_the_era_slice_carries_only_the_requested_planet() -> None:
    context = await _assembler().execute(ALICE, ContextSlice.of_era(1))
    assert _owners(context) == {"alice"}


async def test_the_tick_slice_carries_only_the_requested_planet() -> None:
    context = await _assembler().execute(BOB, ContextSlice.of_ticks(100, 102))
    assert _owners(context) == {"bob"}


async def test_the_event_slice_ascends_inside_the_requested_planet() -> None:
    """A subida é onde o vazamento seria mais discreto.

    `event_id` só é único POR PLANETA, então uma subida sem escopo poderia sair
    da corrida do aluno no meio do caminho e devolver a causa de outro planeta —
    uma cadeia meio dele, meio de estranho, e verossímil dos dois lados.
    """
    extinction = ALICE_TRAIL[-1]
    context = await _assembler().execute(ALICE, ContextSlice.of_event(extinction.event_id))
    assert len(context.ancestry) == 3
    assert _owners(context) == {"alice"}


async def test_the_same_slice_of_two_planets_yields_two_different_dossiers() -> None:
    """Mesmos ids, mesmos tipos, mesmos ticks — e dossiês distintos."""
    alice = await _assembler().execute(ALICE, ContextSlice.of_era(1))
    bob = await _assembler().execute(BOB, ContextSlice.of_era(1))
    assert [e.event_id for e in alice.events] == [e.event_id for e in bob.events]
    assert alice.to_dict() != bob.to_dict()
    assert _owners(alice).isdisjoint(_owners(bob))


async def test_a_planet_with_no_trail_returns_empty_and_never_everything() -> None:
    context = await _assembler().execute("planet-carol", ContextSlice.of_era(1))
    assert context.is_empty


async def test_the_planet_id_is_never_a_predicate_over_the_event() -> None:
    """Planeta é escopo de ARMAZENAMENTO, não campo do evento (ADR 0023, Spec §4).

    O dossiê o guarda como metadado da consulta. Se ele virasse propriedade do
    fato, o mesmo "meteoro no tick 100" passaria a ser dois fatos diferentes.
    """
    context = await _assembler().execute(ALICE, ContextSlice.of_era(1))
    assert context.planet_id == ALICE
    for payload in context.to_dict()["events"]:
        assert "planet_id" not in payload
