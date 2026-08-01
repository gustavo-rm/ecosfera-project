# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Dinâmica determinística da biomassa agregada — porte fiel do `life`.

## Fronteira (ADR 0013)

Este módulo é **provisório**. Contém a física determinística do subsistema `life`
e nada mais: abiogênese por limiar e crescimento logístico até a capacidade de
suporte. Não há aqui — nem pode haver — evolução, especiação, genoma, mutação ou
agentes. A biologia EMERGENTE é o M3, e vive em `simulation_engine/biology/`.

Ninguém deve construir em cima deste módulo achando que é definitivo.

## Fenômeno modelado

**Abiogênese.** A vida surge de uma vez, em quantidade fixa, quando o ambiente
cruza um limiar de viabilidade — e só quando ainda não há vida alguma.

**Crescimento logístico (Verhulst, 1838).** A biomassa cresce proporcionalmente
a si mesma e ao espaço que sobra no orçamento:

    dB/dt = r · B · (1 − B/K)

`K` é a `carrying_capacity` que o Resource Engine publica. Quando `K` é zero — um
ambiente inviável — o crescimento vira declínio à mesma taxa: a vida existente
não se sustenta.

**Ruído demográfico.** Proporcional à população, e não aditivo. Essa escolha vem
do `life` e tem uma razão: perto de zero o ruído é desprezível, então a
abiogênese "pega" em vez de ser sorteada de volta ao nada; e a variação absoluta
cresce com a biomassa, como numa população real.
"""

from __future__ import annotations

from ecosfera_ai.engines.biota.contracts import BiotaEngineParams


def emergence(biomass: float, capacity: float, params: BiotaEngineParams) -> float:
    """Biomassa semeada pela abiogênese neste tick (zero se já houver vida).

    O limiar está em unidades de capacidade porque é a capacidade que o Resource
    publica. É a mesma desigualdade do `life`, reparametrizada — ver `params.yaml`.
    """
    if biomass > 0.0:
        return 0.0
    return params.emergence_amount if capacity >= params.abiogenesis_capacity else 0.0


def logistic_growth(biomass: float, capacity: float, params: BiotaEngineParams) -> float:
    """Crescimento logístico até a capacidade; declínio se o ambiente é inviável."""
    if capacity > 0.0:
        return params.growth_rate * biomass * (1.0 - biomass / capacity)
    return -params.growth_rate * biomass


def demographic_noise(biomass: float, draw: float) -> float:
    """Ruído proporcional à biomassa — desprezível perto de zero, por construção.

    `draw` já vem sorteado com o desvio-padrão do parâmetro, e não normalizado:
    é a linha do `life` preservada tal e qual (`normal(0, σ) · biomassa`). Sortear
    normalizado e multiplicar por σ aqui daria a mesma distribuição, mas não a
    mesma sequência de bits — e a fidelidade do porte é o ponto (ADR 0013).
    """
    return draw * biomass
