"""O consumidor SÓ lê o Event Store — e, nesta subetapa, não conhece LLM algum.

Duas fronteiras, verificadas por ferramenta e não por disciplina.

**A primeira é a regra de ouro da Spec §2**, metade que o M5 ainda não tinha
barrado: *"Consumidores só leem o Event Store"*. Sem barreira, o caminho mais
curto para o dossiê responder uma pergunta difícil é espiar o world-state ou
chamar um Engine — e um consumidor que lê memória de Engine deixa de ser
derivável do event log, que é a ÚNICA definição de correção que o M6 tem. A
plataforma não teria como distinguir o Tutor certo do Tutor que inventa.

**A segunda é a fronteira de SUBETAPA.** O M6.0 é a fundação factual, e ela é
deliberadamente anterior ao LLM: primeiro o fato verificável, depois quem o
reescreve (M6.3). Enquanto a subetapa for esta, uma dependência de Ollama, de
embeddings ou de RAG é regressão de escopo — e o contrato a nomeia em vez de
confiar na memória de quem revisa o PR.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
CONSUMER_PACKAGES = (
    SERVICE_ROOT / "src/ecosfera_ai/domain/consumers",
    SERVICE_ROOT / "src/ecosfera_ai/application/consumers",
)

# O que um consumidor read-side não pode alcançar, direta ou indiretamente.
FORBIDDEN_PREFIXES = (
    "ecosfera_ai.engines",
    "ecosfera_ai.simulation_engine",
    "ecosfera_ai.shared_kernel.world_state",
    "ecosfera_ai.infrastructure",
    "ecosfera_ai.interfaces",
)

# O que a SUBETAPA M6.0 não pode alcançar — o LLM entra no M6.3.
FORBIDDEN_AI = (
    "ollama",
    "sentence_transformers",
    "langgraph",
    "openai",
    "ecosfera_ai.rag",
    "ecosfera_ai.embeddings",
    "ecosfera_ai.application.ports.llm",
    "ecosfera_ai.infrastructure.llm",
)


def _imported_modules() -> dict[Path, set[str]]:
    """Todo módulo importado por cada arquivo dos pacotes de consumidor."""
    found: dict[Path, set[str]] = {}
    for package in CONSUMER_PACKAGES:
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


def test_the_consumer_packages_exist_where_the_boundary_is_declared() -> None:
    """Guarda contra o pacote ser movido e as barreiras ficarem apontando ao vazio."""
    for package in CONSUMER_PACKAGES:
        assert package.is_dir(), f"{package} sumiu — os contratos deixaram de barrar algo"


def test_no_consumer_module_imports_an_engine_or_the_world_state() -> None:
    for source, modules in _imported_modules().items():
        for imported in modules:
            for forbidden in FORBIDDEN_PREFIXES:
                assert not imported.startswith(forbidden), (
                    f"{source.name} importa {imported!r}: um consumidor read-side "
                    "lê o Event Store e nada mais (Spec §2)"
                )


def test_no_consumer_module_imports_an_llm_or_a_rag_component() -> None:
    for source, modules in _imported_modules().items():
        for imported in modules:
            for forbidden in FORBIDDEN_AI:
                assert not imported.startswith(forbidden), (
                    f"{source.name} importa {imported!r}: o LLM é a subetapa M6.3, "
                    "e o M6.0 é a fundação factual que vem antes dele"
                )


def test_the_consumer_reads_through_the_m5_query_contract() -> None:
    """A leitura passa pela PORTA, e não por um segundo mecanismo paralelo.

    O M6.0 consome `EventStoreQuery`; reimplementar a leitura daria duas cópias
    da regra de recorte, e é assim que o `planet_id` fantasma do M5 nasceu.
    """
    assembler = SERVICE_ROOT / "src/ecosfera_ai/application/consumers/assemble_context.py"
    imports = _imported_modules()[assembler]
    assert "ecosfera_ai.application.platform.event_query" in imports


def test_the_domain_dossier_does_not_depend_on_the_application_layer() -> None:
    """O modelo do dossiê é puro: ele não sabe de onde os eventos vieram."""
    for source, modules in _imported_modules().items():
        if "domain" not in source.parts:
            continue
        for imported in modules:
            assert not imported.startswith("ecosfera_ai.application"), (
                f"{source.name} inverteu a camada: domínio importando aplicação"
            )


@pytest.mark.skipif(
    shutil.which("lint-imports") is None,
    reason="import-linter não instalado (rode `uv sync --group dev`)",
)
def test_the_import_linter_contracts_enforce_the_same_boundaries() -> None:
    """A mesma fronteira, agora por ferramenta e sobre o grafo INDIRETO.

    A varredura por AST acima vê o import direto. O `import-linter` vê a cadeia:
    um consumidor que alcance um Engine por três saltos também reprova.
    """
    result = subprocess.run(
        ["lint-imports", "--config", str(SERVICE_ROOT / "pyproject.toml")],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_two_consumer_contracts_are_declared_in_the_pyproject() -> None:
    """Guarda contra o contrato ser removido sem ninguém notar."""
    config = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names = {c["name"] for c in config["tool"]["importlinter"]["contracts"]}
    assert "Consumidores read-side so alcancam o Event Store" in names
    assert "A explicacao ate o M6.1 nao depende de LLM nem de RAG" in names
