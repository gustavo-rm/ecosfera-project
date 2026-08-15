"""Só o adaptador fala com o LLM — e a barreira é de import, não de disciplina.

A exclusividade é o que permite ao M6.4 trocar o modelo por um harness
adversarial, e a qualquer marco futuro trocar de modelo, sem tocar na lógica de
ancoragem. Mais importante: se qualquer outro módulo pudesse falar com o Ollama,
existiria um SEGUNDO caminho até o aluno — e ele não passaria pela verificação de
fundamentação.

O `import-linter` já impõe isso no `pyproject.toml`. Este arquivo existe porque
um contrato pode ser afrouxado num commit que ninguém lê com atenção, e porque
"nenhum outro módulo importa httpx" merece ser afirmado onde alguém o veja ao
mexer na camada.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

from ecosfera_ai.application.generation.language_model import LanguageModelPort
from ecosfera_ai.domain.generation.prompt import AnchoredPrompt
from ecosfera_ai.infrastructure.llm.ollama import NullLanguageModel, OllamaLanguageModel

ADAPTER = Path("src/ecosfera_ai/infrastructure/llm/ollama.py")
GENERATION = (
    Path("src/ecosfera_ai/domain/generation"),
    Path("src/ecosfera_ai/application/generation"),
)
LLM_CLIENTS = {"httpx", "ollama", "openai", "langchain", "langgraph", "requests"}


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


# --- Ninguém além do adaptador -------------------------------------------------


def test_no_generation_module_imports_an_llm_client() -> None:
    """Nem o domínio nem a aplicação da geração conhecem cliente de LLM."""
    for package in GENERATION:
        for module in sorted(package.rglob("*.py")):
            trespassers = _imported_roots(module) & LLM_CLIENTS
            assert not trespassers, f"{module} importa {sorted(trespassers)} — só o adaptador pode"


def test_the_adapter_is_the_only_module_in_the_service_that_talks_http_to_a_model() -> None:
    """Varredura de todo o `src`, e não só da camada de geração.

    O segundo caminho até o aluno não precisaria nascer dentro da geração para
    existir: uma rota HTTP que chamasse o Ollama direto o abriria igual.
    """
    offenders = [
        module
        for module in sorted(Path("src/ecosfera_ai").rglob("*.py"))
        if module != ADAPTER and ({"ollama", "langgraph"} & _imported_roots(module))
    ]
    assert not offenders, f"módulos falando com LLM fora do adaptador: {offenders}"


def test_the_import_contract_that_enforces_this_still_exists() -> None:
    """Se alguém remover o contrato, este teste conta — em vez de o silêncio contar."""
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    contracts = config["tool"]["importlinter"]["contracts"]
    names = {contract["name"] for contract in contracts}

    assert "So o adaptador fala com o LLM" in names
    assert "A verificacao de fundamentacao nao le o corpus" in names


# --- O adaptador satisfaz a porta ---------------------------------------------


def _port_conformance() -> tuple[LanguageModelPort, LanguageModelPort]:
    """Prova, em tempo de checagem de tipo, que as duas implementações servem.

    Mesmo recurso que `postgres_corpus` e `postgres_event_store` usam: sem uma
    atribuição à porta, o `mypy` nada diria sobre uma divergência de assinatura,
    porque nada as atribui à porta no código de produção.
    """
    return OllamaLanguageModel("llama3.1:8b"), NullLanguageModel()


def test_both_implementations_satisfy_the_port() -> None:
    real, null = _port_conformance()
    assert real.model_name == "llama3.1:8b"
    assert null.model_name == "null"


async def test_the_port_never_promises_more_than_prose() -> None:
    """A superfície é estreita de propósito: nada de `chat`, nada de histórico.

    Tudo o que a porta não oferece é coisa que o M6.3 não quer no caminho do
    aluno. Um método `chat` aqui seria a porta lateral por onde a ancoragem
    deixaria de valer.
    """
    for implementation in _port_conformance():
        assert not hasattr(implementation, "chat")
        assert not hasattr(implementation, "complete")
        assert not hasattr(implementation, "history")

    assert await NullLanguageModel().generate(AnchoredPrompt("s", "u")) is None


def test_the_adapter_module_does_not_import_the_corpus_or_the_dossier() -> None:
    """O adaptador manda texto e recebe texto: ele não conhece fato nem passagem.

    Ele importa a porta e o tipo do prompt, e nada mais do domínio — se
    conhecesse o dossiê, poderia decidir sozinho o que mandar, e a montagem do
    prompt deixaria de ser o único lugar onde a ancoragem acontece.
    """
    source = ADAPTER.read_text(encoding="utf-8")
    for forbidden in ("domain.rag", "domain.consumers", "application.rag"):
        assert f"import {forbidden}" not in source and f"from ecosfera_ai.{forbidden}" not in source


@pytest.mark.parametrize("forbidden", ["chat", "complete", "history", "embed"])
def test_the_port_grows_no_second_surface(forbidden: str) -> None:
    """Uma contraprova por método: a estreiteza é a garantia, então ela é cobrada.

    Parametrizado para que o relatório nomeie QUAL superfície apareceu, em vez de
    dizer apenas que o conjunto mudou.
    """
    assert not hasattr(OllamaLanguageModel("m"), forbidden)
    assert not hasattr(NullLanguageModel(), forbidden)
