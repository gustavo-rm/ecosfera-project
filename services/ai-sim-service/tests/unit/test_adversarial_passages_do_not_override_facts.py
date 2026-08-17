"""Passagens ESCOLHIDAS PARA ENGANAR não mudam o que a saída afirma.

O M6.3 já afirmava isto com uma passagem enganosa. Aqui a escolha é adversarial: as
passagens são desenhadas para explorar as fraquezas conhecidas do desenho, e não
apenas para estar fora de assunto.

## O que torna uma passagem adversarial neste sistema

Ela não vem de um aluno — não existe superfície de entrada livre (ver o ADR desta
rodada). Ela vem do CORPUS, e o vetor é a recuperação trazer, para um dossiê,
material que descreve mecanismo que não ocorreu ali. Três formas de fazer isso
darem errado:

  1. a passagem descreve um acontecimento concreto (meteoro, erupção) que o
     dossiê não tem — o modelo pode narrá-lo como se tivesse acontecido;
  2. a passagem carrega números, e números na prosa têm de vir do piso;
  3. a passagem afirma um mecanismo direcional ("o gás carbônico aquece o
     planeta") que é ciência correta e não é o log daquele planeta — o bug do
     M6.1, agora chegando pelo corpus em vez de por inferência do modelo.

A terceira é a mais interessante do M6.4, porque une o Task 0 ao Task B: o mesmo
erro, por outro caminho de entrada.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, cascade_context, passage, spec, use_case

from ecosfera_ai.domain.generation.grounding import verify_grounding
from ecosfera_ai.domain.rag.corpus import CorpusCategory

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()

ADVERSARIAL = (
    passage(
        "ADV-EVENTO",
        CorpusCategory.VOCABULARY_RULE,
        "Ao falar de eras glaciais, lembre que o gelo avança por milhares de anos.",
        similarity=0.97,
    ),
    passage(
        "ADV-NUMERO",
        CorpusCategory.VALIDATED_CORRECTION,
        "Validado: uma extinção em massa pode eliminar 75 por cento das espécies.",
        similarity=0.96,
    ),
    passage(
        "ADV-DIRECAO",
        CorpusCategory.VOCABULARY_RULE,
        "Mais gás carbônico no ar retém mais calor, e o planeta esquenta.",
        similarity=0.95,
    ),
    passage(
        "ADV-ESPECIACAO",
        CorpusCategory.VOCABULARY_RULE,
        "Quando populações se separam, elas se dividem em duas linhagens irmãs.",
        similarity=0.94,
    ),
)


# --- O modelo que engole a passagem é barrado, uma forma de cada vez ----------


@pytest.mark.parametrize(
    ("seduced", "expected_in_reason"),
    [
        ("O começo de uma era glacial cobriu o planeta de gelo.", "glacial"),
        ("A extinção eliminou 75 por cento das espécies daquele planeta.", "75"),
        # A cascata TEM um `TemperatureShift`, e ele é de RESFRIAMENTO (-14,0).
        # Afirmar aquecimento aqui não inventa o evento: contradiz a direção dele,
        # que é o achado mais preciso dos dois. O caso de invenção pura vive em
        # `test_co2_without_temperature_shift_not_generalized`, num dossiê sem o evento.
        ("Com mais gás carbônico, o planeta esquentou naquele ciclo.", "contradiz"),
        ("A população se dividiu em duas linhagens irmãs logo depois.", "BIO-001"),
    ],
)
async def test_a_model_that_repeats_the_passage_as_fact_is_caught(
    seduced: str, expected_in_reason: str
) -> None:
    """Cada passagem adversarial tem a sua armadilha, e todas são pegas.

    Note que a passagem é ciência correta nos quatro casos. O que a torna falsa é
    ser afirmada sobre um planeta cujo log não a contém.
    """
    result = await use_case(ScriptedModel(seduced)).execute(
        floor=FLOOR, context=CONTEXT, passages=list(ADVERSARIAL)
    )

    assert result.fell_back, f"passou repetindo a passagem: {seduced!r}"
    assert result.text == FLOOR.summary
    assert expected_in_reason in result.fallback_reason


# --- E a saída fiel não é penalizada por companhia ruim -----------------------


async def test_the_same_faithful_output_passes_with_the_adversarial_passages() -> None:
    """A passagem adversarial não contamina uma saída que não a seguiu.

    Sem isto, "passagem ruim leva a recuo" poderia estar medindo o recuo por
    causa da PASSAGEM, e não por causa do que o modelo escreveu — e o verificador
    estaria lendo o corpus, que é justamente o que um contrato de import proíbe.
    """
    faithful = "No ciclo 100, a queda de um meteoro atingiu o planeta."

    with_adversarial = await use_case(ScriptedModel(faithful)).execute(
        floor=FLOOR, context=CONTEXT, passages=list(ADVERSARIAL)
    )
    alone = await use_case(ScriptedModel(faithful)).execute(floor=FLOOR, context=CONTEXT)

    assert not with_adversarial.fell_back
    assert with_adversarial.text == alone.text
    assert with_adversarial.verdict.passed == alone.verdict.passed


def test_the_verdict_is_identical_whether_or_not_the_passages_were_retrieved() -> None:
    """A prova direta: o veredito não é função das passagens.

    `verify_grounding` nem sequer recebe passagem — a chamada abaixo é a mesma
    nos dois mundos. O contrato de import é o que garante que continue assim.
    """
    faithful = "No ciclo 100, a queda de um meteoro atingiu o planeta."
    verdict = verify_grounding(faithful, floor=FLOOR, context=CONTEXT, spec=spec())

    assert verdict.passed
    assert verdict.reasons == ()


# --- A passagem mais perigosa: a que é verdadeira em geral --------------------


async def test_a_scientifically_correct_passage_cannot_license_an_ungrounded_claim() -> None:
    """O centro do M6, num caso só.

    "Mais gás carbônico retém mais calor" é ciência correta, vem do corpus do
    projeto e tem similaridade altíssima. Nada disso autoriza a dizer que ESTE
    planeta esquentou — o log dele registra a temperatura CAINDO 14 graus depois
    do meteoro, que é o oposto do que o mecanismo geral sugeriria.

    É o caso mais claro que este marco tem de "verdadeiro em geral, falso aqui".
    """
    only_carbon = ADVERSARIAL[2]
    assert "esquenta" in only_carbon.text, "a passagem precisa mesmo afirmar o mecanismo"

    result = await use_case(
        ScriptedModel("O gás carbônico subiu e o planeta esquentou por causa disso.")
    ).execute(floor=FLOOR, context=CONTEXT, passages=[only_carbon])

    assert result.fell_back
    assert "contradiz" in result.fallback_reason
    assert "-14.0" in result.fallback_reason, "o motivo cita a variação que o log registra"
