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


def test_the_era_is_narrated_from_the_event_trail_on_the_production_path() -> None:
    """Item F do M1: o caminho de PRODUÇÃO narra a partir do Canal B.

    Não basta a capacidade existir — `advance-era` tem de usá-la. `narrated_from`
    é dado da resposta, e não inferência sobre o conteúdo da explicação:
    auditabilidade por adivinhação não é auditabilidade.
    """
    from fastapi.testclient import TestClient

    from ecosfera_ai.application.simulation.advance_era import (
        NARRATED_FROM_EVENTS,
        NARRATED_FROM_STATE_DELTA,
    )
    from ecosfera_ai.main import app

    base = "/ai/api/v1/simulation"
    with TestClient(app) as client:
        planet_id = client.post(f"{base}/planets", json={"seed": 2027}).json()["planet_id"]
        sources = [
            client.post(f"{base}/planets/{planet_id}/advance-era").json()["narrated_from"]
            for _ in range(8)
        ]

    assert NARRATED_FROM_EVENTS in sources, "nenhuma era foi narrada pela trilha"
    assert set(sources) <= {NARRATED_FROM_EVENTS, NARRATED_FROM_STATE_DELTA}


def test_an_era_without_notable_events_falls_back_instead_of_going_silent() -> None:
    """O recuo é decisão de produto, não descuido (ADR 0011).

    O Canal B registra travessia de patamar, não o contínuo — uma era pode passar
    sem nenhuma ocorrência notável. Devolver explicação vazia nesses casos seria
    regressão pedagógica. O delta agregado é estado PUBLICADO, não memória
    interna de Engine, então o recuo não viola a fronteira.
    """
    import asyncio

    from ecosfera_ai.application.simulation.advance_era import (
        NARRATED_FROM_STATE_DELTA,
        AdvanceEraUseCase,
    )
    from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
    from ecosfera_ai.infrastructure.persistence.inmemory_planet_repo import (
        InMemoryPlanetRepository,
    )
    from ecosfera_ai.simulation_engine.state import PlanetSeed

    async def run() -> None:
        repo = InMemoryPlanetRepository()
        await CreatePlanetUseCase(repo, PARAMS).execute(PlanetSeed("mudo", 2027))
        rules = ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml")))
        # SEM explicador de eventos: e o caso de uso continua explicando.
        use_case = AdvanceEraUseCase(
            repo, _framework_ticker(), rules, PARAMS.timeline.era_length, explain_events=None
        )
        outcome = await use_case.execute("mudo")

        assert outcome.narrated_from == NARRATED_FROM_STATE_DELTA
        assert outcome.explanation.chain, "a era nunca pode ficar sem explicação"
        assert outcome.causal_trace == ()

    asyncio.run(run())


def _framework_ticker():
    from ecosfera_ai.engines.legacy.orchestrator import FrameworkTickOrchestrator

    return FrameworkTickOrchestrator(
        build_planet_engine(PARAMS, budget=PARAMS.engine_budget), PARAMS.bounds
    )
