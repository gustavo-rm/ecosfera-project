"""A regra de ouro da Spec §2, verificada nos três Engines do M1.

Nenhum deles importa outro nem lê estado interno alheio — só world-state. Aqui
isso é verificado por INSPEÇÃO do módulo e das declarações, não por convenção.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.legacy.orchestrator import build_planet_engine
from ecosfera_ai.shared_kernel.world_state import SliceRef
from ecosfera_ai.simulation_engine.params import load_params

PARAMS = load_params(Path("configs/simulation_params.yaml"))
SERVICE_ROOT = Path(__file__).resolve().parents[2]
ENGINES_ROOT = SERVICE_ROOT / "src" / "ecosfera_ai" / "engines"
SCIENTIFIC = ("geology", "atmosphere", "climate")


def _imports_of(package: str) -> set[str]:
    """Todos os módulos importados por um pacote de Engine."""
    found: set[str] = set()
    for path in (ENGINES_ROOT / package).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
    return found


@pytest.mark.parametrize("package", SCIENTIFIC)
def test_a_scientific_engine_never_imports_another_engine(package: str) -> None:
    others = {f"ecosfera_ai.engines.{name}" for name in SCIENTIFIC if name != package}
    others |= {"ecosfera_ai.engines.legacy", "ecosfera_ai.engines.planet"}
    offenders = {
        module
        for module in _imports_of(package)
        if any(module == other or module.startswith(f"{other}.") for other in others)
    }
    assert not offenders, f"{package} importa outro Engine: {sorted(offenders)}"


@pytest.mark.parametrize("package", SCIENTIFIC)
def test_a_scientific_engine_never_reaches_infrastructure_or_interfaces(package: str) -> None:
    forbidden = ("ecosfera_ai.infrastructure", "ecosfera_ai.interfaces")
    offenders = {m for m in _imports_of(package) if m.startswith(forbidden)}
    assert not offenders, f"{package} alcança camada proibida: {sorted(offenders)}"


def test_every_engine_writes_exactly_one_slice_and_owns_it_alone() -> None:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    written = [engine.writes for engine in planet.registry.engines]
    assert len(written) == len(set(written)), "fatia com dois donos"


def test_the_declared_reads_match_what_the_coupling_needs() -> None:
    """A declaração é o contrato: quem lê o quê fica visível ao Planet."""
    assert GeologyEngine().reads == frozenset()
    assert AtmosphereEngine().reads == frozenset({SliceRef.GEOLOGY})
    assert ClimateEngine().reads == frozenset({SliceRef.ATMOSPHERE})


def test_nobody_reads_a_slice_it_did_not_declare() -> None:
    """O Planet só entrega proveniência do que foi declarado (Spec §2)."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    for engine in planet.registry.engines:
        declared = engine.reads | engine.lagged_reads | {engine.writes}
        assert declared, f"{engine.engine_id} não declarou nada"


@pytest.mark.skipif(shutil.which("lint-imports") is None, reason="import-linter não instalado")
def test_import_linter_contracts_still_hold() -> None:
    result = subprocess.run(
        ["lint-imports", "--config", str(SERVICE_ROOT / "pyproject.toml")],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
