"""Recurso puro: de estado físico para orçamento biológico.

## Fenômeno modelado

Este Engine responde a uma pergunta só: **quanta vida este planeta comporta?**
A resposta é um orçamento — a `carrying_capacity` — e a biologia gasta dentro
dele sem nunca escrever de volta (ADR 0006).

**Lei do mínimo (Liebig, 1840).** O crescimento não é limitado pela soma dos
nutrientes, e sim pelo **mais escasso** em relação à sua demanda. Um oceano
farto de nitrogênio e sem fósforo não sustenta mais vida do que o fósforo
permite. É por isso que os macronutrientes entram por `min(...)` e não por média:

    limitante = min(N/demanda_N, P/demanda_P, S/demanda_S)

> Liebig, J. von (1840). *Die organische Chemie in ihrer Anwendung auf
> Agricultur und Physiologie.* — a formulação original da lei do mínimo.

**Habitabilidade multiplicativa.** Os quatro fatores (temperatura, água,
nutriente, energia) MULTIPLICAM-SE, e não se somam. A diferença é física: um
fator nulo zera a habitabilidade, porque não existe vida sem água por mais
perfeita que seja a temperatura. Uma soma permitiria compensar a ausência de um
recurso com o excesso de outro, que é justamente o que a lei do mínimo nega.

Os termos de temperatura e água são os do subsistema `life` determinístico, sem
alteração de valor: a gaussiana térmica em torno do ótimo e a saturação hídrica
(ADR 0013). Os termos de nutriente e energia são novos do M2 — é o que o
Resource Engine acrescenta ao converter física em orçamento.
"""

from __future__ import annotations

import math

from ecosfera_ai.engines.resource.contracts import ResourceEngineParams

_EPS = 1e-9


def water_available(ocean: float, freshwater: float, params: ResourceEngineParams) -> float:
    """Água biologicamente utilizável: a doce inteira, a salgada em parte."""
    return max(0.0, freshwater) + params.ocean_accessibility * max(0.0, ocean)


def limiting_nutrient(
    nitrogen: float, phosphorus: float, sulfur: float, params: ResourceEngineParams
) -> float:
    """Fração do elemento MAIS ESCASSO frente à sua demanda (lei do mínimo)."""
    return min(
        max(0.0, nitrogen) / max(params.nitrogen_demand, _EPS),
        max(0.0, phosphorus) / max(params.phosphorus_demand, _EPS),
        max(0.0, sulfur) / max(params.sulfur_demand, _EPS),
    )


def nutrients_available(
    nutrients: float,
    nitrogen: float,
    phosphorus: float,
    sulfur: float,
    params: ResourceEngineParams,
) -> float:
    """Estoque de nutrientes efetivamente aproveitável, limitado pelo mais escasso."""
    limit = min(1.0, limiting_nutrient(nitrogen, phosphorus, sulfur, params))
    return max(0.0, nutrients) * limit


def energy_available(solar_flux: float, params: ResourceEngineParams) -> float:
    """Parcela da irradiância incidente que vira energia biologicamente útil."""
    return params.energy_conversion * max(0.0, solar_flux)


def _saturating(value: float, requirement: float) -> float:
    """Aptidão [0,1] de um recurso: cresce até saturar no requisito."""
    if requirement <= 0.0:
        return 1.0
    return min(1.0, max(0.0, value) / requirement)


def thermal_suitability(temperature: float, params: ResourceEngineParams) -> float:
    """Aptidão térmica: gaussiana em torno do ótimo (idêntica ao `life`)."""
    offset = (temperature - params.optimal_temperature) / params.temperature_tolerance
    return math.exp(-(offset**2))


def habitability(
    temperature: float,
    water: float,
    nutrients: float,
    energy: float,
    params: ResourceEngineParams,
) -> float:
    """Índice [0,1] de aptidão do ambiente à vida — produto dos quatro fatores.

    Multiplicativo de propósito: um fator nulo zera o resultado, porque nenhum
    excesso compensa um recurso ausente (lei do mínimo).
    """
    return (
        thermal_suitability(temperature, params)
        * _saturating(water, params.water_requirement)
        * _saturating(nutrients, params.nutrient_requirement)
        * _saturating(energy, params.energy_requirement)
    )


def carrying_capacity(habitability_index: float, params: ResourceEngineParams) -> float:
    """Orçamento biológico do planeta, em unidades de biomassa.

    É o ÚNICO acoplamento entre a camada determinística e a biologia: o Biota
    (M2, provisório) e a evolução emergente (M3) consomem esta capacidade e nunca
    escrevem de volta — por isso a física continua reproduzível bit-a-bit com a
    biologia ligada ou desligada (ADR 0006).
    """
    return params.max_carrying_capacity * max(0.0, habitability_index)


def consumption(biomass: float, params: ResourceEngineParams) -> float:
    """Recurso retirado pela biomassa existente neste tick."""
    return params.consumption_per_biomass * max(0.0, biomass)
