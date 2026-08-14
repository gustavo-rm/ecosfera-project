"""A recuperação traz a passagem CERTA — não apenas alguma passagem.

A diferença é o teste inteiro. Um retriever que devolve o primeiro item do corpus
com uma nota qualquer passa em toda asserção de forma ("veio algo", "tem score",
"tem fonte") e falha no único critério que importa: responder à pergunta.

## O caminho que o M6.3 vai usar de verdade

`for_cause_code` é o atalho central: dado o `cause_code` de um evento REAL do
planeta — que veio do Event Store, não daqui —, quais regras de linguagem
governam a forma de narrá-lo. É consulta filtrada, conjunto candidato pequeno, e
por isso a exigência é de primeiro lugar.

## Texto livre exige estar entre os recuperados, e a diferença é honesta

O embedder de referência é LÉXICO: mede sobreposição de vocabulário, não sentido.
Numa consulta sobre especiação, a regra do ancestral comum e a que separa
adaptação de especiação são as duas respostas legítimas, e um baseline léxico não
tem como ordená-las por importância pedagógica — isso é trabalho do modelo
semântico de produção. O que o M6.2 promete, e o que se verifica aqui, é que a
entrada certa é RECUPERADA.
"""

from __future__ import annotations

import pytest
from tests.support_rag import indexed_retriever

from ecosfera_ai.domain.rag.corpus import CorpusCategory

# --- O caminho por código de causa: exige primeiro lugar ----------------------


@pytest.mark.parametrize(
    ("cause_code", "expected"),
    [
        ("CATASTROPHIC_EVENT", "VAL-Q8"),
        ("DIVERGENT_NICHE", "VOC-002"),
        ("PREY_COLLAPSE", "VAL-Q12"),
        ("THERMAL_INTOLERANCE", "VOC-005"),
    ],
)
async def test_a_cause_code_retrieves_the_rule_that_governs_it(
    cause_code: str, expected: str
) -> None:
    found = await (await indexed_retriever()).for_cause_code(cause_code, limit=3)
    assert found, f"{cause_code} não recuperou regra alguma"
    assert found[0].entry_id == expected, (
        f"{cause_code} trouxe {found[0].entry_id}, e não {expected}"
    )


async def test_the_cause_code_path_only_returns_entries_that_address_it() -> None:
    """O filtro é por chave de roteamento, e não por parecer relevante."""
    found = await (await indexed_retriever()).for_cause_code("CATASTROPHIC_EVENT", limit=10)
    for passage in found:
        assert "CATASTROPHIC_EVENT" in passage.relevant_cause_codes


async def test_the_cause_code_path_returns_only_language_material() -> None:
    """Regras e correções — não objetivos de currículo, que respondem outra pergunta."""
    found = await (await indexed_retriever()).for_cause_code("CATASTROPHIC_EVENT", limit=10)
    assert {passage.category for passage in found} <= {
        CorpusCategory.VOCABULARY_RULE,
        CorpusCategory.VALIDATED_CORRECTION,
    }


async def test_an_unknown_cause_code_retrieves_nothing_rather_than_anything() -> None:
    """Recuperar "o mais próximo" para um código inexistente seria pior que vazio."""
    found = await (await indexed_retriever()).for_cause_code("CODIGO_QUE_NAO_EXISTE")
    assert found == ()


# --- Texto livre: a entrada certa está entre as recuperadas -------------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("especiação ancestral comum linhagens", "VOC-002"),
        ("aptidão contextual ou absoluta", "VOC-005"),
        ("adaptação frequência dos traços numa população", "VOC-003"),
        ("capacidade de suporte níveis tróficos", "VAL-Q11"),
        ("ciclo curto e ciclo longo da água", "VAL-Q15"),
    ],
)
async def test_a_topic_query_retrieves_the_entry_about_that_topic(
    query: str, expected: str
) -> None:
    found = await (await indexed_retriever()).execute(query, limit=3)
    assert expected in {passage.entry_id for passage in found}, (
        f"{query!r} não trouxe {expected}; veio {[p.entry_id for p in found]}"
    )


async def test_a_curriculum_query_retrieves_the_matching_objective() -> None:
    found = await (await indexed_retriever()).execute(
        "efeito estufa gás carbônico temperatura",
        limit=3,
        categories=frozenset({CorpusCategory.CURRICULUM_OBJECTIVE}),
    )
    assert found[0].entry_id == "BNCC-EFEITO-ESTUFA"


async def test_an_unrelated_query_does_not_score_high() -> None:
    """A contraprova: sem ela, um retriever que devolve tudo com nota alta passaria."""
    found = await (await indexed_retriever()).execute("receita de bolo de cenoura", limit=3)
    assert all(passage.similarity < 0.2 for passage in found), (
        f"consulta sem relação obteve nota alta: {[(p.entry_id, p.similarity) for p in found]}"
    )


# --- Proveniência acompanha a recuperação ------------------------------------


async def test_every_retrieved_passage_carries_its_source() -> None:
    """Sem origem a passagem é inútil para auditoria, por mais relevante que seja."""
    found = await (await indexed_retriever()).execute("especiação", limit=10)
    assert found
    for passage in found:
        assert passage.source.strip()
        assert passage.embedding_model == "ecosfera-deterministic-v1"


async def test_a_zero_limit_returns_nothing_without_touching_the_index() -> None:
    assert await (await indexed_retriever()).execute("especiação", limit=0) == ()


async def test_the_minimum_similarity_filter_drops_weak_matches() -> None:
    """O corte existe para quem já sabe o que fazer com recuperação fraca (M6.4)."""
    retriever = await indexed_retriever()
    everything = await retriever.execute("especiação", limit=10)
    strict = await retriever.execute("especiação", limit=10, min_similarity=0.3)
    assert len(strict) < len(everything)
    assert all(passage.similarity >= 0.3 for passage in strict)
