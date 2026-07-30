"""A regra de ouro da Spec §2, verificada por ferramenta e não por disciplina.

`import-linter` lê os contratos declarados em `pyproject.toml`. Trazê-lo para
dentro do pytest garante que a fronteira quebre o `make check` local, e não só o
pipeline — quem viola descobre antes de abrir o PR.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    shutil.which("lint-imports") is None,
    reason="import-linter não instalado (rode `uv sync --group dev`)",
)


def test_engine_and_layer_boundaries_hold() -> None:
    result = subprocess.run(
        ["lint-imports", "--config", str(SERVICE_ROOT / "pyproject.toml")],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "contrato de importação violado — um Engine alcançou o que não devia:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_the_contracts_cover_the_rules_of_the_spec() -> None:
    """Guarda contra o contrato ser removido do pyproject sem ninguém notar."""
    import tomllib

    config = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names = {c["name"] for c in config["tool"]["importlinter"]["contracts"]}

    assert "Engines nao importam outros Engines" in names
    assert "Moldura e Engines nao alcancam infraestrutura nem interfaces" in names
