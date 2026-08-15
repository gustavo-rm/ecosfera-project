"""Trocar uma passagem irmã pela outra não muda fato algum — correção 3 do M6.3.

O achado vem do portão do embedder (ADR 0027, adendo). Para a mesma consulta, a
busca por similaridade devolve tanto a regra de vocabulário quanto a correção
validada que diz a MESMA coisa, e qual delas vem em primeiro depende do modelo de
embedding: o léxico preferiu VAL-Q8, o semântico preferiu VOC-006.

Isso é ambiguidade de CATEGORIA, não de qualidade — as duas são orientação de
registro legítima. Este arquivo afirma que a ambiguidade não vaza para lugar
nenhum onde importe:

  1. o veredito de fundamentação não muda;
  2. o conteúdo FACTUAL da saída não muda;
  3. a ordem do prompt é estável, porque a arbitragem é por categoria.

O item 3 é o que resolve o problema em vez de tolerá-lo. Sem ele, trocar de
embedder mudaria o prompt — e um prompt que varia com uma escolha de
infraestrutura é irreprodutível justamente onde se tenta medir um componente
não-determinístico.
"""

from __future__ import annotations

from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import (
    ScriptedModel,
    cascade_context,
    passage,
    sibling_passages,
    spec,
    use_case,
)

from ecosfera_ai.application.generation.generate_explanation import arbitrate_by_category
from ecosfera_ai.domain.generation.grounding import verify_grounding
from ecosfera_ai.domain.rag.corpus import CorpusCategory

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()
FAITHFUL = (
    "No ciclo 100, a queda de um meteoro atingiu o planeta. Um evento assim não escolhe "
    "quem sobrevive: elimina quem estava ali, por mais bem adaptada que a comunidade "
    "estivesse ao ambiente em que vivia."
)


# --- 1. O veredito não depende de qual irmã foi recuperada --------------------


def test_the_verdict_is_the_same_whichever_sibling_was_retrieved() -> None:
    """E a razão é estrutural: o verificador não lê passagem nenhuma.

    A tolerância aqui não é um caso especial tratado com cuidado — é consequência
    de o verificador conferir a saída contra o PISO e o DOSSIÊ. O contrato de
    import "A verificacao de fundamentacao nao le o corpus" é o que impede que
    alguém, um dia, faça o veredito depender do corpus sem perceber.
    """
    rule, correction = sibling_passages()
    del rule, correction  # a passagem não entra na chamada: é esse o ponto

    verdict = verify_grounding(FAITHFUL, floor=FLOOR, context=CONTEXT, spec=spec())
    assert verdict.passed, verdict.reasons


# --- 2. O conteúdo factual não muda -------------------------------------------


async def test_the_factual_content_is_unaffected_by_which_sibling_informs_register() -> None:
    """As duas execuções recebem irmãs distintas e afirmam o mesmo sobre o planeta."""
    rule, correction = sibling_passages()

    with_rule = await use_case(ScriptedModel(FAITHFUL)).execute(
        floor=FLOOR, context=CONTEXT, passages=[rule]
    )
    with_correction = await use_case(ScriptedModel(FAITHFUL)).execute(
        floor=FLOOR, context=CONTEXT, passages=[correction]
    )

    assert with_rule.text == with_correction.text
    assert with_rule.verdict.passed == with_correction.verdict.passed
    assert with_rule.fell_back is with_correction.fell_back is False
    # O piso é o mesmo nos dois: é ele que diz o que aconteceu.
    assert with_rule.floor_text == with_correction.floor_text


async def test_the_provenance_records_which_sibling_actually_informed_it() -> None:
    """Tolerar a ambiguidade não é apagá-la: quem auditar precisa saber qual entrou."""
    rule, correction = sibling_passages()

    result = await use_case(ScriptedModel(FAITHFUL)).execute(
        floor=FLOOR, context=CONTEXT, passages=[correction]
    )

    assert [source.entry_id for source in result.register_sources] == [correction.entry_id]
    assert result.register_sources[0].category is CorpusCategory.VALIDATED_CORRECTION
    assert rule.entry_id not in {source.entry_id for source in result.register_sources}


# --- 3. A arbitragem torna a ordem do prompt estável --------------------------


def test_the_vocabulary_rule_comes_before_its_validated_correction() -> None:
    """A regra curta e citável primeiro; o registro de por que ela existe depois."""
    rule, correction = sibling_passages()
    assert correction.similarity < rule.similarity  # o caso fácil

    ordered = arbitrate_by_category([correction, rule])
    assert [p.entry_id for p in ordered] == [rule.entry_id, correction.entry_id]


def test_the_category_wins_even_when_similarity_says_otherwise() -> None:
    """O caso que importa: a correção pontua MAIS alto e ainda assim vem depois.

    É exatamente a situação medida no ADR 0027 — o embedder semântico pôs a
    correção validada à frente. Se a nota mandasse, o prompt mudaria ao trocar de
    embedder; como a categoria manda, não muda.
    """
    rule, _ = sibling_passages()
    louder = passage(
        "VAL-Q8",
        CorpusCategory.VALIDATED_CORRECTION,
        "Validado: nem toda extinção tem causa adaptativa.",
        similarity=0.99,
    )

    ordered = arbitrate_by_category([louder, rule])
    assert [p.entry_id for p in ordered] == [rule.entry_id, louder.entry_id]


async def test_the_prompt_is_identical_regardless_of_retrieval_order() -> None:
    """A propriedade que fecha a correção 3, afirmada sobre o prompt REAL."""
    rule, correction = sibling_passages()

    forward = ScriptedModel(FAITHFUL)
    await use_case(forward).execute(floor=FLOOR, context=CONTEXT, passages=[rule, correction])
    backward = ScriptedModel(FAITHFUL)
    await use_case(backward).execute(floor=FLOOR, context=CONTEXT, passages=[correction, rule])

    assert forward.prompts[0].user == backward.prompts[0].user


def test_the_ordering_is_total_so_two_identical_scores_do_not_flip() -> None:
    """Sem desempate por id, duas entradas empatadas dariam ordem arbitrária."""
    first = passage("VOC-002", CorpusCategory.VOCABULARY_RULE, "regra A", similarity=0.5)
    second = passage("VOC-005", CorpusCategory.VOCABULARY_RULE, "regra B", similarity=0.5)

    assert arbitrate_by_category([first, second]) == arbitrate_by_category([second, first])
