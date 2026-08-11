"""Fatia vazia devolve dossiê VAZIO e explícito — nunca erro, nunca ausência muda.

O caso é comum e ESPERADO, não excepcional. A especiação é o exemplo medido: o
`speciation_threshold` vale 0,12 e um passo de mutação anda ~0,02, então cruzar o
limiar num tick exige ~6 σ. Uma corrida de 200 ticks emite 39 eventos na semente
2027 e 76 na 99 — **nenhum** de especiação (`docs/decisions/deferred.md`). Até a
Fase 2, uma era inteira sem especiação alguma é o comportamento NORMAL do modelo.

Um consumidor que tratasse a ausência como falha faria duas coisas erradas ao
mesmo tempo: transformaria o caso comum em exceção, e mandaria quem for avaliar o
Tutor caçar um defeito de prompt ou de RAG que não existe.

E "vazio explícito" não é o mesmo que "vazio". O dossiê vazio ainda diz de qual
planeta e de qual fatia ele fala — é o que distingue *"nada aconteceu na era 4"*
de *"ninguém perguntou pela era 4"*.
"""

from __future__ import annotations

from tests.support_context import branching_cascade

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext

PLANET = "planet-quiet"
CASCADE = branching_cascade()  # era 1


def _assembler() -> ContextAssembler:
    return ContextAssembler(InMemoryEventQuery.of(PLANET, CASCADE))


async def test_an_era_with_no_events_returns_an_empty_dossier() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_era(9))
    assert context.is_empty
    assert context.events == ()
    assert context.causal_roots == ()


async def test_a_tick_window_with_no_events_returns_an_empty_dossier() -> None:
    context = await _assembler().execute(PLANET, ContextSlice.of_ticks(5000, 5100))
    assert context.is_empty


async def test_an_unknown_event_returns_an_empty_dossier_and_not_an_error() -> None:
    """Um id que não existe naquele planeta devolve vazio, jamais "tudo"."""
    context = await _assembler().execute(PLANET, ContextSlice.of_event("evt-inexistente"))
    assert context.is_empty
    assert context.ancestry == ()


async def test_an_era_without_speciation_is_normal_and_not_an_error() -> None:
    """O caso comum do modelo atual: eventos acontecem, especiação não.

    Este é o cenário que o Tutor vai encontrar quase sempre até a Fase 2.
    """
    context = await _assembler().execute(PLANET, ContextSlice.of_era(1))
    assert not context.is_empty
    assert context.speciations == ()
    assert context.extinctions, "a era tem extinções — o vazio é só o da especiação"


async def test_the_empty_dossier_still_says_which_planet_and_which_slice() -> None:
    """Vazio EXPLÍCITO: sabe-se que se perguntou, e que a resposta foi nada."""
    requested = ContextSlice.of_era(9)
    context = await _assembler().execute(PLANET, requested)
    payload = context.to_dict()
    assert payload["planet_id"] == PLANET
    assert payload["slice"] == requested.to_dict()
    assert payload["is_empty"] is True


async def test_an_empty_planet_returns_empty_instead_of_everything() -> None:
    """A pergunta sobre um planeta sem trilha não pode cair no planeta de outro."""
    context = await _assembler().execute("planet-que-nao-existe", ContextSlice.of_era(1))
    assert context.is_empty


def test_the_empty_dossier_is_navigable_without_special_cases() -> None:
    """Quem consumir não precisa de um ramo `if vazio` para não quebrar."""
    context = FactualContext.empty(PLANET, ContextSlice.of_era(9))
    assert context.consequences_of("qualquer") == ()
    assert context.cause_of("qualquer") is None
    assert context.event("qualquer") is None
    assert context.markers == ()
