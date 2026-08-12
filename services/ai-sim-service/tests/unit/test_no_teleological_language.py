"""BIO-005 — nada no sistema atribui INTENÇÃO à evolução.

O erro conceitual mais comum e mais grave, e o que a plataforma existe para
desfazer: "a espécie desenvolveu resistência", "evoluiu para sobreviver". É
Lamarckismo com roupa nova — o organismo mudando porque precisava.

A formulação correta tem duas metades, e as duas precisam aparecer:

  * a variação vem ANTES e sem propósito — "surgiu uma mutação aleatória";
  * o ambiente decide DEPOIS — "a característica aumentou a sobrevivência
    porque o ambiente era X".

Esta é a diretriz de vocabulário que o Tutor do M6 herda. Guardá-la agora é o
que impede que ela chegue lá como boa intenção.

**Uso × menção.** Citar a formulação errada para rejeitá-la é o oposto do
defeito, e a documentação faz exatamente isso. Por isso, no código e nos ADRs, a
linha só conta como denúncia quando a frase aparece FORA de aspas — mesma
técnica de `test_contextual_fitness_wording`. Nos `template` das regras causais
não há exceção alguma: ali tudo é prosa que chega ao aluno.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# Lista negra MÍNIMA: formulações que afirmam intenção, propósito ou progresso.
# Curta de propósito — uma lista longa vira ruído e ninguém a mantém.
TELEOLOGICAL = (
    "desenvolveu resistência",
    "desenvolveram resistência",
    "criou resistência",
    "criaram resistência",
    "desenvolveu a capacidade",
    "evoluiu para",
    "evoluir para",
    "evoluíram para",
    "para se adaptar",
    "a fim de se adaptar",
    "se adaptou para",
    "adaptou-se para",
    "a fim de sobreviver",
    "com o objetivo de sobreviver",
    "a espécie quis",
    "a espécie decidiu",
    "a espécie precisava",
    "a espécie precisou",
    "a natureza escolheu",
    "a evolução escolheu",
    "mais evoluída",
    "mais evoluído",
)

RULES = Path("configs/causal_rules.yaml")
# A prosa do M6.1 entra NESTA guarda, e não numa segunda parecida. O vocabulário
# anti-teleológico é UM: fosse duplicado, uma das cópias envelheceria sozinha, e
# a que envelhecesse seria justamente a que alguém consultaria ao escrever a
# frase seguinte. Quem acrescentar um arquivo de prosa acrescenta-o aqui.
EXPLANATIONS = Path("configs/explanation_templates.yaml")
SOURCES = sorted(Path("src/ecosfera_ai").rglob("*.py"))
ADRS = sorted(Path("docs/adr").glob("*.md"))


def _templates() -> list[str]:
    """Toda a prosa versionada que pode chegar ao aluno, dos dois arquivos."""
    rules: dict[str, Any] = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    prose = [str(rule["template"]) for rule in rules.get("rules", [])]

    explanations: dict[str, Any] = yaml.safe_load(EXPLANATIONS.read_text(encoding="utf-8")) or {}
    prose += [str(entry["text"]) for entry in explanations.get("templates", [])]
    # As orações de mecanismo são prosa tanto quanto os templates: elas entram
    # nas frases inteiras, e uma formulação teleológica ali chegaria ao aluno
    # exatamente do mesmo jeito.
    prose += [str(text) for text in (explanations.get("mechanisms") or {}).values()]
    prose += [str(text) for text in (explanations.get("nouns") or {}).values()]
    return prose


def _without_quoted(line: str) -> str:
    """Remove o que está entre aspas: ali a frase é MENÇÃO, não uso."""
    return re.sub(r'"[^"]*"|«[^»]*»|“[^”]*”', "", line)


# --- A prosa que chega ao aluno -----------------------------------------------


def test_no_causal_rule_template_is_teleological() -> None:
    """As regras causais SÃO a fala do sistema no MVP — sem LLM entre elas e o aluno."""
    for template in _templates():
        lowered = template.lower()
        for phrase in TELEOLOGICAL:
            assert phrase not in lowered, (
                f"a regra causal atribui intenção à evolução: {template!r} contém {phrase!r}"
            )


def test_the_rules_say_the_variation_came_first_and_by_chance() -> None:
    """Metade um da formulação correta: a mutação é aleatória e não escolhida."""
    prose = " ".join(_templates()).lower()
    assert "mutação aleatória" in prose, (
        "nenhuma regra descreve a mutação como ALEATÓRIA — sem isso o aluno "
        "preenche a lacuna com propósito"
    )


def test_the_rules_say_the_environment_decided_afterwards() -> None:
    """Metade dois: a vantagem é consequência do ambiente, não de um plano."""
    prose = " ".join(_templates()).lower()
    assert "aumentou a sobrevivência" in prose
    assert "porque" in prose, "a vantagem aparece sem a causa ambiental que a explica"


# --- O código e os ADRs, com a distinção uso × menção -------------------------


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_no_source_file_uses_a_teleological_formulation(path: Path) -> None:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        unquoted = _without_quoted(line.lower())
        for phrase in TELEOLOGICAL:
            assert phrase not in unquoted, (
                f"{path}:{number} atribui intenção à evolução ({phrase!r}) — BIO-005"
            )


@pytest.mark.parametrize("path", ADRS, ids=lambda p: p.name)
def test_no_adr_uses_a_teleological_formulation(path: Path) -> None:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        unquoted = _without_quoted(line.lower())
        for phrase in TELEOLOGICAL:
            assert phrase not in unquoted, (
                f"{path}:{number} atribui intenção à evolução ({phrase!r}) — BIO-005"
            )


def test_the_mutation_is_documented_as_undirected_in_the_domain() -> None:
    """A ordem correta (variação → ambiente) está escrita onde a mutação vive."""
    text = Path("src/ecosfera_ai/engines/evolution/domain.py").read_text(encoding="utf-8")
    assert "não-direcionada" in text
    assert "aleatória" in text


# --- Contraprova do próprio filtro --------------------------------------------


def test_the_guard_would_catch_a_real_teleological_sentence() -> None:
    """Sem esta contraprova, a lista negra poderia estar simplesmente errada."""
    offender = "a comunidade desenvolveu resistência ao calor"
    assert any(phrase in _without_quoted(offender) for phrase in TELEOLOGICAL)


def test_the_guard_does_not_accuse_a_quoted_mention() -> None:
    """Citar o erro para rejeitá-lo é o oposto do erro."""
    mention = 'nunca dizer "a espécie desenvolveu resistência" ao aluno'
    assert not any(phrase in _without_quoted(mention) for phrase in TELEOLOGICAL)
