"""`event_id` NÃO é único entre planetas — o fato que motiva a migration 0005.

Roda sem Docker, de propósito: é uma propriedade da derivação de identificador,
não da persistência, e é a premissa de que dependem o índice composto
`(planet_id, event_id)` e todo o teste de isolamento. Deixá-la atrás do guard de
Postgres significaria que a justificativa da correção só é verificada onde há
Docker.

O M4 fixou `event_id = uuid5(semente, era, tick, engine, tipo, sequência)` para
que o replay seja bit-a-bit (RF-023), e a Spec §4 mantém planeta fora do
envelope. As duas decisões são certas e, juntas, implicam esta consequência: dois
planetas de mesma semente produzem identificadores idênticos.
"""

from __future__ import annotations

from tests.support_events import SHARED_SEED, cascade

from ecosfera_ai.shared_kernel.events import correlation_id_for, deterministic_id


def test_two_planets_with_the_same_seed_produce_identical_event_ids() -> None:
    """O cenário de uma turma a que se disse "usem a semente 2027"."""
    ana = cascade(seed=SHARED_SEED, owner="ana")
    bruno = cascade(seed=SHARED_SEED, owner="bruno")

    assert [e.event_id for e in ana] == [e.event_id for e in bruno], (
        "os ids deixaram de colidir — se a derivação passou a incluir o planeta, "
        "a chave composta da migration 0005 virou redundante e o ADR 0023 precisa "
        "ser revisitado"
    )
    assert [e.correlation_id for e in ana] == [e.correlation_id for e in bruno]


def test_the_content_differs_where_the_identifier_does_not() -> None:
    """É o que torna o teste de isolamento capaz de DETECTAR o vazamento.

    A derivação não usa `cause_detail`, então dois eventos podem ter o mesmo id e
    conteúdos distintos. Sem essa folga, duas trilhas idênticas tornariam o
    vazamento indistinguível do acerto — contar não provaria nada.
    """
    ana = cascade(seed=SHARED_SEED, owner="ana")
    bruno = cascade(seed=SHARED_SEED, owner="bruno")

    for one, other in zip(ana, bruno, strict=True):
        assert one.event_id == other.event_id
        assert one.cause_detail["owner"] != other.cause_detail["owner"]


def test_the_derivation_takes_no_planet_at_all() -> None:
    """Direto na fonte: nem o id nem a correlação recebem planeta."""
    assert deterministic_id(2027, 1, 100, "evolution", "SpeciesExtinct", 1) == deterministic_id(
        2027, 1, 100, "evolution", "SpeciesExtinct", 1
    )
    assert correlation_id_for(2027, 1, 100) == correlation_id_for(2027, 1, 100)


def test_different_seeds_do_separate_the_trails() -> None:
    """Contraprova: a semente separa; o que ela não faz é IDENTIFICAR planeta."""
    assert [e.event_id for e in cascade(seed=1)] != [e.event_id for e in cascade(seed=2)]
