"""PUREZA: a simulação NÃO lê store, logs, métricas ou traces (invariante).

É a regra que o M5 mais poderia quebrar sem querer. Consolidar a observabilidade
convida a fechar o laço — "o Diretor podia olhar as métricas", "o Engine podia
consultar a trilha" — e qualquer um desses laços mata o replay, porque trilha e
métrica são EFEITO da execução, não entrada dela.

A emissão continua determinística e dentro do loop; a CONSUMAÇÃO (persistir,
projetar, exportar) é lateral e fora dele (ADR-ARCH-0002).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ENGINES_DIR = Path("src/ecosfera_ai/engines")

# Módulos de PLATAFORMA que nenhum Engine de simulação pode alcançar.
PLATFORM = ("portable", "timeseries", "event_query", "export_simulation", "persistence")


def _engine_sources() -> list[Path]:
    return [p for p in ENGINES_DIR.rglob("*.py") if "planet" not in p.parts]


@pytest.mark.parametrize("path", _engine_sources(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_engine_imports_the_platform_layer(path: Path) -> None:
    """Um Engine que importasse o Event Store poderia lê-lo — e leria."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
        elif isinstance(node, ast.Import):
            module = " ".join(a.name for a in node.names)
        else:
            continue
        for forbidden in PLATFORM:
            assert forbidden not in module, f"{path} alcança a plataforma via {module}"


def test_the_tick_produces_the_same_result_with_and_without_a_sink() -> None:
    """A prova FUNCIONAL da pureza: observar não muda o observado.

    Se qualquer Engine lesse o que foi emitido, ligar o sink mudaria a
    trajetória. Este teste roda os dois mundos e exige igualdade bit-a-bit.
    """
    with_sink = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=InMemoryEventStore())
    without = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)

    a = snapshot_of(initial_state(PlanetSeed("purity", 2027), PARAMS))
    b = snapshot_of(initial_state(PlanetSeed("purity", 2027), PARAMS))
    for _ in range(200):
        a = with_sink.tick(a).snapshot
        b = without.tick(b).snapshot

    assert a == b, "observar mudou a simulação — o laço se fechou"


def test_publishing_or_not_does_not_change_the_state() -> None:
    """`publish=False` é o modo do replay: mesmo cálculo, sem tocar o Canal B."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=InMemoryEventStore())
    a = snapshot_of(initial_state(PlanetSeed("publish", 2027), PARAMS))
    b = snapshot_of(initial_state(PlanetSeed("publish", 2027), PARAMS))
    for _ in range(120):
        a = planet.tick(a, publish=True).snapshot
        b = planet.tick(b, publish=False).snapshot
    assert a == b


def test_the_engine_order_is_unchanged_by_the_platform_work() -> None:
    """O M5 é plataforma: não acrescenta nem reordena Engine de simulação."""
    assert ENGINE_ORDER == (
        "astronomy",
        "geology",
        "chemistry",
        "atmosphere",
        "climate",
        "hydrology",
        "resource",
        "evolution",
        "ecology",
        "event",
    )


def test_the_sink_is_only_called_after_the_tick_closes() -> None:
    """O sink recebe eventos DEPOIS do fecho — nunca durante o cálculo.

    Um sink que fosse chamado no meio poderia, em tese, ser lido pelo Engine
    seguinte no mesmo tick. Aqui se afirma que o snapshot já está fechado quando
    o primeiro evento chega.
    """
    seen: list[int] = []

    class Spy(InMemoryEventStore):
        def emit(self, event: object) -> None:  # type: ignore[override]
            seen.append(getattr(getattr(event, "occurred_at", None), "tick", -1))

    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=Spy())
    snapshot = snapshot_of(initial_state(PlanetSeed("sink", 2027), PARAMS))
    outcome = planet.tick(snapshot)

    assert outcome.snapshot.tick == snapshot.tick + 1, "o tick não fechou"
    assert all(tick == snapshot.tick for tick in seen), (
        "o sink recebeu evento de um tick que ainda não havia fechado"
    )
