"""Os três recortes devolvem o conjunto CERTO de eventos — nem mais, nem menos.

Um recorte que devolve demais é o defeito do ADR 0023 outra vez, em outra
dimensão: o Tutor narra a era 2 citando um evento da era 3, e a afirmação é
derivável do event log — só não daquela fatia. Um recorte que devolve de menos é
mais discreto e igualmente ruim: o Tutor omite o que aconteceu e o aluno preenche
o silêncio com a intuição espontânea.

Por isso cada recorte é afirmado pelo CONJUNTO exato de identificadores, e não
por contagem — como o teste de isolamento de planeta já ensinou, contar não basta.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade, life_emerged, spans_two_eras

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, SliceKind
from ecosfera_ai.shared_kernel.events import DomainEvent

PLANET = "planet-slices"

CASCADE = branching_cascade()  # era 1, ticks 100..103
METEOR, COOLING, WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE
EARLY = life_emerged(era=0, tick=10)
LATER = spans_two_eras()  # era 1 (tick 90) -> era 2 (tick 120)

TRAIL: list[DomainEvent] = [EARLY, *LATER, *CASCADE]


def _assembler() -> ContextAssembler:
    return ContextAssembler(InMemoryEventQuery.of(PLANET, TRAIL))


# --- Recorte por ERA ----------------------------------------------------------


async def test_the_era_slice_returns_exactly_that_era() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_era(1))
    assert {e.event_id for e in context.events} == {LATER[0].event_id} | {
        e.event_id for e in CASCADE
    }


async def test_the_era_slice_excludes_the_neighbouring_eras() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_era(1))
    ids = {e.event_id for e in context.events}
    assert EARLY.event_id not in ids
    assert LATER[1].event_id not in ids


# --- Recorte por JANELA DE TICKS ---------------------------------------------


async def test_the_tick_window_is_inclusive_on_both_ends() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_ticks(100, 102))
    assert {e.event_id for e in context.events} == {
        METEOR.event_id,
        COOLING.event_id,
        WILDFIRE.event_id,
        CATASTROPHIC.event_id,
    }


async def test_the_tick_window_ignores_the_era_and_cuts_only_by_tick() -> None:
    """Recorte por tick é recorte por tick: eras diferentes entram se couberem.

    É o comportamento do contrato de query do M5 (`from_tick`/`to_tick` sem
    `era`), e este recorte apenas o consome — reinterpretá-lo aqui criaria duas
    definições de janela.
    """
    context = await _assembler().execute(PLANET, ContextSlice.of_ticks(90, 120))
    assert {LATER[0].event_id, LATER[1].event_id} <= {e.event_id for e in context.events}


# --- Recorte por EVENTO -------------------------------------------------------


async def test_the_event_slice_is_the_event_plus_both_directions() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_event(COOLING.event_id))
    assert {e.event_id for e in context.events} == {
        METEOR.event_id,  # subindo
        COOLING.event_id,  # o foco
        ECOLOGICAL.event_id,  # descendo
    }


async def test_the_event_slice_leaves_out_the_siblings_it_did_not_cause() -> None:
    """O incêndio partilha a causa com o resfriamento — e não decorre dele.

    Trazê-lo seria confundir "mesma origem" com "mesma cadeia", e o Tutor
    apresentaria como consequência algo que apenas partilhou o gatilho.
    """
    context = await _assembler().execute(PLANET, ContextSlice.of_event(COOLING.event_id))
    assert WILDFIRE.event_id not in {e.event_id for e in context.events}


async def test_the_event_slice_of_a_root_carries_the_whole_cascade() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_event(METEOR.event_id))
    assert {e.event_id for e in context.events} == {e.event_id for e in CASCADE}
    assert [e.event_id for e in context.ancestry] == [METEOR.event_id]


# --- A forma do recorte é validada na construção ------------------------------


def test_a_slice_without_the_fields_that_define_it_is_refused() -> None:
    """Um recorte incompleto não pode virar consulta silenciosamente ampla."""
    with pytest.raises(ValueError, match="recorte"):
        ContextSlice(kind=SliceKind.ERA)
    with pytest.raises(ValueError, match="recorte"):
        ContextSlice(kind=SliceKind.EVENT)
    with pytest.raises(ValueError, match="recorte"):
        ContextSlice(kind=SliceKind.TICKS, from_tick=10)


def test_the_slice_travels_inside_the_dossier() -> None:
    """Quem receber o dossiê sabe de que fatia ele fala (auditabilidade)."""
    assert ContextSlice.of_era(3).to_dict() == {
        "kind": "era",
        "era": 3,
        "from_tick": None,
        "to_tick": None,
        "event_id": None,
    }
