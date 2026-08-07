"""Todo campo declarado da query é APLICADO e é TESTADO.

A varredura que originou o ADR 0023 encontrou, na superfície do contrato do M5:

  - `planet_id` declarado e nunca aplicado (o fantasma);
  - `era`, `causation_id` e `event_types` aplicados e nunca exercitados;
  - dois testes cujos nomes prometiam cobertura que não davam
    (`by_era_and_tick` não passava era; `by_engine_and_event_type` não passava
    tipo).

Um campo decorativo é pior que a ausência dele: quem chama confia, e o efeito é
silencioso. Este arquivo transforma a varredura em barreira — se alguém somar um
campo a `EventQuery` sem aplicá-lo, ou aplicá-lo sem testá-lo, quebra aqui.
"""

from __future__ import annotations

import dataclasses
import inspect
from dataclasses import replace

from tests.support_events import cascade

from ecosfera_ai.application.platform.event_query import EventQuery
from ecosfera_ai.shared_kernel.events import DomainEvent

# Um valor que NÃO casa com a trilha de referência, por campo. Somar um campo a
# `EventQuery` sem somá-lo aqui quebra `test_every_declared_field_is_applied`.
NON_MATCHING: dict[str, object] = {
    "era": 999,
    "from_tick": 10_000,
    "to_tick": -1,
    "correlation_id": "correlacao-inexistente",
    "causation_id": "causacao-inexistente",
    "cause_codes": frozenset({"CAUSA_QUE_NAO_EXISTE"}),
    "event_types": frozenset({"TipoQueNaoExiste"}),
    "engine_ids": frozenset({"engine-que-nao-existe"}),
}


def _trail() -> list[DomainEvent]:
    return cascade(owner="varredura")


def test_the_reference_trail_matches_an_empty_query() -> None:
    """Base da varredura: sem restrição, tudo casa."""
    events = _trail()
    assert all(EventQuery().matches(e) for e in events)


def test_every_declared_field_is_applied() -> None:
    """Cada campo, sozinho, tem de conseguir EXCLUIR um evento que casaria.

    É o teste que o `planet_id` fantasma não passava: ele era declarado, e
    nenhum valor dele mudava o resultado de `matches()`.
    """
    events = _trail()
    declared = {f.name for f in dataclasses.fields(EventQuery)}
    covered = set(NON_MATCHING) | {"include_diagnostics"}

    assert declared == covered, (
        f"campo(s) sem cobertura na varredura: {declared ^ covered}. "
        "Todo campo novo de EventQuery precisa de um valor que NÃO case aqui."
    )

    for field_name, value in NON_MATCHING.items():
        spec = replace(EventQuery(), **{field_name: value})
        assert not any(spec.matches(e) for e in events), (
            f"{field_name!r} é decorativo: com um valor impossível, ainda casou. "
            "É o defeito do planet_id do M5 de volta."
        )


def test_every_declared_field_also_accepts_a_matching_value() -> None:
    """O complemento: o campo não pode ser um "nunca casa" disfarçado.

    Sem isto, um campo quebrado que rejeitasse TUDO passaria no teste acima.
    """
    events = _trail()
    first = events[0]
    matching: dict[str, object] = {
        "era": first.occurred_at.era,
        "from_tick": first.occurred_at.tick,
        "to_tick": first.occurred_at.tick,
        "correlation_id": first.correlation_id,
        "cause_codes": frozenset({str(first.cause_code.value)}),
        "event_types": frozenset({first.event_type}),
        "engine_ids": frozenset({first.engine_id}),
    }
    for field_name, value in matching.items():
        spec = replace(EventQuery(), **{field_name: value})
        assert spec.matches(first), f"{field_name!r} rejeitou o próprio valor do evento"

    # `causation_id` casa com o elo, não com a raiz.
    linked = next(e for e in events if e.causation_id)
    assert EventQuery(causation_id=linked.causation_id).matches(linked)


def test_include_diagnostics_is_exercised_in_both_directions() -> None:
    """O M5 só exercitava o default. `True` nunca fora testado."""
    from ecosfera_ai.shared_kernel.events import CoreCauseCode, EventEmitter, diagnostic_event

    emitter = EventEmitter(engine_id="planet", seed=1, tick=1, era=0)
    noise = diagnostic_event(emitter, CoreCauseCode.BUDGET_EXCEEDED, {"engine": "climate"})

    assert not EventQuery().matches(noise), "o diagnóstico entrou na visão científica"
    assert EventQuery(include_diagnostics=True).matches(noise), (
        "com a flag ligada o diagnóstico continuou fora — a visão técnica não enxerga nada"
    )


def test_planet_is_not_a_field_of_the_event_predicate() -> None:
    """A correção estrutural: planeta é escopo da porta, não predicado (ADR 0023)."""
    declared = {f.name for f in dataclasses.fields(EventQuery)}
    assert "planet_id" not in declared, (
        "planet_id voltou a ser campo de EventQuery — o envelope §4 não carrega "
        "planeta, então ele não teria por onde filtrar e voltaria a ser decorativo"
    )


def test_the_port_requires_a_planet_on_every_read() -> None:
    """E o escopo é obrigatório: sem default que degrade para "todos"."""
    from ecosfera_ai.application.platform.event_query import EventStoreQuery

    for method in ("query", "causal_chain"):
        signature = inspect.signature(getattr(EventStoreQuery, method))
        first = list(signature.parameters.values())[1]
        assert first.name == "planet_id", f"{method} não escopa planeta em primeiro lugar"
        assert first.default is inspect.Parameter.empty, (
            f"{method} tem default para planet_id — um esquecimento devolveria "
            "a base inteira, que é como o defeito do M5 se comportava"
        )
