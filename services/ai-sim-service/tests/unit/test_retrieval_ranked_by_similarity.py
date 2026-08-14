"""O ranking é por similaridade, decrescente, e o número que sai significa algo.

O M6.3 vai usar a ordem para decidir o que entra no prompt, e o M6.4 vai usar o
número para calibrar confiança. Um ranking fora de ordem faria o consumidor de
cima escolher o material pior achando que escolheu o melhor — e sem nada acusando,
porque a lista continuaria bem formada.

## Uma ressalva medida, e registrada onde ela é usada

A similaridade é comparável DENTRO de uma consulta, e não ENTRE consultas de
formatos diferentes: uma busca de dois tokens contra um texto longo produz número
baixo mesmo sendo a resposta certa. Quem for escolher um limiar único no M6.4
precisa saber disso antes, e não depois de calibrar em cima de uma média que
mistura formatos.
"""

from __future__ import annotations

import pytest
from tests.support_rag import indexed_retriever

from ecosfera_ai.domain.rag.embedding import DeterministicEmbedder, cosine_similarity

QUERIES = (
    "especiação ancestral comum",
    "aptidão contextual",
    "extinção catastrófica meteoro",
    "efeito estufa",
)


@pytest.mark.parametrize("query", QUERIES)
async def test_the_scores_come_out_in_descending_order(query: str) -> None:
    found = await (await indexed_retriever()).execute(query, limit=10)
    scores = [passage.similarity for passage in found]
    assert scores == sorted(scores, reverse=True), f"ranking fora de ordem: {scores}"


@pytest.mark.parametrize("query", QUERIES)
async def test_every_score_is_a_cosine(query: str) -> None:
    found = await (await indexed_retriever()).execute(query, limit=10)
    assert all(-1.0 <= passage.similarity <= 1.0 for passage in found)


async def test_the_reported_score_is_the_real_similarity() -> None:
    """A nota não é decorativa: ela é recalculável a partir do texto indexado.

    Sem isto, o retriever poderia devolver a ordem certa com números inventados,
    e o guardrail do M6.4 se calibraria sobre ficção.
    """
    from tests.support_rag import manifest

    from ecosfera_ai.application.rag.index_corpus import _embeddable_text

    query = "aptidão contextual ou absoluta"
    embedder = DeterministicEmbedder()
    query_vector = embedder.embed([query])[0]
    by_id = {entry.entry_id: entry for entry in manifest().entries}

    found = await (await indexed_retriever()).execute(query, limit=3)
    for passage in found:
        expected = cosine_similarity(
            query_vector, embedder.embed([_embeddable_text(by_id[passage.entry_id])])[0]
        )
        assert passage.similarity == pytest.approx(expected)


async def test_a_closer_passage_outranks_a_farther_one() -> None:
    """O ordenamento reflete o conteúdo, e não a ordem do manifesto."""
    found = await (await indexed_retriever()).execute("aptidão contextual ou absoluta", limit=3)
    assert found[0].entry_id == "VOC-005"
    assert found[0].similarity > found[-1].similarity


async def test_the_limit_takes_the_best_and_not_the_first() -> None:
    """Cortar em `limit` não pode virar "os primeiros do manifesto"."""
    retriever = await indexed_retriever()
    everything = await retriever.execute("especiação ancestral comum", limit=50)
    top_two = await retriever.execute("especiação ancestral comum", limit=2)
    assert [passage.entry_id for passage in top_two] == [
        passage.entry_id for passage in everything[:2]
    ]


async def test_ties_are_broken_deterministically() -> None:
    """Empate resolvido pelo id — senão o mesmo corpus daria ordens diferentes.

    Uma consulta sem token algum empata TUDO em zero, que é o caso extremo em que
    a ordem de inserção apareceria se não houvesse desempate.
    """
    retriever = await indexed_retriever()
    first = await retriever.execute("!!!", limit=5)
    second = await retriever.execute("!!!", limit=5)
    assert [p.entry_id for p in first] == [p.entry_id for p in second]
    assert [p.entry_id for p in first] == sorted(p.entry_id for p in first)


async def test_the_ranking_is_stable_across_reindexing() -> None:
    """Reindexar o mesmo manifesto não pode mudar o que o Tutor recupera."""
    query = "extinção catastrófica"
    first = await (await indexed_retriever()).execute(query, limit=5)
    second = await (await indexed_retriever()).execute(query, limit=5)
    assert [(p.entry_id, p.similarity) for p in first] == [
        (p.entry_id, p.similarity) for p in second
    ]
