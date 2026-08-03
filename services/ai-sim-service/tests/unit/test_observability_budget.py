"""Orçamento por tick nos Engines (Spec §6, ADR-ARCH-0002).

Estourar o teto emite `DiagnosticEvent` e **não altera um bit** do resultado.
Reagir ao tempo de execução faria a trajetória depender da carga da máquina, e o
replay bit-a-bit morreria junto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.engines.atmosphere.contracts import load_params as atmosphere_params
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.climate.contracts import load_params as climate_params
from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
from ecosfera_ai.engines.event.contracts import load_params as event_params
from ecosfera_ai.engines.geology.contracts import load_params as geology_params
from ecosfera_ai.shared_kernel.engine import TickBudget
from ecosfera_ai.shared_kernel.events import CoreCauseCode
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _snapshot():
    return snapshot_of(initial_state(PlanetSeed("budget", 2027), PARAMS))


@pytest.mark.parametrize(
    ("name", "loader"),
    [
        ("geology", geology_params),
        ("atmosphere", atmosphere_params),
        ("climate", climate_params),
        # O Event Engine entra aqui no M4: é o Engine em que a tentação de
        # realimentar a simulação com medição é maior, e o orçamento é a
        # fronteira que garante que estourar o teto vira DIAGNÓSTICO — não
        # decisão do Diretor.
        ("event", event_params),
    ],
)
def test_every_engine_declares_its_budget_as_versioned_data(name: str, loader) -> None:
    params = loader()
    assert params.max_duration_s > 0.0, f"{name} sem teto de tempo"
    assert params.max_events > 0, f"{name} sem teto de eventos"


def test_exceeding_the_budget_does_not_move_a_single_number() -> None:
    generous = build_planet_engine(PARAMS, budget=TickBudget()).tick(_snapshot())
    impossible = build_planet_engine(PARAMS, budget=TickBudget(max_duration_s=-1.0)).tick(
        _snapshot()
    )

    assert impossible.snapshot == generous.snapshot


def test_exceeding_the_budget_emits_one_diagnostic_per_engine() -> None:
    outcome = build_planet_engine(PARAMS, budget=TickBudget(max_duration_s=-1.0)).tick(_snapshot())
    diagnostics = [event for event in outcome.events if event.is_diagnostic]

    assert len(diagnostics) == len(outcome.samples)
    assert all(e.cause_code is CoreCauseCode.BUDGET_EXCEEDED for e in diagnostics)
    assert {str(e.cause_detail["engine"]) for e in diagnostics} == set(ENGINE_ORDER)


def test_the_diagnostic_never_reaches_the_scientific_view() -> None:
    store = InMemoryEventStore()
    build_planet_engine(PARAMS, budget=TickBudget(max_duration_s=-1.0), sink=store).tick(
        _snapshot()
    )

    assert store.technical_view(), "o diagnóstico tem de existir para o desenvolvedor"
    assert all(not e.is_diagnostic for e in store.scientific_view())


def test_metrics_are_collected_for_every_engine() -> None:
    outcome = build_planet_engine(PARAMS, budget=PARAMS.engine_budget).tick(_snapshot())
    assert {s.engine_id for s in outcome.samples} == set(ENGINE_ORDER)
    assert all(s.entities_processed >= 1 for s in outcome.samples)


def test_no_engine_reads_metrics_or_logs() -> None:
    """Pureza: nenhum Engine do M1 importa o módulo de observabilidade."""
    import ast

    root = Path("src/ecosfera_ai/engines")
    for package in ("geology", "atmosphere", "climate"):
        for path in (root / package).rglob("*.py"):
            if path.name == "observability.py":
                continue  # é o sink do Engine, chamado DEPOIS do tick
            tree = ast.parse(path.read_text(encoding="utf-8"))
            modules = {
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            assert "ecosfera_ai.core.observability" not in modules
            assert "ecosfera_ai.shared_kernel.observability" not in modules


# --- O Event Engine sob orçamento (M4) ----------------------------------------


def _director_planet(budget: TickBudget, store: InMemoryEventStore):
    """Planeta com o Diretor ATIVO — sem evento, o teste não afirmaria nada."""
    return build_planet_engine(PARAMS, budget=budget, sink=store)


def test_the_event_engine_result_is_identical_under_an_impossible_budget() -> None:
    """O Diretor NÃO reage ao orçamento: estourá-lo não muda o que ele decide.

    É a afirmação central do §6 aplicada ao Engine mais perigoso do marco. Se o
    Diretor agendasse menos eventos por estar "atrasado", a trajetória passaria a
    depender da carga da máquina, e o replay bit-a-bit morreria junto.
    """
    generous = _director_planet(TickBudget(), InMemoryEventStore())
    starved = _director_planet(TickBudget(max_duration_s=-1.0), InMemoryEventStore())

    a, b = _snapshot(), _snapshot()
    for _ in range(200):
        a = generous.tick(a).snapshot
        b = starved.tick(b).snapshot

    assert a.event == b.event, "o orçamento alterou as decisões do Diretor"
    assert a == b, "o orçamento alterou o tick"


def test_exceeding_the_budget_emits_a_diagnostic_for_the_event_engine() -> None:
    store = InMemoryEventStore()
    planet = _director_planet(TickBudget(max_duration_s=-1.0), store)
    planet.tick(_snapshot())

    # O Engine responsável vem no `cause_detail`, que é onde o diagnóstico
    # técnico carrega estrutura — `participants` é vocabulário do domínio.
    diagnostics = [
        e for e in store.events if e.is_diagnostic and e.cause_detail.get("engine") == "event"
    ]
    assert diagnostics, "o Event Engine estourou o teto sem emitir diagnóstico"
    assert all(isinstance(e.cause_code, CoreCauseCode) for e in diagnostics)


def test_the_event_engine_declares_its_budget_in_versioned_data() -> None:
    params = event_params()
    assert params.max_duration_s > 0.0
    assert params.max_events > 0
