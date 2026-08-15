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
    config.addinivalue_line(  # type: ignore[attr-defined]
        "markers",
        "fail_without_ollama: exige um daemon Ollama com o modelo baixado; falha "
        "(em vez de pular) quando ECOSFERA_REQUIRE_OLLAMA está ligada",
    )


def pytest_runtest_setup(item: object) -> None:
    if item.get_closest_marker("fail_without_docker") is not None:  # type: ignore[attr-defined]
        raise AssertionError(
            "ECOSFERA_REQUIRE_POSTGRES está ligada e não há daemon Docker: "
            "os testes de persistência NÃO podem ser pulados neste ambiente"
        )
    if item.get_closest_marker("fail_without_ollama") is not None:  # type: ignore[attr-defined]
        raise AssertionError(
            "ECOSFERA_REQUIRE_OLLAMA está ligada e não há daemon Ollama respondendo: "
            "os testes de geração real NÃO podem ser pulados neste ambiente"
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

# Cada família de pulo responde ao SEU requisito, e não a qualquer um deles.
#
# A primeira versão desta guarda tratava "infraestrutura" como um bloco só, e o
# CI a reprovou na primeira execução com dois jobs: o `quality-gate` roda com
# Postgres exigido e SEM Ollama, então os testes de geração pulam ali por um
# motivo perfeitamente legítimo — eles têm job próprio. Somar os dois faria a
# política exigir, de todo job, uma infraestrutura que só um deles tem.
#
# O mapeamento abaixo é o que mantém a exigência estrita onde ela vale: um pulo
# que menciona Ollama só reprova quando ECOSFERA_REQUIRE_OLLAMA está ligada.
_SKIP_FAMILIES: dict[str, tuple[str, ...]] = {
    "postgres": ("docker", "testcontainers", "postgres", "redis"),
    "ollama": ("ollama",),
}
_infra_skips: dict[str, list[str]] = {family: [] for family in _SKIP_FAMILIES}


def pytest_runtest_logreport(report: object) -> None:
    if not (getattr(report, "skipped", False) and getattr(report, "when", "") == "setup"):
        return
    longrepr = getattr(report, "longrepr", None)
    detailed = isinstance(longrepr, tuple) and len(longrepr) > 2
    reason = str(longrepr[2]) if detailed else str(longrepr)
    lowered = reason.lower()
    for family, hints in _SKIP_FAMILIES.items():
        if any(hint in lowered for hint in hints):
            _infra_skips[family].append(f"{getattr(report, 'nodeid', '?')} — {reason}")
            return


def pytest_sessionfinish(session: object, exitstatus: int) -> None:
    from tests.docker_guard import postgres_required
    from tests.ollama_guard import ollama_required

    required = {"postgres": postgres_required(), "ollama": ollama_required()}
    offending = [
        entry for family, entries in _infra_skips.items() if required[family] for entry in entries
    ]
    if not offending:
        return
    print(
        f"\nUm requisito de infraestrutura está ligado e {len(offending)} teste(s) "
        "que ele cobre PULARAM:\n  "
        + "\n  ".join(offending)
        + "\n\nNeste ambiente a infraestrutura é verificada, não presumida: um pulo "
        "aqui é uma verificação que não aconteceu com a árvore verde.",
    )
    session.exitstatus = 1  # type: ignore[attr-defined]
