"""Filtrar por categoria devolve só aquela categoria — e é isso que dá controle.

Pedir "regras de vocabulário relevantes a este mecanismo" é pergunta diferente de
"objetivos de currículo desta faixa de ensino". Um retriever que misturasse as
duas obrigaria o M6.3 a filtrar depois — e filtrar depois é como se perde o
controle sobre o que entra no prompt do modelo.

O filtro é aqui, na consulta, e não numa limpeza posterior que alguém pode
esquecer de fazer.
"""

from __future__ import annotations

import pytest
from tests.support_rag import indexed_retriever, manifest

from ecosfera_ai.domain.rag.corpus import CorpusCategory

PRESENT = tuple(category for category in CorpusCategory if manifest().of_category(category))


@pytest.mark.parametrize("category", PRESENT, ids=lambda c: c.value)
async def test_filtering_returns_only_that_category(category: CorpusCategory) -> None:
    found = await (await indexed_retriever()).execute(
        "especiação extinção clima", limit=20, categories=frozenset({category})
    )
    assert found, f"a categoria {category.value} não devolveu nada"
    assert all(passage.category is category for passage in found)


async def test_filtering_by_two_categories_returns_both_and_nothing_else() -> None:
    wanted = frozenset({CorpusCategory.VOCABULARY_RULE, CorpusCategory.VALIDATED_CORRECTION})
    found = await (await indexed_retriever()).execute("extinção", limit=20, categories=wanted)
    assert {passage.category for passage in found} <= wanted
    assert len({passage.category for passage in found}) == 2


async def test_no_filter_reaches_every_category_present_in_the_corpus() -> None:
    """A contraprova: sem ela, "só aquela categoria" passaria com o filtro devolvendo nada."""
    found = await (await indexed_retriever()).execute("planeta vida clima espécie", limit=50)
    assert {passage.category for passage in found} == set(PRESENT)


async def test_an_empty_category_set_matches_nothing() -> None:
    """Pedir "nenhuma categoria" devolve nada — e não, silenciosamente, tudo."""
    found = await (await indexed_retriever()).execute(
        "especiação", limit=20, categories=frozenset()
    )
    assert found == ()


async def test_the_category_filter_composes_with_the_cause_code_filter() -> None:
    found = await (await indexed_retriever()).execute(
        "extinção",
        limit=20,
        categories=frozenset({CorpusCategory.VALIDATED_CORRECTION}),
        cause_code="CATASTROPHIC_EVENT",
    )
    assert found
    for passage in found:
        assert passage.category is CorpusCategory.VALIDATED_CORRECTION
        assert "CATASTROPHIC_EVENT" in passage.relevant_cause_codes


async def test_curriculum_entries_carry_their_grade_band_and_codes() -> None:
    """O que torna o filtro por currículo útil ao M6.3: faixa e código viajam junto."""
    found = await (await indexed_retriever()).execute(
        "efeito estufa",
        limit=5,
        categories=frozenset({CorpusCategory.CURRICULUM_OBJECTIVE}),
    )
    top = found[0]
    assert top.grade_band
    assert top.bncc_codes
    assert top.code_verified is not None
