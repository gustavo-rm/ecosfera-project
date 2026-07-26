from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ECOSFERA_CAUSAL_RULES_PATH", str(Path("configs/causal_rules.yaml")))
os.environ.setdefault(
    "ECOSFERA_SIMULATION_PARAMS_PATH", str(Path("configs/simulation_params.yaml"))
)

from ecosfera_ai.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
