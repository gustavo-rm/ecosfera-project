"""O M6.1 ainda não tem LLM — e a fronteira é barrada, não prometida.

A ordem do M6 é deliberada: primeiro o fato verificável (M6.0), depois o PISO de
qualidade por template (M6.1), depois a recuperação pedagógica (M6.2), e só então
o gerador (M6.3). Cada etapa existe para que a seguinte possa ser avaliada.

O piso é o que dá sentido ao LLM. Sem ele, "o modelo está ajudando?" não tem
resposta — não haveria com o que comparar, e qualquer saída fluente pareceria
progresso. Um LLM que entrasse antes desta subetapa estar fechada não teria como
ser reprovado.

Daí a proibição valer para a subetapa inteira, e não só para o pacote novo: a
camada de consumidores, o explicador que a alimenta e a prosa versionada. Todos
os três chegam ao aluno; nenhum deles pode ganhar um gerador antes da hora.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

SERVICE_ROOT = Path(__file__).resolve().parents[2]
SRC = SERVICE_ROOT / "src/ecosfera_ai"

# Os pacotes que compõem o caminho evento -> prosa depois do M6.1.
EXPLANATION_PATH = (
    SRC / "domain/consumers",
    SRC / "application/consumers",
    SRC / "application/feedback",
    SRC / "domain/feedback",
)

FORBIDDEN_AI = (
    "ollama",
    "sentence_transformers",
    "langgraph",
    "openai",
    "anthropic",
    "transformers",
    "ecosfera_ai.rag",
    "ecosfera_ai.embeddings",
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


@pytest.mark.parametrize("package", EXPLANATION_PATH, ids=lambda p: p.name)
def test_no_module_on_the_explanation_path_imports_an_llm(package: Path) -> None:
    for source, modules in _imports_of(package).items():
        for imported in modules:
            for forbidden in FORBIDDEN_AI:
                assert not imported.startswith(forbidden), (
                    f"{source.name} importa {imported!r}: o gerador é o M6.3, e o "
                    "M6.1 é o piso contra o qual ele será medido"
                )


def test_the_import_linter_contract_covers_the_explanation_path() -> None:
    """A varredura por AST vê o import direto; o contrato vê a cadeia inteira."""
    config = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    contracts = config["tool"]["importlinter"]["contracts"]
    named = next(
        c for c in contracts if c["name"] == "A explicacao ate o M6.1 nao depende de LLM nem de RAG"
    )
    sources = set(named["source_modules"])

    assert "ecosfera_ai.domain.consumers" in sources
    assert "ecosfera_ai.application.consumers" in sources
    assert "ecosfera_ai.application.feedback" in sources, (
        "o explicador que narra a trilha ficou fora do contrato — ele é o "
        "caminho mais curto para um LLM entrar sem ninguém notar"
    )


@pytest.mark.skipif(
    shutil.which("lint-imports") is None,
    reason="import-linter não instalado (rode `uv sync --group dev`)",
)
def test_the_contracts_hold() -> None:
    result = subprocess.run(
        ["lint-imports", "--config", str(SERVICE_ROOT / "pyproject.toml")],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_explanation_source_is_declared_as_rules_not_a_model() -> None:
    """A resposta da API diz de onde a frase veio, e hoje ela não vem de modelo."""
    from tests.support_context import branching_cascade
    from tests.support_explanation import context_of, renderer

    from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
    from ecosfera_ai.application.feedback.explain_from_events import (
        ExplainFromEventsUseCase,
        load_translation,
    )
    from ecosfera_ai.domain.feedback.rule_loader import build_engine

    use_case = ExplainFromEventsUseCase(
        ExplainCausalUseCase(build_engine(Path("configs/causal_rules.yaml"))),
        load_translation(Path("configs/event_observations.yaml")),
        renderer(),
    )
    outcome = use_case.execute("planet-m61", list(context_of(branching_cascade()).events))
    assert outcome.explanation.source == "rules"


def test_the_llm_flag_is_still_off_by_default() -> None:
    """A flag existe desde o Inc 0 e continua desligada — nada a ligou por engano."""
    from ecosfera_ai.config.settings import Settings

    assert Settings().llm_enabled is False


def test_no_template_promises_something_a_model_would_have_to_write() -> None:
    """O piso não pode depender de prosa que só um gerador produziria.

    Um template com reticências, um "..." de continuação ou uma instrução do tipo
    "descreva" seria um buraco esperando pelo M6.3 — e até lá o aluno leria a
    lacuna.
    """
    # A marca de lacuna é a palavra inteira em CAIXA ALTA, e não o substrato: em
    # português "atinge todo mundo" contém "todo", e uma busca ingênua acusaria
    # justamente a frase da extinção catastrófica — a mais importante do arquivo.
    marker = re.compile(r"\b(TODO|FIXME|XXX)\b")
    raw = yaml.safe_load(
        (SERVICE_ROOT / "configs/explanation_templates.yaml").read_text(encoding="utf-8")
    )
    for entry in raw["templates"]:
        text = str(entry["text"])
        assert "..." not in text, f"{entry['id']} deixa a frase pela metade"
        assert not marker.search(text), f"{entry['id']} tem lacuna por preencher"


def test_the_gap_marker_check_would_catch_a_real_placeholder() -> None:
    """Contraprova: o filtro pega a lacuna de verdade sem acusar "todo mundo"."""
    marker = re.compile(r"\b(TODO|FIXME|XXX)\b")
    assert marker.search("A frase continua TODO")
    assert not marker.search("um evento assim atinge todo mundo")
