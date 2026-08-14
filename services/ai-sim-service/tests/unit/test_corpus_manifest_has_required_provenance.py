"""Toda entrada do corpus declara de onde veio — e o corpus não inventa currículo.

A pergunta que este arquivo existe para manter respondível é *"por que o Tutor
falou assim com meu filho?"*. A resposta tem de ser um documento, não uma
lembrança — e é por isso que proveniência aqui é invariante, não convenção.

Duas fronteiras, e a segunda é a que se relaxa sob pressão de prazo:

* **origem obrigatória** — nenhuma entrada anônima entra no corpus;
* **licença obrigatória em material externo** — na dúvida sobre a procedência de
  um texto, ele fica de fora. Regra dura, não julgamento a calibrar.
"""

from __future__ import annotations

import pytest
import yaml
from tests.support_rag import MANIFEST_PATH, manifest

from ecosfera_ai.domain.rag.corpus import (
    CorpusCategory,
    CorpusEntry,
    MissingProvenanceError,
)

MANIFEST = manifest()


def test_the_corpus_is_not_empty() -> None:
    """Sem isto, tudo o que segue passaria com o corpus vazio."""
    assert MANIFEST.entries


def test_every_entry_declares_a_source() -> None:
    for entry in MANIFEST.entries:
        assert entry.source.strip(), f"a entrada {entry.entry_id} é anônima"


def test_every_source_points_at_a_document_that_exists() -> None:
    """A origem não pode ser uma frase bonita: ela nomeia arquivo do repositório.

    O caminho vem antes de qualquer '§' ou parêntese de detalhe. Uma origem que
    aponta para um arquivo inexistente é pior que nenhuma — ela passa na revisão
    e falha na auditoria, que é quando importa.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    monorepo = root.parents[1]
    for entry in MANIFEST.entries:
        cited = entry.source.split()[0].split("(")[0].rstrip(",;")
        candidates = [root / cited, monorepo / cited]
        assert any(path.is_file() for path in candidates), (
            f"a entrada {entry.entry_id} cita {cited!r}, que não existe no repositório"
        )


def test_external_references_declare_a_license() -> None:
    for entry in MANIFEST.of_category(CorpusCategory.EXTERNAL_REFERENCE):
        assert entry.license.strip(), (
            f"a referência externa {entry.entry_id} não declara licença; na dúvida, ela fica fora"
        )


def test_an_anonymous_entry_is_refused_by_the_model() -> None:
    """A guarda é do tipo, e não só do arquivo revisado à mão."""
    with pytest.raises(MissingProvenanceError, match="anônimo"):
        CorpusEntry(
            entry_id="SEM-ORIGEM",
            category=CorpusCategory.VOCABULARY_RULE,
            source="   ",
            text="uma regra qualquer",
        )


def test_an_external_reference_without_license_is_refused() -> None:
    with pytest.raises(MissingProvenanceError, match="licença"):
        CorpusEntry(
            entry_id="EXT-SEM-LICENCA",
            category=CorpusCategory.EXTERNAL_REFERENCE,
            source="algum livro",
            text="um trecho qualquer",
        )


def test_an_empty_entry_is_refused() -> None:
    with pytest.raises(MissingProvenanceError, match="vazia"):
        CorpusEntry(
            entry_id="VAZIA",
            category=CorpusCategory.VOCABULARY_RULE,
            source="docs/adr/0019-catastrophic-vs-ecological-extinction.md",
            text="   ",
        )


def test_entry_ids_are_unique() -> None:
    ids = [entry.entry_id for entry in MANIFEST.entries]
    assert len(ids) == len(set(ids)), "há entrada duplicada no manifesto"


def test_a_duplicated_id_fails_the_whole_load() -> None:
    """Um corpus meio carregado é pior que nenhum: ninguém revisou aquele conjunto."""
    import tempfile
    from pathlib import Path

    raw = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw["entries"] = [raw["entries"][0], raw["entries"][0]]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "duplicado.yaml"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        with pytest.raises(MissingProvenanceError, match="duas vezes"):
            from ecosfera_ai.domain.rag.corpus import load_manifest

            load_manifest(path)


def test_the_manifest_declares_the_embedding_model() -> None:
    """Trocar de modelo muda o sentido de toda similaridade já gravada.

    Declarar o modelo no arquivo revisável é o que torna a troca uma mudança
    versionada, e não um efeito colateral de deploy.
    """
    assert MANIFEST.embedding_model.strip()


def test_the_corpus_priority_is_respected() -> None:
    """Regras de linguagem e correções validadas são a maioria do corpus.

    A decisão do ADR 0027: o Tutor tira a VOZ do vocabulário do projeto, não de
    um manual. Se um dia o material externo ou o currículo passar a dominar, esta
    asserção falha e obriga a decisão a ser retomada explicitamente.
    """
    own_voice = len(MANIFEST.of_category(CorpusCategory.VOCABULARY_RULE)) + len(
        MANIFEST.of_category(CorpusCategory.VALIDATED_CORRECTION)
    )
    assert own_voice >= len(MANIFEST.entries) / 2


def test_no_external_reference_was_indexed_this_round() -> None:
    """Decisão registrada do M6.2, e não esquecimento.

    O projeto cita Elton (1927) e Verhulst (1838) nos ADRs como referência
    BIBLIOGRÁFICA; não há neste repositório o texto integral delas com licença
    verificada. Indexar paráfrase própria apresentando-a como "referência externa"
    inventaria proveniência — exatamente o que a categoria existe para impedir.
    """
    assert MANIFEST.of_category(CorpusCategory.EXTERNAL_REFERENCE) == ()
