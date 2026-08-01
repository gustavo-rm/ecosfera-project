"""Química pura: ciclos do carbono não-atmosférico, de N/P/S e do pH.

## Fenômeno modelado

**Troca ar–oceano.** O oceano absorve ou libera CO2 conforme o desequilíbrio de
pressão parcial entre ar e água — a **lei de Henry**, linearizada em torno da
referência pré-industrial:

    F = solubilidade · (pCO2_ar − pCO2_oceano) · (1 − saturação_do_oceano)

O sinal é a decisão de projeto que evita dupla contagem: `F > 0` significa que o
oceano **absorve**, e é exatamente esse número que a Atmosphere subtrai do seu
estoque. Um fluxo, dois livros, sinais opostos. A soma dos dois reservatórios só
muda pelo que entra da geologia ou sai por soterramento — e é isso que o teste
de balanço de carbono verifica.

**Acidificação.** Mais carbono dissolvido, menos pH. A relação é logarítmica
porque o pH é, por definição, o logaritmo negativo da concentração de H⁺:

    pH = pH_ref − sensibilidade · log10(C_oceano / C_ref)

Referência: Sabine et al. (2004), *The oceanic sink for anthropogenic CO2*,
Science 305, que quantifica a absorção oceânica e a queda de pH associada.

**Nutrientes e N/P/S.** Liberados pelo **intemperismo** (proporcional ao relevo
e ao vulcanismo que a Geology publica) e drenados por soterramento. É o mesmo
braço "sumidouro" do ciclo carbonato-silicato que a Atmosphere usa para o
carbono, aplicado aos demais elementos.
"""

from __future__ import annotations

import math

from ecosfera_ai.engines.chemistry.contracts import ChemistryEngineParams

_EPS = 1e-9


def ocean_partial_pressure(ocean_carbon: float, params: ChemistryEngineParams) -> float:
    """Pressão parcial equivalente do carbono dissolvido."""
    return params.reference_co2 * (ocean_carbon / max(params.reference_ocean_carbon, _EPS))


def air_sea_flux(
    atmospheric_co2: float, ocean_carbon: float, params: ChemistryEngineParams
) -> float:
    """Troca ar<->oceano. Positivo = o oceano ABSORVE da atmosfera (Henry).

    A saturação impede que um oceano cheio continue absorvendo indefinidamente —
    sem ela, o reservatório oceânico viraria um sumidouro infinito e o carbono
    atmosférico desapareceria.
    """
    gradient = atmospheric_co2 - ocean_partial_pressure(ocean_carbon, params)
    saturation = min(1.0, ocean_carbon / max(params.ocean_carbon_capacity, _EPS))
    return params.solubility * gradient * (1.0 - saturation)


def carbon_burial(ocean_carbon: float, params: ChemistryEngineParams) -> float:
    """Sequestro para o sedimento — a única SAÍDA do sistema acoplado."""
    return params.burial_coeff * max(0.0, ocean_carbon)


def ocean_ph(ocean_carbon: float, params: ChemistryEngineParams) -> float:
    """pH oceânico: cai logaritmicamente com o carbono dissolvido."""
    ratio = max(ocean_carbon, _EPS) / max(params.reference_ocean_carbon, _EPS)
    return params.reference_ph - params.ph_sensitivity * math.log10(max(ratio, _EPS))


def weathering_release(relief: float, volcanism: float, yield_coeff: float) -> float:
    """Liberação de elementos pelo intemperismo do relevo exposto."""
    return yield_coeff * max(0.0, relief) * max(0.0, volcanism)


def nutrient_change(
    nutrients: float, relief: float, volcanism: float, params: ChemistryEngineParams
) -> float:
    """Variação do estoque de nutrientes: intemperismo menos reciclagem."""
    released = weathering_release(relief, volcanism, params.weathering_nutrient_yield)
    recycled = params.nutrient_recycling * max(0.0, nutrients)
    return released - recycled


def element_change(
    stock: float,
    relief: float,
    volcanism: float,
    yield_coeff: float,
    params: ChemistryEngineParams,
) -> float:
    """Variação de N, P ou S: intemperismo menos soterramento."""
    released = weathering_release(relief, volcanism, yield_coeff)
    buried = params.element_burial * max(0.0, stock)
    return released - buried
