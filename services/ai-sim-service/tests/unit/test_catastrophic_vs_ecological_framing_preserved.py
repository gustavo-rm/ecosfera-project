"""A distinção do ADR 0019 não colapsa — afirmada como INVARIANTE, não como igualdade.

## A mudança de método, que é própria deste marco

Todo marco anterior testou por igualdade: mesma entrada, mesma saída, byte a byte.
Era possível porque tudo era determinístico, e era a forma mais forte de
afirmação disponível.

Com um modelo generativo no caminho, essa forma deixa de existir. Duas execuções
com a mesma entrada produzem textos diferentes, e nenhum dos dois é o "certo".
O que resta — e o que passa a valer para o M6.3 e o M6.4 — é afirmar
PROPRIEDADES que precisam valer para toda saída, qualquer que seja o texto:

  * o que o piso chama de catastrófico não vira falha de adaptação;
  * o que o piso chama de ecológico não vira catástrofe;
  * nenhuma saída ordena espécies por superioridade.

Aqui as N gerações são roteirizadas, e isso é deliberado: um modelo real
produziria as violações raramente e de modo imprevisível, e um teste que
dependesse de ele errar seria intermitente. Roteirizar as N variações é o que
torna a afirmação exaustiva em vez de sortuda. A contrapartida com um modelo de
verdade é `test_generation_over_ollama.py`, que roda no CI.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import ScriptedModel, cascade_context, spec, use_case

from ecosfera_ai.domain.consumers.factual_context import ExtinctionNature
from ecosfera_ai.domain.generation.grounding import verify_grounding

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()

# Reformulações da MESMA catástrofe: o meteoro do ciclo 100 e o que ele causou.
# Variam em vocabulário e ordem, como um modelo variaria.
FAITHFUL_CATASTROPHE = (
    "No ciclo 100, a queda de um meteoro atingiu o planeta e a comunidade desapareceu de "
    "uma vez, por mais bem adaptada que estivesse.",
    "Um meteoro caiu no ciclo 100. Um evento assim não escolhe quem sobrevive: elimina "
    "quem estava ali naquele momento.",
    "A comunidade sumiu no ciclo 100 por causa da queda de um meteoro — não por não dar "
    "conta do ambiente, mas porque um evento extremo não seleciona.",
)

# As mesmas informações, agora com a distinção COLAPSADA. Todas têm de ser pegas.
COLLAPSED_CATASTROPHE = (
    "No ciclo 100, a comunidade desapareceu porque era inferior às outras.",
    "A comunidade não era boa o suficiente para o ambiente e por isso sumiu no ciclo 100.",
    "A espécie evoluiu para resistir, mas não deu tempo, e ela era fraca demais.",
)


def _verdict(text: str) -> object:
    return verify_grounding(text, floor=FLOOR, context=CONTEXT, spec=spec())


# --- O cenário é o que se pensa que é -----------------------------------------


def test_the_dossier_really_holds_both_kinds_of_extinction() -> None:
    """Sem isto, o arquivo inteiro poderia estar afirmando sobre o cenário errado.

    A contraprova do próprio cenário: se a cascata deixasse de conter uma
    extinção catastrófica, todo teste abaixo continuaria verde sem verificar a
    distinção que existe para verificar.
    """
    natures = {extinction.nature for extinction in CONTEXT.extinctions}
    assert ExtinctionNature.CATASTROPHIC in natures
    assert len(CONTEXT.extinctions) >= 2


def test_the_floor_states_the_distinction_before_any_model_touches_it() -> None:
    """O piso já separa as duas, e é isso que o modelo tem de PRESERVAR."""
    summary = FLOOR.summary.lower()
    assert "por mais bem adaptada" in summary
    assert "não escolhe quem sobrevive" in summary


# --- A invariante, sobre N gerações -------------------------------------------


@pytest.mark.parametrize("generation", FAITHFUL_CATASTROPHE)
def test_a_faithful_reframing_passes_however_it_is_worded(generation: str) -> None:
    """Três textos distintos, todos fiéis: nenhum é reprovado por ser diferente.

    É a metade que impede o portão de virar um teste de igualdade disfarçado.
    """
    verdict = _verdict(generation)
    assert verdict.passed, verdict.reasons


@pytest.mark.parametrize("generation", COLLAPSED_CATASTROPHE)
def test_collapsing_the_distinction_is_refused_however_it_is_worded(generation: str) -> None:
    """A catástrofe narrada como fracasso da comunidade — a concepção a desfazer.

    É o erro que a plataforma inteira existe para não ensinar, e o que o torna
    perigoso é soar como uma explicação.
    """
    verdict = _verdict(generation)
    assert not verdict.passed, f"passou colapsando a distinção: {generation!r}"


async def test_the_invariant_holds_across_repeated_generations() -> None:
    """A propriedade vale para a sequência inteira, e não para uma saída sorteada.

    O modelo devolve, uma por vez, todas as variações — fiéis e colapsadas
    misturadas. Depois de cada uma, o que chegou ao aluno tem de estar limpo:
    ou a reescrita fiel, ou o piso.
    """
    replies = [*FAITHFUL_CATASTROPHE, *COLLAPSED_CATASTROPHE]
    model = ScriptedModel(*replies)
    case = use_case(model)

    delivered = []
    for _ in replies:
        result = await case.execute(floor=FLOOR, context=CONTEXT)
        delivered.append(result)

    assert len(model.prompts) == len(replies)
    for result in delivered:
        summary = result.text.lower()
        assert "era inferior" not in summary
        assert "não era boa o suficiente" not in summary
        assert "era fraca" not in summary
        if result.fell_back:
            assert result.text == FLOOR.summary

    assert any(not result.fell_back for result in delivered), "nenhuma fiel passou"
    assert any(result.fell_back for result in delivered), "nenhuma colapsada foi barrada"
