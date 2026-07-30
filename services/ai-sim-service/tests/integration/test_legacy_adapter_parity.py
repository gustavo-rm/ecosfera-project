"""Paridade determinística: o núcleo atual atravessa a moldura sem mudar um bit.

É o critério que separa o M0 de uma reescrita: a moldura tem de ser transparente
para a física já validada. Qualquer divergência aqui é regressão, não refinamento.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.engines.legacy.adapter import LegacySubsystemAdapter
from ecosfera_ai.engines.legacy.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.legacy.orchestrator import (
    FrameworkTickOrchestrator,
    build_planet_engine,
    legacy_invariants,
)
from ecosfera_ai.shared_kernel.world_state import SliceRef
from ecosfera_ai.simulation_engine.params import build_orchestrator, initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
SEEDS = (7, 2027, 31337)
TICKS = 40


def _pair() -> tuple[object, FrameworkTickOrchestrator]:
    legacy = build_orchestrator(PARAMS)
    planet = build_planet_engine(legacy, budget=PARAMS.engine_budget)
    return legacy, FrameworkTickOrchestrator(legacy, planet)


@pytest.mark.parametrize("seed", SEEDS)
def test_framework_reproduces_the_legacy_trajectory(seed: int) -> None:
    legacy, framework = _pair()
    start = initial_state(PlanetSeed("parity", seed), PARAMS)

    direct, through_frame = start, start
    for _ in range(TICKS):
        direct = legacy.tick(direct).state  # type: ignore[attr-defined]
        through_frame = framework.tick(through_frame).state

    assert direct == through_frame


def test_observations_and_delta_are_preserved() -> None:
    """O que o motor de regras causais consome não muda de forma nem de valor."""
    legacy, framework = _pair()
    start = initial_state(PlanetSeed("parity", 555), PARAMS)

    direct = legacy.tick(start)  # type: ignore[attr-defined]
    framed = framework.tick(start)

    assert framed.state == direct.state
    assert framed.delta == direct.delta
    assert framed.observations == direct.observations


def test_bridge_round_trips_without_loss() -> None:
    state = initial_state(PlanetSeed("bridge", 99), PARAMS)
    assert planet_state_of(snapshot_of(state)) == state


def test_framework_orchestrator_keeps_the_legacy_surface() -> None:
    """Os casos de uso não percebem a troca: mesma superfície, mesmos valores."""
    legacy, framework = _pair()

    assert framework.bounds == legacy.bounds  # type: ignore[attr-defined]
    assert framework.subsystem_names == legacy.subsystem_names  # type: ignore[attr-defined]
    assert framework.planet.engine_ids == ("legacy_planet",)


def test_the_adapter_owns_the_transitional_slice_alone() -> None:
    legacy = build_orchestrator(PARAMS)
    planet = build_planet_engine(legacy, budget=PARAMS.engine_budget)

    assert planet.engine_ids == ("legacy_planet",)
    assert planet.registry.owned_slices == {SliceRef.LEGACY: "legacy_planet"}


def test_the_adapter_still_exposes_the_coupling_order() -> None:
    """As sementes dos Engines de M1/M2 continuam visíveis e testáveis."""
    adapter = LegacySubsystemAdapter(build_orchestrator(PARAMS))
    assert adapter.subsystem_names == (
        "physics",
        "chemistry",
        "climate",
        "geology",
        "ocean",
        "life",
    )


def test_legacy_invariants_are_no_ops_on_the_legacy_path() -> None:
    """Elas rodam de verdade no caminho real — e, por construção, não recortam nada.

    É a evidência de que a máquina de invariantes está ligada sem alterar a
    física: o núcleo já aplicou as mesmas faixas antes de devolver o delta.
    """
    legacy = build_orchestrator(PARAMS)
    planet = build_planet_engine(legacy, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("inv", 4242), PARAMS))

    assert legacy_invariants(legacy.bounds), "as invariantes precisam existir"
    for _ in range(TICKS):
        outcome = planet.tick(snapshot)
        assert outcome.breaches == ()
        snapshot = outcome.snapshot


def test_framework_path_feeds_the_event_channel_without_changing_state() -> None:
    """Ligar a observabilidade não move um número (ADR-ARCH-0002)."""
    from ecosfera_ai.shared_kernel.observability import InMemoryEventStore

    legacy = build_orchestrator(PARAMS)
    store = InMemoryEventStore()
    silent = build_planet_engine(legacy, budget=PARAMS.engine_budget)
    observed = build_planet_engine(legacy, budget=PARAMS.engine_budget, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("obs", 8), PARAMS))

    assert silent.tick(snapshot).snapshot == observed.tick(snapshot).snapshot
