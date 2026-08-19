"""A progressão de era NÃO alcança a onivoria de força plena — o teto é o dado.

Esta é a guarda que fecha um risco de contenção DIFERIDA. O ADR 0030 contém a
força plena (peso do produtor 0,30) porque ela amplifica a dívida de carbono do
ADR 0020 além do teto de 60 ppm. Mas a onivoria é destravada por ERA: se a rampa
subisse até 0,30 sozinha ao chegar na `full_era`, a contenção seria só um ADIAMENTO
— a amplificação voltaria em silêncio assim que uma sessão jogasse até a era 12,
e nenhum teste de era 0 a pegaria.

## Por que ela NÃO sobe (o mecanismo, não a intenção)

A rampa é MULTIPLICATIVA sobre o dado versionado:

    peso_efetivo(era) = params.predator_diet_producer × força(era),  força ∈ [0, 1]

Logo o **teto é o próprio valor de `params.yaml`** (hoje 0,02, o default
conservador MEDIDO), e a era só interpola de 0 até ele. O valor de referência de
força plena (0,30) não está no dado: vive em comentário e em override explícito de
teste. Chegar a 0,30 exige EDITAR o dado versionado — uma decisão deliberada, que
é justamente o que a Fase 3 destrava —, nunca apenas jogar mais tempo.

Estes testes travam as duas metades: o teto vem do dado (e o dado está contido), e
nenhuma era o ultrapassa.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import generalist_strength, predator_diet
from ecosfera_ai.simulation_engine.params import load_params

ECOLOGY = ecology_params()
PARAMS = load_params(Path("configs/simulation_params.yaml"))

# O default CONSERVADOR de fábrica, medido como não-amplificante no varrido de 16
# sementes (ADR 0030). É o TETO que a progressão de era pode alcançar.
CONSERVATIVE_CEILING = 0.02
# O valor de REFERÊNCIA de força plena, BLOQUEADO pela Fase 3 (ADR 0020/0030).
# Não pode ser alcançável por progressão de era — só por mudança de dado.
BLOCKED_FULL_STRENGTH = 0.30


def test_the_versioned_ceiling_is_the_conservative_default() -> None:
    """O dado versionado carrega o teto contido — não o valor de força plena.

    Guarda de DADO: se alguém subir `predator_diet.producer` no `params.yaml` para
    a força plena sem que a Fase 3 tenha pago a dívida de carbono, é aqui que
    aparece — antes de a amplificação chegar ao horizonte longo.
    """
    assert ECOLOGY.predator_diet_producer == pytest.approx(CONSERVATIVE_CEILING), (
        f"o peso do produtor no params.yaml saiu do default conservador "
        f"({ECOLOGY.predator_diet_producer} em vez de {CONSERVATIVE_CEILING}); se foi "
        "deliberado e a Fase 3 landou, atualize este teste e o ADR 0030 junto"
    )
    assert ECOLOGY.predator_diet_producer < BLOCKED_FULL_STRENGTH, (
        "a força plena entrou no dado versionado ainda bloqueada pela Fase 3"
    )


def test_no_era_ever_exceeds_the_versioned_ceiling() -> None:
    """Nenhuma era — nem uma absurdamente distante — passa do teto do dado.

    Varre muito além da `full_era` porque o risco é justamente a era TARDIA: um
    teto que valesse só perto da `full_era` deixaria a rampa escapar depois.
    """
    weights = [predator_diet(era, ECOLOGY)[1] for era in range(0, 10_001)]
    assert max(weights) == pytest.approx(CONSERVATIVE_CEILING), (
        f"alguma era ultrapassou o teto conservador: máximo {max(weights)}"
    )
    assert max(weights) < BLOCKED_FULL_STRENGTH, (
        "a progressão de era alcançou a força plena BLOQUEADA — a contenção do "
        "ADR 0030 seria apenas um adiamento, não uma contenção"
    )


def test_at_full_era_the_weight_is_the_conservative_value_not_full_strength() -> None:
    """Na `full_era` a força é 1, e mesmo assim o peso é o conservador.

    Força 1 NÃO significa "dieta de força plena": significa "todo o teto
    versionado". É a distinção que mantém a contenção real.
    """
    full = ECOLOGY.generalist_full_era
    assert generalist_strength(full, ECOLOGY) == 1.0, "a rampa não completou na full_era"

    herbivore, producer = predator_diet(full, ECOLOGY)
    assert producer == pytest.approx(CONSERVATIVE_CEILING)
    assert producer != pytest.approx(BLOCKED_FULL_STRENGTH)
    assert herbivore + producer == pytest.approx(1.0), "os pesos deixaram de somar 1"


def test_the_ceiling_tracks_the_data_so_fase3_can_lift_it_deliberately() -> None:
    """O bloqueio é do DADO, não do código: a Fase 3 destrava editando o params.

    Prova que a contenção não é uma trava mágica no código — o mecanismo continua
    genérico. Com o dado elevado (o que a Fase 3 fará, depois de pagar a dívida de
    carbono), a mesma rampa entrega a força plena. Hoje, o dado a mantém contida.
    """
    unblocked = replace(ECOLOGY, predator_diet_producer=BLOCKED_FULL_STRENGTH)
    assert predator_diet(unblocked.generalist_full_era, unblocked)[1] == pytest.approx(
        BLOCKED_FULL_STRENGTH
    ), "a rampa deixou de acompanhar o dado — o teto virou constante no código"
    # E segue sendo a ERA que gradua: destravar o dado não retroage à era 0.
    assert predator_diet(0, unblocked) == (1.0, 0.0), "o dado elevado vazou para a era 0"


def test_a_session_past_full_era_holds_the_conservative_weight_long_horizon() -> None:
    """Uma sessão REAL que atravessa a `full_era` segue no peso conservador.

    Verificado, não presumido (é o que o fecho da Fase 1 exigia). A sessão avança
    eras como o jogo avança, cruza a `full_era` bem dentro do horizonte válido, e
    o peso em jogo no fim continua o conservador — de modo que a estabilidade
    medida em `test_long_horizon_stability_not_worsened` é a DESTE regime, e não a
    de um planeta que nunca destravou a onivoria.
    """
    from tests.integration.test_long_horizon_stability_not_worsened import (
        CO2_AMPLITUDE_BOUND,
        DEFAULT,
        VALID_GAME_HORIZON,
        _advancing_trail,
        _settled_co2_amplitude,
    )

    trail = _advancing_trail(DEFAULT, ticks=VALID_GAME_HORIZON, seed=5)
    eras = [snapshot.era for snapshot in trail]
    full = DEFAULT.generalist_full_era

    assert max(eras) > full, (
        f"a sessão nem chegou à full_era ({max(eras)} <= {full}): o teste seria vazio"
    )
    ticks_at_full = sum(1 for era in eras if era >= full)
    assert ticks_at_full > VALID_GAME_HORIZON // 2, (
        "a maior parte do horizonte precisa rodar COM a onivoria destravada, "
        f"senão o horizonte longo não a mediu (só {ticks_at_full} ticks)"
    )
    assert predator_diet(max(eras), DEFAULT)[1] == pytest.approx(CONSERVATIVE_CEILING), (
        "o peso escapou do teto conservador no fim de uma sessão longa"
    )
    assert _settled_co2_amplitude(trail) < CO2_AMPLITUDE_BOUND, (
        "com a onivoria destravada por toda a segunda metade do horizonte, a "
        "amplitude de CO₂ passou do teto — a contenção não se sustenta"
    )
