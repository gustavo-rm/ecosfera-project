"""Uma passagem recuperada NÃO pode ocupar o lugar de um fato — garantia de tipo.

A decisão arquitetural central do M6.2, e o motivo de ela ser verificada por
ferramenta e não por disciplina.

## O modo de falha que isto impede

No M6.3 um LLM vai receber, no mesmo prompt, o dossiê factual do planeta daquele
aluno (M6.0/M6.1) e algumas passagens deste corpus. Se as duas chegarem com a
mesma cara, nada impede que uma passagem dizendo *"extinções catastróficas são
independentes de aptidão"* seja lida como *"houve uma extinção catastrófica neste
planeta"*. A frase resultante seria fluente, pedagogicamente correta em tese, e
FALSA sobre o planeta da criança — ancorada num corpus real, e não no event log
dela. É a alucinação mais difícil de detectar que este desenho admite, e não
precisa de um modelo mal-comportado: basta um tipo permissivo demais.

## As três camadas da garantia

1. **Campos disjuntos** — uma passagem não tem `event_id`, `occurred_at`,
   `cause_code` nem nada que caracterize um fato. Tratá-la como fato quebra na
   primeira leitura de atributo, em vez de produzir narrativa errada em silêncio.
2. **Sem parentesco** — nenhuma herança comum, nenhum protocolo comum, `isinstance`
   falso nos dois sentidos.
3. **O verificador de tipos recusa** — e isto é afirmado rodando o `mypy` sobre a
   atribuição proibida, e não deduzido de que "os tipos são diferentes".
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import fields
from pathlib import Path

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.passage import FACT_BEARING_FIELDS, RetrievedPassage
from ecosfera_ai.shared_kernel.events import DomainEvent

SERVICE_ROOT = Path(__file__).resolve().parents[2]

PASSAGE = RetrievedPassage(
    entry_id="VOC-002",
    category=CorpusCategory.VOCABULARY_RULE,
    source="docs/adr/0023-common-ancestor-speciation-model.md",
    text="Duas linhagens compartilham um ancestral comum.",
    similarity=0.9,
)


# --- 1. Campos disjuntos ------------------------------------------------------


def test_a_passage_carries_no_fact_bearing_field() -> None:
    names = {field.name for field in fields(RetrievedPassage)}
    leaked = names & FACT_BEARING_FIELDS
    assert not leaked, f"RetrievedPassage ganhou campo de fato: {leaked}"


def test_the_fact_types_really_do_carry_those_fields() -> None:
    """Contraprova: sem ela, a lista de campos proibidos poderia estar vazia de fato."""
    event_fields = {field.name for field in fields(DomainEvent)}
    context_fields = {field.name for field in fields(FactualContext)}
    assert event_fields & FACT_BEARING_FIELDS, "a lista não descreve um DomainEvent"
    assert context_fields & FACT_BEARING_FIELDS, "a lista não descreve um FactualContext"


def test_a_passage_has_no_attribute_that_a_narrator_would_read_from_a_fact() -> None:
    """Quem tratar a passagem como evento quebra AGORA, e não na frase do aluno."""
    for attribute in ("event_id", "occurred_at", "cause_code", "causation_id", "participants"):
        assert not hasattr(PASSAGE, attribute), (
            f"a passagem responde a {attribute!r} e passaria por um fato"
        )


# --- 2. Sem parentesco --------------------------------------------------------


def test_a_passage_is_not_an_event_and_an_event_is_not_a_passage() -> None:
    from tests.support_context import branching_cascade

    event = branching_cascade()[0]
    assert not isinstance(PASSAGE, DomainEvent)
    assert not isinstance(event, RetrievedPassage)


def test_the_two_hierarchies_share_no_base_beyond_object() -> None:
    passage_bases = set(type(PASSAGE).__mro__) - {object}
    event_bases = set(DomainEvent.__mro__) - {object}
    context_bases = set(FactualContext.__mro__) - {object}
    assert not passage_bases & event_bases
    assert not passage_bases & context_bases


def test_a_passage_cannot_be_put_into_a_factual_context() -> None:
    """O dossiê é construído a partir de eventos, e recusa qualquer outra coisa."""
    context = FactualContext.of("planet-rag", ContextSlice.of_era(1), ())
    assert context.is_empty
    assert all(isinstance(event, DomainEvent) for event in context.events)


# --- 3. O verificador de tipos recusa, e isso é EXECUTADO ---------------------


def test_mypy_refuses_a_passage_where_a_fact_is_expected() -> None:
    """A garantia afirmada rodando a ferramenta, não deduzida.

    Sem este teste, "os tipos são diferentes" seria uma observação sobre o código
    de hoje. Com ele, a fronteira é verificada: se alguém der à passagem a forma
    de um evento — por herança, por protocolo estrutural, por `Any` no meio do
    caminho —, o `mypy` para de reclamar e este teste falha.
    """
    probe = """
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.passage import RetrievedPassage
from ecosfera_ai.shared_kernel.events import DomainEvent


def narra(event: DomainEvent) -> str:
    return event.event_type


passage = RetrievedPassage(
    entry_id="VOC-002",
    category=CorpusCategory.VOCABULARY_RULE,
    source="docs/adr/0023-common-ancestor-speciation-model.md",
    text="Duas linhagens compartilham um ancestral comum.",
    similarity=0.9,
)
narra(passage)
FactualContext.of("p", ContextSlice.of_era(1), (passage,))
"""
    with tempfile.TemporaryDirectory() as tmp:
        probe_file = Path(tmp) / "probe.py"
        probe_file.write_text(probe, encoding="utf-8")
        result = subprocess.run(
            ["uv", "run", "mypy", "--strict", "--no-error-summary", str(probe_file)],
            cwd=SERVICE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode != 0, (
        "o mypy ACEITOU passar uma passagem onde um fato é esperado — a fronteira "
        f"entre registro e fato deixou de existir:\n{result.stdout}"
    )
    assert "arg-type" in result.stdout, (
        f"o mypy reprovou por outro motivo que não o tipo do argumento:\n{result.stdout}"
    )


def test_the_probe_itself_would_pass_with_a_real_event() -> None:
    """Contraprova do teste acima: o roteiro só reprova por causa da passagem."""
    probe = """
from ecosfera_ai.shared_kernel.events import DomainEvent


def narra(event: DomainEvent) -> str:
    return event.event_type
"""
    with tempfile.TemporaryDirectory() as tmp:
        probe_file = Path(tmp) / "ok.py"
        probe_file.write_text(probe, encoding="utf-8")
        result = subprocess.run(
            ["uv", "run", "mypy", "--strict", "--no-error-summary", str(probe_file)],
            cwd=SERVICE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, f"o roteiro de controle já falhava sozinho:\n{result.stdout}"
