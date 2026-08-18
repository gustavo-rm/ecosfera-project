"""O prefixo de onze palavras não sobrevive a este turno (M6.5).

O ADR 0029 mediu o confundidor com precisão de citação: duas frases do piso da
cascata ramificada saíam do mesmo `T-CHAIN-CAUSED` e repetiam, palavra por
palavra, o mesmo começo —

    "a queda de um meteoro veio antes e é o que explica:"

Onze palavras idênticas em frases vizinhas são o pior material possível para
pedir paráfrase. É o caso deste arquivo, e ele cobra duas coisas distintas: que
as formas alternativas EXISTAM, e que sejam formulações de verdade — não a mesma
frase com uma palavra a menos.

## Por que o mesmo teste cobra a afirmação preservada

Variar a forma é seguro exatamente na medida em que a afirmação não varia junto.
As três formas dizem que `{cause_subject}` precede `{subject}` no elo do dossiê e
que `{subject}` ocorreu pelo mecanismo dado — nem mais, nem menos. Uma forma que
perdesse o elo causal seria uma frase mais bonita afirmando menos do que o log
contém, e o M6.1 chama isso de descrição, não de explicação.
"""

from __future__ import annotations

import re

from tests.support_context import branching_cascade
from tests.support_explanation import explain, templates

from ecosfera_ai.domain.consumers.explanation import Register

CHAIN_CAUSED = "T-CHAIN-CAUSED"
SLOT = re.compile(r"\{(\w+)\}")

# O prefixo exato que o ADR 0029 citou, já renderizado.
MEASURED_PREFIX = "a queda de um meteoro veio antes e é o que explica:"


def _forms() -> tuple[str, ...]:
    return tuple(form.text for form in templates().variants_of(CHAIN_CAUSED, Register.STANDARD))


def _longest_shared_prefix(first: str, second: str) -> int:
    """Quantas palavras iniciais as duas frases têm em comum."""
    left, right = first.lower().split(), second.lower().split()
    shared = 0
    for a, b in zip(left, right, strict=False):
        if a != b:
            break
        shared += 1
    return shared


# --- As formas são mais de uma, e dizem a mesma coisa -------------------------


def test_the_construct_is_no_longer_single_form() -> None:
    assert len(_forms()) >= 3, "o template que o ADR 0029 nomeou segue com uma forma só"


def test_every_form_carries_exactly_the_same_slots() -> None:
    """Slots iguais é o que garante afirmação igual.

    Uma forma que largasse `{cause_subject}` deixaria de dizer o que veio antes —
    e a frase viraria a descrição que o M6.1 recusa. Uma que pedisse um slot novo
    exigiria do dossiê algo que ele não prometeu, e falharia em produção no
    primeiro planeta sem aquele campo.
    """
    slots = [frozenset(SLOT.findall(text)) for text in _forms()]
    assert slots.count(slots[0]) == len(slots), f"formas com slots diferentes: {slots}"
    assert slots[0] == frozenset({"tick", "cause_subject", "subject", "mechanism"})


def test_every_form_keeps_the_causal_link_explicit() -> None:
    """A palavra pode mudar; o elo, não.

    O que se cobra é que a frase continue dizendo DUAS coisas: que houve algo
    antes, e que o assunto ocorreu por um mecanismo. As três formas dizem isso
    com palavras diferentes, e nenhuma delas vira "aconteceu isto e depois
    aquilo", que é justamente a descrição sem causa.
    """
    for text in _forms():
        lowered = text.lower()
        assert "antes" in lowered or "primeiro" in lowered, (
            f"a forma {text!r} perdeu o que veio ANTES na cadeia"
        )
        assert "porque" in lowered, f"a forma {text!r} perdeu o mecanismo"


# --- E o prefixo medido some do piso ------------------------------------------


def test_the_eleven_word_prefix_appears_at_most_once_in_the_cascade() -> None:
    """O achado do ADR 0029, cobrado no artefato que o produziu."""
    summary = explain(list(branching_cascade())).summary.lower()
    assert summary.count(MEASURED_PREFIX) <= 1, (
        "o prefixo de onze palavras ainda se repete no piso da cascata"
    )


def test_the_two_neighbouring_chain_sentences_share_almost_no_opening() -> None:
    """A medida direta: quantas palavras iniciais as duas vizinhas ainda dividem.

    Antes eram onze e mais — as frases só divergiam quando o assunto mudava.
    Três é um limite frouxo de propósito: o que se quer impedir é o bloco
    repetitivo, e não que duas frases comecem ambas por uma preposição.
    """
    chained = [
        fact.text
        for fact in explain(list(branching_cascade())).facts
        if fact.template_id == CHAIN_CAUSED
    ]
    assert len(chained) == 2
    assert _longest_shared_prefix(chained[0], chained[1]) <= 3, (
        f"as duas vizinhas ainda abrem quase igual: {chained}"
    )


def test_the_shared_prefix_measure_would_catch_the_old_shape() -> None:
    """Contraprova do critério: com o piso antigo, o número era grande.

    Sem isto, o limite acima poderia estar passando por ser folgado demais em vez
    de por a repetição ter acabado. As duas frases abaixo são as que o piso
    produzia antes deste turno, copiadas do que o renderizador imprimia.
    """
    before_first = (
        "No ciclo 101, a queda de um meteoro veio antes e é o que explica: "
        "um grande incêndio aconteceu porque um evento extraordinário começou."
    )
    before_second = (
        "No ciclo 101, a queda de um meteoro veio antes e é o que explica: "
        "a mudança de temperatura aconteceu porque a quantidade de calor retida "
        "pela atmosfera mudou."
    )
    assert _longest_shared_prefix(before_first, before_second) >= 13
