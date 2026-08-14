"""A superfície portável do RAG e as guardas que falham alto.

Formas serializáveis (para a auditoria humana e para a rota futura) e os erros que
o pipeline levanta em vez de degradar. São a parte do contrato que o M6.3 vai
consumir e que o M6.4 vai gravar — se ela mudar de forma em silêncio, os dois
quebram longe daqui.
"""

from __future__ import annotations

import pytest
from tests.support_rag import indexed_retriever, manifest

from ecosfera_ai.application.rag.corpus_index import InMemoryCorpusIndex
from ecosfera_ai.application.rag.index_corpus import (
    EmbeddingModelMismatchError,
    IndexCorpusUseCase,
)
from ecosfera_ai.application.rag.retrieve import passages_to_dicts
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder, cosine_similarity


async def test_the_index_report_is_portable_and_names_every_source() -> None:
    """O relatório é a trilha de auditoria da indexação."""
    report = await IndexCorpusUseCase(DeterministicEmbedder(), InMemoryCorpusIndex()).execute(
        manifest()
    )
    payload = report.to_dict()

    assert payload["model_name"] == "ecosfera-deterministic-v1"
    assert payload["indexed"] == len(manifest().entries)
    assert sum(dict(payload["by_category"]).values()) == payload["indexed"]  # type: ignore[arg-type]
    assert payload["sources"]


async def test_indexing_with_the_wrong_model_fails_loudly() -> None:
    """Gravar vetores de um modelo sob o nome de outro é o defeito silencioso.

    O sintoma seria a passagem errada com um número plausível ao lado — não uma
    exceção — porque a consulta compararia espaços vetoriais distintos.
    """

    class _OtherModel(DeterministicEmbedder):
        @property
        def name(self) -> str:
            return "outro-modelo-v9"

    with pytest.raises(EmbeddingModelMismatchError, match="outro-modelo-v9"):
        await IndexCorpusUseCase(_OtherModel(), InMemoryCorpusIndex()).execute(manifest())


def test_a_corpus_entry_serializes_with_its_provenance() -> None:
    entry = next(e for e in manifest().entries if e.category is CorpusCategory.CURRICULUM_OBJECTIVE)
    payload = entry.to_dict()

    assert payload["source"] == entry.source
    assert payload["bncc_codes"] == list(entry.bncc_codes)
    assert payload["code_verified"] == entry.code_verified


async def test_passages_serialize_with_score_source_and_model() -> None:
    """O que a rota de auditoria e o M6.4 vão gravar."""
    found = await (await indexed_retriever()).execute("especiação", limit=2)
    payloads = passages_to_dicts(found)

    assert len(payloads) == len(found)
    for payload, passage in zip(payloads, found, strict=True):
        assert payload["entry_id"] == passage.entry_id
        assert payload["source"] == passage.source
        assert payload["similarity"] == passage.similarity
        assert payload["embedding_model"] == "ecosfera-deterministic-v1"


def test_a_serialized_passage_carries_no_fact_bearing_key() -> None:
    """A separação registro × fato vale também na forma portável.

    É onde ela se perderia mais facilmente: um dicionário não tem tipo, e é
    dicionário que vai para dentro de um prompt no M6.3.
    """
    from ecosfera_ai.domain.rag.passage import FACT_BEARING_FIELDS, RetrievedPassage

    payload = RetrievedPassage(
        entry_id="VOC-001",
        category=CorpusCategory.VOCABULARY_RULE,
        source="docs/adr/0023-common-ancestor-speciation-model.md",
        text="regra",
        similarity=0.5,
    ).to_dict()
    assert not set(payload) & FACT_BEARING_FIELDS


def test_comparing_vectors_of_different_sizes_fails_loudly() -> None:
    """Quase sempre o sinal de que dois modelos foram misturados."""
    with pytest.raises(ValueError, match="dimensões diferentes"):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


def test_a_null_vector_is_similar_to_nothing() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


async def test_the_in_memory_index_keeps_models_apart() -> None:
    """Reindexar com um modelo não apaga o que o outro gravou."""
    index = InMemoryCorpusIndex()
    embedder = DeterministicEmbedder()
    await IndexCorpusUseCase(embedder, index).execute(manifest())

    await index.replace_all("outro-modelo-v9", [])
    found = await index.search(embedder.name, embedder.embed(["especiação"])[0], limit=5)
    assert found, "reindexar outro modelo apagou o corpus deste"
