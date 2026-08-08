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


# ─────────────────────────────────────────────────────────────────────────────
# Portão de "zero skips" — a asserção que faltava.
#
# A marca `fail_without_docker` cobre UM caminho: o arquivo que usa
# `requires_postgres()` e não encontra Docker. Não cobre o arquivo que declara o
# próprio `skipif`, nem o que esquece a marca. Nesses casos o teste pula em
# silêncio e a árvore fica verde.
#
# Até aqui, "nenhum teste pulou no CI" era conferido por um humano lendo a linha
# de resumo e somando à mão. Isso é precisamente a suposição tácita que este
# serviço já pagou caro duas vezes — o `planet_id` que não filtrava e o
# `oxygen` sem escritor. Com a flag ligada, qualquer pulo por infraestrutura
# passa a REPROVAR a suíte, seja qual for o mecanismo que o produziu.
# ─────────────────────────────────────────────────────────────────────────────

_INFRA_SKIP_HINTS = ("docker", "testcontainers", "postgres", "redis")
_infra_skips: list[str] = []


def pytest_runtest_logreport(report: object) -> None:
    if not (getattr(report, "skipped", False) and getattr(report, "when", "") == "setup"):
        return
    longrepr = getattr(report, "longrepr", None)
    detailed = isinstance(longrepr, tuple) and len(longrepr) > 2
    reason = str(longrepr[2]) if detailed else str(longrepr)
    if any(hint in reason.lower() for hint in _INFRA_SKIP_HINTS):
        _infra_skips.append(f"{getattr(report, 'nodeid', '?')} — {reason}")


def pytest_sessionfinish(session: object, exitstatus: int) -> None:
    from tests.docker_guard import postgres_required

    if not (postgres_required() and _infra_skips):
        return
    print(
        "\nECOSFERA_REQUIRE_POSTGRES está ligada e "
        f"{len(_infra_skips)} teste(s) de infraestrutura PULARAM:\n  "
        + "\n  ".join(_infra_skips)
        + "\n\nNeste ambiente a persistência é verificada, não presumida: um pulo "
        "aqui é uma verificação que não aconteceu com a árvore verde.",
    )
    session.exitstatus = 1  # type: ignore[attr-defined]
