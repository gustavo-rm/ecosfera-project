"""O tutor embrionário explica a partir do Event Store — sem LLM (ADR 0011).

Verifica a fronteira do ADR-ARCH-0001: o consumidor lê a trilha de eventos, não o
world-state nem a memória de nenhum Engine. A prosa continua saindo do motor de
regras determinístico; o Engine só forneceu o esqueleto causal como dado.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.application.feedback.explain_from_events import (
    ExplainFromEventsUseCase,
    load_translation,
)
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.legacy.bridge import snapshot_of
from ecosfera_ai.engines.legacy.orchestrator import build_planet_engine
from ecosfera_ai.shared_kernel.events import CoreCauseCode, EventEmitter
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TRANSLATION = load_translation(Path("configs/event_observations.yaml"))
TICKS = 80


def _use_case() -> ExplainFromEventsUseCase:
    rules = ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml")))
    return ExplainFromEventsUseCase(rules, TRANSLATION)


def _store(seed: int = 2027) -> InMemoryEventStore:
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("tutor", seed), PARAMS))
    for _ in range(TICKS):
        snapshot = planet.tick(snapshot).snapshot
    return store


def test_the_explanation_comes_from_rules_and_is_grounded() -> None:
    outcome = _use_case().execute("tutor", _store().scientific_view())

    assert outcome.explanation.source == "rules", "LLM só no M6"
    assert outcome.explanation.grounded is True
    assert outcome.explanation.chain


def test_the_narrated_chain_covers_the_vertical_slice() -> None:
    """As regras de sempre narram a cadeia que os Engines novos produziram."""
    outcome = _use_case().execute("tutor", _store().scientific_view())
    fired = {step.rule_id for step in outcome.explanation.chain}

    assert "R-VOLC-CO2" in fired, "a erupção deveria explicar o carbono"
    assert "R-CO2-TEMP" in fired, "o carbono deveria explicar a temperatura"


def test_the_trace_accompanies_the_explanation() -> None:
    outcome = _use_case().execute("tutor", _store().scientific_view())
    assert outcome.trace, "a explicação precisa vir com o rastro que a sustenta"


def test_diagnostic_events_never_reach_the_student() -> None:
    """A visão técnica é do desenvolvedor; o tutor lê só a científica."""
    emitter = EventEmitter(engine_id="planet", seed=1, tick=1, era=0)
    from ecosfera_ai.shared_kernel.events import diagnostic_event

    noise = diagnostic_event(emitter, CoreCauseCode.BUDGET_EXCEEDED, {"limit": "duration_s"})
    assert TRANSLATION.observations([noise]) == []


def test_unknown_event_types_are_skipped_not_fatal() -> None:
    """O Event Store cresce com Engines novos; o tutor não pode quebrar por isso."""
    emitter = EventEmitter(engine_id="futuro", seed=1, tick=1, era=0)
    unknown = emitter.emit("AlgoQueAindaNaoExiste", CoreCauseCode.ENGINE_HEARTBEAT)
    assert TRANSLATION.observations([unknown]) == []


def test_the_translation_is_versioned_data() -> None:
    assert TRANSLATION.version >= 1
    assert "VolcanicEruption" in TRANSLATION.mappings


def test_the_consumer_does_not_import_any_engine() -> None:
    """ADR-ARCH-0001: consumidores só dependem do Event Store, não dos Engines."""
    import ast

    source = Path("src/ecosfera_ai/application/feedback/explain_from_events.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not {m for m in modules if m.startswith("ecosfera_ai.engines")}


def test_the_explanation_is_reproducible() -> None:
    first = _use_case().execute("tutor", _store(seed=99).scientific_view())
    second = _use_case().execute("tutor", _store(seed=99).scientific_view())
    assert [s.rule_id for s in first.explanation.chain] == [
        s.rule_id for s in second.explanation.chain
    ]
