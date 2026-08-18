"""Variar a forma não pode custar o determinismo do piso (M6.5).

É a condição sem a qual este turno inteiro seria um retrocesso. O M6.1 comprou,
com um renderizador puro, a única coisa que torna a medição do M6.4 interpretável:
uma LINHA DE BASE estável. Se o piso variasse sozinho, "a saída mudou" deixaria de
distinguir modelo de renderizador, e a avaliação adversarial mediria o próprio
instrumento.

Por isso a variação é por POSIÇÃO da frase, e não por sorteio. A ordem dos
rascunhos já é determinística — o dossiê ordena por tempo de simulação —, então a
forma escolhida é uma função pura do dossiê, exatamente como o texto era antes.

`test_explanation_is_deterministic` continua sendo o guarda geral. Este arquivo
cobra o eixo NOVO: que a escolha da forma, especificamente, seja estável.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import speciation_event
from tests.support_context import branching_cascade, life_emerged
from tests.support_explanation import context_of, explain, renderer, templates

from ecosfera_ai.domain.consumers.explanation import Register
from ecosfera_ai.domain.consumers.templates import MalformedVariantError, load_templates

TRAIL = [life_emerged(era=1, tick=99), *branching_cascade()]

CHAIN_CAUSED = "T-CHAIN-CAUSED"
QUIET_PERIOD = "T-QUIET-PERIOD"


# --- Mesma fatia, mesma forma -------------------------------------------------


def test_the_same_dossier_chooses_the_same_forms_every_time() -> None:
    assert explain(TRAIL).summary == explain(TRAIL).summary


def test_the_choice_does_not_depend_on_the_arrival_order() -> None:
    """Reordenar a trilha não muda a forma escolhida.

    A escolha é pela posição na SAÍDA, e a saída é ordenada pelo tempo de
    simulação. Se ela dependesse da ordem de chegada, o piso passaria a depender
    de como os eventos foram lidos do Event Store — que é precisamente o tipo de
    acoplamento que a projeção pura do M6.0 existe para não ter.
    """
    assert explain(TRAIL).summary == explain(list(reversed(TRAIL))).summary


def test_two_template_sets_loaded_from_the_same_file_agree() -> None:
    """Determinismo de processo: nada depende de estado acumulado no objeto."""
    context = context_of(TRAIL)
    assert renderer().render(context).to_dict() == renderer().render(context).to_dict()


def test_the_facts_still_compare_equal_field_by_field() -> None:
    assert explain(TRAIL).facts == explain(list(reversed(TRAIL))).facts


def test_a_speciation_still_renders_identically_across_runs() -> None:
    """O fato mais raro, que é o que a avaliação vai querer comparar."""
    event = speciation_event()
    first = explain([event], era=event.occurred_at.era)
    second = explain([event], era=event.occurred_at.era)
    assert first.to_dict() == second.to_dict()


# --- A regra do índice, cobrada diretamente -----------------------------------


def test_the_index_wraps_instead_of_failing() -> None:
    """Uma fatia longa passa do número de formas, e isso é normal.

    O módulo é o que permite a quem chama ignorar quantas formas existem. Sem
    ele, uma era com muitos fatos estouraria o índice — e o Tutor emudeceria numa
    fatia grande, que é exatamente onde ele mais precisa falar.
    """
    table = templates()
    forms = table.variants_of(CHAIN_CAUSED, Register.STANDARD)
    for index in range(len(forms) * 3):
        assert (
            table.get(CHAIN_CAUSED, Register.STANDARD, variant=index) is forms[index % len(forms)]
        )


def test_a_single_form_template_ignores_the_index_entirely() -> None:
    """Contraprova: o comportamento anterior ao M6.5, preservado por construção.

    A maioria dos templates tem uma forma só, e para eles o índice não pode ter
    efeito algum — é isso que faz esta mudança não tocar em nenhuma família de
    frase além da cascata.
    """
    table = templates()
    assert len(table.variants_of(QUIET_PERIOD, Register.STANDARD)) == 1
    chosen = {table.get(QUIET_PERIOD, Register.STANDARD, variant=index).text for index in range(7)}
    assert len(chosen) == 1


def test_the_register_fallback_still_works_with_variants() -> None:
    """Cair para `standard` continua valendo, e cai para a forma certa.

    `T-CHAIN-CAUSED` não tem variante `simple`; pedir nesse registro tem de
    devolver a forma `standard` do MESMO índice, e não a forma zero. Sem isso, a
    costura de registro do M6.1 desfaria a variação sem avisar.
    """
    table = templates()
    for index in range(6):
        simple = table.get(CHAIN_CAUSED, Register.SIMPLE, variant=index)
        standard = table.get(CHAIN_CAUSED, Register.STANDARD, variant=index)
        assert simple is standard


# --- Numeração errada falha ALTO, e no carregamento ---------------------------


def test_a_gap_in_the_numbering_fails_at_load_time(tmp_path: Path) -> None:
    """Um `variant: 2` sem o `variant: 1` leria a frase errada, em silêncio.

    A escolha é posicional: com um buraco, a tupla teria dois elementos e a
    posição 1 traria o texto que o autor numerou como 2. A prosa que chegaria ao
    aluno seria diferente da que a revisão pedagógica aprovou, e nada avisaria.
    """
    path = tmp_path / "templates.yaml"
    path.write_text(
        "version: 1\ntemplates:\n"
        '  - {id: T-X, register: standard, variant: 0, text: "primeira"}\n'
        '  - {id: T-X, register: standard, variant: 2, text: "terceira"}\n',
        encoding="utf-8",
    )
    with pytest.raises(MalformedVariantError, match="frase errada"):
        load_templates(path)


def test_two_forms_with_the_same_number_fail_at_load_time(tmp_path: Path) -> None:
    """O defeito que sempre existiu, agora denunciado em vez de silenciado.

    Até aqui duas entradas com o mesmo `id` e `register` se sobrescreviam, e a
    segunda vencia: uma frase revisada e aprovada simplesmente não chegava ao ar.
    Com formas alternativas, escrever o mesmo id várias vezes passa a ser o jeito
    NORMAL de usar o arquivo, e o descuido deixa de ser raro.
    """
    path = tmp_path / "templates.yaml"
    path.write_text(
        "version: 1\ntemplates:\n"
        '  - {id: T-X, register: standard, variant: 0, text: "primeira"}\n'
        '  - {id: T-X, register: standard, variant: 0, text: "outra"}\n',
        encoding="utf-8",
    )
    with pytest.raises(MalformedVariantError, match="duas vezes"):
        load_templates(path)


def test_the_production_file_loads_clean() -> None:
    """Contraprova das duas guardas: elas não estão reprovando o arquivo real."""
    assert templates().version >= 1


def test_the_simple_register_of_the_cascade_is_stable_too() -> None:
    """O registro curto tem formas próprias em número próprio, e não quebra."""
    context = context_of(TRAIL)
    first = renderer().render(context, Register.SIMPLE)
    second = renderer().render(context, Register.SIMPLE)
    assert first.summary == second.summary
    assert first.summary != renderer().render(context, Register.STANDARD).summary
