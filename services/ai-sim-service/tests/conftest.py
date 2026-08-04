from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ECOSFERA_CAUSAL_RULES_PATH", str(Path("configs/causal_rules.yaml")))
os.environ.setdefault(
    "ECOSFERA_SIMULATION_PARAMS_PATH", str(Path("configs/simulation_params.yaml"))
)

from ecosfera_ai.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def pytest_configure(config: object) -> None:
    """Registra a marca que transforma "sem Docker" em falha (ver docker_guard)."""
    config.addinivalue_line(  # type: ignore[attr-defined]
        "markers",
        "fail_without_docker: exige Docker; falha (em vez de pular) quando "
        "ECOSFERA_REQUIRE_POSTGRES está ligada",
    )


def pytest_runtest_setup(item: object) -> None:
    if item.get_closest_marker("fail_without_docker") is not None:  # type: ignore[attr-defined]
        raise AssertionError(
            "ECOSFERA_REQUIRE_POSTGRES está ligada e não há daemon Docker: "
            "os testes de persistência NÃO podem ser pulados neste ambiente"
        )
