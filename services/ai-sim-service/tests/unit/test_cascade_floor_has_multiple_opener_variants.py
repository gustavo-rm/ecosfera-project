"""O piso da cascata não abre todas as frases do mesmo jeito (M6.5).

## O defeito que este arquivo fecha

O ADR 0028 previu e a medição de n=15 do M6.4 confirmou: o piso da cascata abria
TODAS as suas frases com a mesma construção — *"No ciclo N, …"*. Diante de um
bloco assim, o LLM do M6.3 devolve quase-cópia em vez de paráfrase, e uma
quase-cópia passa na fundamentação trivialmente, porque não acrescenta nada que
se possa inventar. A taxa daquele cenário media, em boa parte, **o quanto o
modelo deixou de reescrever**.

A evidência estava no log do portão de geração: das quinze amostras da cascata
com `llama3.1:8b`, as quinze começavam com a mesma frase de oito palavras, e
catorze seguiam com o mesmo início de segunda frase, variando só o verbo.

## O que se corrige, e o que NÃO se corrige

Muda a FORMA das frases da família da cascata. Não muda o que elas afirmam, nem
quais fatos entram, nem a ordem — isso é assunto do M6.0 e do M6.1, e continua
cobrado onde sempre esteve (`test_cascade_facts_identical_across_variants`).

O `T-EXTINCTION-ECOLOGICAL` fica de fora de propósito: o cenário de piso curto
já mostrava variação de verdade na medição, e mexer nele mudaria o controle
contra o qual o confundidor é comparado.
"""

from __future__ import annotations

import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain, templates

from ecosfera_ai.domain.consumers.explanation import Register

# A família da cascata: os templates que rendem as frases daquele piso.
CASCADE_FAMILY = ("T-CHAIN-ROOT", "T-CHAIN-CAUSED", "T-EXTINCTION-CATASTROPHIC")

# Quantas palavras bastam para dizer que duas frases "abrem igual". Quatro é o
# tamanho de "No ciclo {tick}," mais uma — curto o bastante para não confundir
# abertura com frase inteira, longo o bastante para que coincidir seja repetição.
OPENER_WORDS = 4


def _opener(sentence: str) -> str:
    return " ".join(sentence.split()[:OPENER_WORDS]).lower()


# --- As formas existem, e são de fato distintas -------------------------------


@pytest.mark.parametrize("template_id", CASCADE_FAMILY)
def test_each_cascade_template_has_at_least_three_forms(template_id: str) -> None:
    """Duas já quebrariam a repetição; três evitam que ela volte a cada três frases."""
    forms = templates().variants_of(template_id, Register.STANDARD)
    assert len(forms) >= 3, f"{template_id} segue em forma única — a repetição continua"


@pytest.mark.parametrize("template_id", CASCADE_FAMILY)
def test_the_forms_of_a_template_do_not_share_an_opening(template_id: str) -> None:
    """Formas que abrem igual não resolvem nada: é a abertura que repetia."""
    openers = [
        _opener(form.text) for form in templates().variants_of(template_id, Register.STANDARD)
    ]
    assert len(set(openers)) == len(openers), (
        f"{template_id} tem formas que começam igual: {openers}"
    )


@pytest.mark.parametrize("template_id", CASCADE_FAMILY)
def test_no_form_is_a_truncation_of_the_first(template_id: str) -> None:
    """Encurtar a frase reduziria a repetição sem dar mais o que reescrever.

    O objetivo é dar ao modelo superfície LEGÍTIMA de paráfrase, e uma forma
    espremida faz o contrário: ela devolve menos texto e, com menos texto, a
    quase-cópia fica ainda mais provável.
    """
    forms = templates().variants_of(template_id, Register.STANDARD)
    canonical = len(forms[0].text.split())
    for form in forms[1:]:
        assert len(form.text.split()) >= canonical * 0.8, (
            f"{template_id} forma {form.text!r} é encurtamento, e não formulação alternativa"
        )


# --- E o piso da cascata, renderizado, deixa de se repetir --------------------


def test_the_rendered_cascade_no_longer_opens_every_sentence_the_same_way() -> None:
    """O antes e o depois, no artefato que o modelo realmente recebe.

    Antes deste turno as cinco frases começavam com "no ciclo" — cinco de cinco.
    O `T-EXTINCTION-ECOLOGICAL` continua começando assim, e é escolha: ele é o
    controle da medição, e está fora do escopo deste turno.
    """
    facts = explain(list(branching_cascade())).facts
    openers = [_opener(fact.text) for fact in facts]

    assert len(facts) == 5
    assert len(set(openers)) >= 4, f"o piso ainda se repete: {openers}"
    assert sum(1 for opener in openers if opener.startswith("no ciclo")) < len(facts), (
        "toda frase ainda abre da mesma forma — a correção não chegou ao piso"
    )


def test_two_consecutive_facts_from_the_same_template_read_differently() -> None:
    """O caso que o ADR 0029 nomeou: duas `T-CHAIN-CAUSED` seguidas.

    Elas existem porque o meteoro tem mais de um efeito direto, e é a situação
    mais comum numa cascata real. Antes, saíam palavra por palavra iguais até o
    ponto em que o assunto mudava.
    """
    facts = explain(list(branching_cascade())).facts
    chained = [fact for fact in facts if fact.template_id == "T-CHAIN-CAUSED"]

    assert len(chained) == 2, "o cenário precisa mesmo ter duas para valer"
    assert _opener(chained[0].text) != _opener(chained[1].text)


def test_the_variant_is_chosen_by_the_position_of_the_sentence() -> None:
    """A regra de escolha, afirmada onde ela pode ser lida.

    Sem isto, "existem formas" e "as formas são usadas" seriam duas afirmações, e
    só a primeira estaria verificada — o renderizador poderia estar pedindo
    sempre a forma zero e o arquivo continuaria cheio de prosa que ninguém lê.
    """
    table = templates()
    facts = explain(list(branching_cascade())).facts

    for position, fact in enumerate(facts):
        forms = table.variants_of(fact.template_id, Register.STANDARD)
        assert fact.text == forms[position % len(forms)].render(dict(fact.slots))
