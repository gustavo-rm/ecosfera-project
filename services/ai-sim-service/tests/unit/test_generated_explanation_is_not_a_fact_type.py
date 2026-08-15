"""`GeneratedExplanation` não pode ocupar o lugar de um fato — terceira vez.

Mesma disciplina que o M6.2 aplicou a `RetrievedPassage`, agora sobre o tipo mais
perigoso dos três: este carrega prosa escrita por um modelo, e prosa gerada é
exatamente o que *soa* como uma afirmação sobre o planeta do aluno.

O risco concreto no M6.4: um harness adversarial vai passar saídas geradas por
funções que hoje recebem dossiê. Se o tipo permitisse a substituição, uma
avaliação inteira poderia rodar tratando texto de modelo como fato do Event
Store — e concluiria que está tudo bem.

A garantia é de FORMA, e a prova executa o `mypy` sobre a atribuição proibida:
afirmar "os tipos são diferentes" lendo o código é a versão frágil do argumento,
porque ela deixa de valer no dia em que alguém acrescentar um campo.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from ecosfera_ai.domain.consumers.explanation import Explanation
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.generation.anchoring import (
    FACT_BEARING_FIELDS,
    GeneratedExplanation,
    RegisterSource,
)
from ecosfera_ai.shared_kernel.events import DomainEvent


def _field_names(cls: type) -> set[str]:
    return {field.name for field in fields(cls)}


# --- Nenhum campo em comum ----------------------------------------------------


def test_a_generated_explanation_carries_no_fact_bearing_field() -> None:
    """Sem `event_id`, sem `occurred_at`, sem `cause_code`, sem `participants`."""
    trespassers = _field_names(GeneratedExplanation) & FACT_BEARING_FIELDS
    assert not trespassers, f"campos de fato apareceram na geração: {sorted(trespassers)}"


def test_the_fact_bearing_list_actually_describes_the_fact_types() -> None:
    """Contraprova da própria lista: uma lista vazia passaria o teste acima.

    Se `FACT_BEARING_FIELDS` deixasse de nomear campos reais de `DomainEvent` e
    `FactualContext`, o teste anterior viraria decoração — verificaria a ausência
    de nomes que ninguém usa.
    """
    real = _field_names(DomainEvent) | _field_names(FactualContext)
    covered = FACT_BEARING_FIELDS & real
    assert len(covered) >= 6, (
        f"a lista de campos de fato descolou dos tipos reais; cobre apenas {sorted(covered)}"
    )


def test_a_generated_explanation_shares_nothing_with_a_domain_event() -> None:
    assert not _field_names(GeneratedExplanation) & _field_names(DomainEvent)


def test_the_provenance_record_carries_no_fact_bearing_field() -> None:
    """`RegisterSource` também não: ele é proveniência de REGISTRO."""
    assert not _field_names(RegisterSource) & FACT_BEARING_FIELDS


# --- Nenhuma ancestralidade comum ---------------------------------------------


def test_there_is_no_shared_ancestry_between_generation_and_fact() -> None:
    """Herança comum abriria a substituição pela porta dos fundos."""
    for fact_type in (DomainEvent, FactualContext, Explanation):
        assert not issubclass(GeneratedExplanation, fact_type)
        assert not issubclass(fact_type, GeneratedExplanation)


# --- E o verificador de tipos recusa, de fato ---------------------------------


FORBIDDEN = """
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.generation.anchoring import GeneratedExplanation


def needs_a_fact(context: FactualContext) -> str:
    return context.planet_id


def hand_it_generated_prose(generated: GeneratedExplanation) -> str:
    return needs_a_fact(generated)
"""


def test_mypy_refuses_to_pass_generated_prose_where_a_fact_is_expected(tmp_path: Path) -> None:
    """A afirmação executada, e não deduzida.

    Se alguém der à geração a forma de um dossiê, o `mypy` para de reclamar e
    ESTE teste falha — que é o alarme que se quer, disparado no momento em que a
    fronteira é enfraquecida e não meses depois.
    """
    offender = tmp_path / "forbidden_assignment.py"
    offender.write_text(FORBIDDEN, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(offender)],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    assert result.returncode != 0, (
        "o mypy ACEITOU passar uma explicação gerada onde se espera um dossiê factual — "
        f"a separação de tipos foi enfraquecida:\n{result.stdout}"
    )
    assert "arg-type" in result.stdout, result.stdout
