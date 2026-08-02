"""Orçamento por tick nos Engines do M1 (Spec §6, ADR-ARCH-0002).

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
