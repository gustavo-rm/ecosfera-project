"""O M6.2 RECUPERA; ele não gera, e não conhece LLM algum.

A ordem do M6 é deliberada: fato verificável (M6.0), piso de qualidade por
template (M6.1), recuperação pedagógica (M6.2) e só então o gerador (M6.3). Cada
etapa existe para que a seguinte possa ser avaliada.

Esta subetapa entrega a INFRAESTRUTURA de recuperação. Se ela já compusesse
texto, a fronteira entre "material recuperado" e "texto gerado" desapareceria na
única camada em que ela ainda é fácil de auditar — e o M6.4 não teria como dizer
se uma frase saiu do corpus, do dossiê ou do modelo.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
SRC = SERVICE_ROOT / "src/ecosfera_ai"
RAG_PACKAGES = (SRC / "domain/rag", SRC / "application/rag")

FORBIDDEN_AI = (
    "ollama",
    "langgraph",
    "openai",
    "anthropic",
    "ecosfera_ai.application.ports.llm",
    "ecosfera_ai.infrastructure.llm",
)


def _imports_of(package: Path) -> dict[Path, set[str]]:
    found: dict[Path, set[str]] = {}
    for source in sorted(package.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        found[source] = names
    return found


@pytest.mark.parametrize("package", RAG_PACKAGES, ids=lambda p: p.name)
def test_no_rag_module_imports_an_llm(package: Path) -> None:
    for source, modules in _imports_of(package).items():
        for imported in modules:
            for forbidden in FORBIDDEN_AI:
                assert not imported.startswith(forbidden), (
                    f"{source.name} importa {imported!r}: gerar é o M6.3, e o M6.2 "
                    "é a recuperação contra a qual o gerador será medido"
                )


@pytest.mark.parametrize("package", RAG_PACKAGES, ids=lambda p: p.name)
def test_no_rag_module_reaches_the_fact_or_the_simulation(package: Path) -> None:
    """O corpus é material do PROJETO, não do planeta de ninguém.

    Se a camada de registro pudesse ler o Event Store, a separação entre "o que
    aconteceu" e "como se diz" viraria convenção — e o M6.3 herdaria a confusão
    já embutida na fonte que ele consome.
    """
    forbidden = (
        "ecosfera_ai.engines",
        "ecosfera_ai.simulation_engine",
        "ecosfera_ai.shared_kernel.world_state",
        "ecosfera_ai.domain.consumers",
        "ecosfera_ai.application.consumers",
    )
    for source, modules in _imports_of(package).items():
        for imported in modules:
            for prefix in forbidden:
                assert not imported.startswith(prefix), (
                    f"{source.name} alcança {imported!r}: registro e fato não se misturam"
                )


def test_the_retriever_returns_passages_and_never_composed_prose() -> None:
    """A saída é uma lista de passagens com origem — não um texto montado.

    Se algum dia o retriever devolvesse `str`, a diferença entre citar e escrever
    teria sumido sem que nenhum import proibido aparecesse.
    """
    import inspect

    from ecosfera_ai.application.rag.retrieve import RetrievePassagesUseCase

    for method in (RetrievePassagesUseCase.execute, RetrievePassagesUseCase.for_cause_code):
        annotation = inspect.signature(method).return_annotation
        assert "RetrievedPassage" in str(annotation), (
            f"{method.__name__} devolve {annotation!r}, e não passagens"
        )
        assert str(annotation) != "str"


def test_no_rag_module_concatenates_passages_into_one_text() -> None:
    """A varredura do sinal mais barato de composição: juntar textos de passagens.

    Compor é o M6.3. Um `" ".join(...)` sobre o texto das passagens seria a
    geração nascendo aqui, sem import algum que a denunciasse.
    """
    for package in RAG_PACKAGES:
        for source in sorted(package.rglob("*.py")):
            text = source.read_text(encoding="utf-8")
            for mark in (".join(passage", ".join(p.text", ".join(entry.text"):
                assert mark not in text, f"{source.name} compõe texto a partir de passagens"


def test_the_contracts_name_the_rag_boundary() -> None:
    config = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names = {c["name"] for c in config["tool"]["importlinter"]["contracts"]}
    assert "O RAG do M6.2 recupera, e nao gera" in names
    assert "O corpus pedagogico nao alcanca o fato nem a simulacao" in names


@pytest.mark.skipif(
    shutil.which("lint-imports") is None,
    reason="import-linter não instalado (rode `uv sync --group dev`)",
)
def test_the_contracts_hold() -> None:
    """A varredura por AST vê o import direto; o contrato vê a cadeia inteira."""
    result = subprocess.run(
        ["lint-imports", "--config", str(SERVICE_ROOT / "pyproject.toml")],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_llm_flag_is_still_off_by_default() -> None:
    from ecosfera_ai.config.settings import Settings

    assert Settings().llm_enabled is False
