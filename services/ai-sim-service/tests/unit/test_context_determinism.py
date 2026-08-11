"""Mesma trilha, mesmo dossiê — sempre, e independente da ordem de chegada.

O M6 troca os testes de invariante física por avaliação adversarial (M6.4), e
essa troca só funciona se a ENTRADA do avaliador for estável. Um dossiê que varia
entre execuções faria toda diferença de saída do Tutor virar ruído inconclusivo:
ninguém saberia se mudou o prompt, o modelo ou a matéria-prima.

A ameaça concreta é a ordem de chegada. A trilha chega do Event Store ordenada
por tempo de simulação, mas um import, uma paginação ou um `set` no meio do
caminho podem embaralhá-la. Ordenar por (era, tick, id) — e nunca por ordem de
inserção — é o que torna o dossiê função apenas do CONTEÚDO da trilha.
"""

from __future__ import annotations

import json

from tests.support_context import branching_cascade, life_emerged

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext

TRAIL = (life_emerged(era=1, tick=99), *branching_cascade())
SLICE = ContextSlice.of_era(1)


def _dossier(events: tuple[object, ...]) -> str:
    context = FactualContext.of("planet-det", SLICE, events)  # type: ignore[arg-type]
    return json.dumps(context.to_dict(), sort_keys=True, ensure_ascii=False)


def test_the_same_trail_produces_the_same_dossier() -> None:
    assert _dossier(TRAIL) == _dossier(TRAIL)


def test_the_dossier_does_not_depend_on_the_arrival_order() -> None:
    """Reordenar a entrada não pode mudar uma vírgula da saída."""
    assert _dossier(TRAIL) == _dossier(tuple(reversed(TRAIL)))


def test_two_dossiers_of_the_same_trail_compare_equal() -> None:
    """Igualdade estrutural, e não só igualdade de JSON."""
    first = FactualContext.of("planet-det", SLICE, TRAIL)
    second = FactualContext.of("planet-det", SLICE, tuple(reversed(TRAIL)))
    assert first == second


def test_the_timeline_is_ordered_by_simulation_time() -> None:
    context = FactualContext.of("planet-det", SLICE, tuple(reversed(TRAIL)))
    keys = [(e.occurred_at.era, e.occurred_at.tick, e.event_id) for e in context.events]
    assert keys == sorted(keys)


def test_sibling_consequences_keep_a_stable_order() -> None:
    """Os irmãos de um mesmo nó saem sempre na mesma ordem.

    Sem isto o JSON do dossiê mudaria a cada corrida por permutação de ramos —
    diferença sem significado que apagaria as diferenças que têm.
    """
    forward = FactualContext.of("planet-det", SLICE, TRAIL).causal_roots
    backward = FactualContext.of("planet-det", SLICE, tuple(reversed(TRAIL))).causal_roots
    assert [n.to_dict() for n in forward] == [n.to_dict() for n in backward]


def test_the_markers_are_stable_too() -> None:
    first = FactualContext.of("planet-det", SLICE, TRAIL).markers
    second = FactualContext.of("planet-det", SLICE, tuple(reversed(TRAIL))).markers
    assert first == second
