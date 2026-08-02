"""Física pura do ciclo da água: quatro reservatórios e os fluxos entre eles.

## Fenômeno modelado

A água circula entre **oceano**, **gelo**, **vapor** e **água doce**. Nenhum
fluxo cria nem destrói água — cada um apenas move massa de um reservatório para
outro, e é isso que torna a conservação uma invariante verificável (Spec §3).

    evaporação   : oceano  -> vapor      (cresce com a temperatura)
    precipitação : vapor   -> água doce
    escoamento   : doce    -> oceano
    degelo       : gelo    -> oceano     (acima do limiar térmico)
    congelamento : oceano  -> gelo       (abaixo do limiar térmico)

**Evaporação e temperatura.** A dependência real é de Clausius–Clapeyron, em que
a pressão de vapor de saturação cresce exponencialmente com a temperatura. Na
faixa habitável (~0–40 °C) a curva é bem aproximada por uma reta, e é essa
linearização que se usa aqui — explicitamente, para que o aluno veja "mais calor,
mais evaporação" sem que o modelo finja uma precisão que não tem.

**Criosfera.** Degelo e congelamento são proporcionais ao excesso térmico sobre
o limiar e ao estoque disponível. O gelo realimenta o clima pelo albedo — mas
essa seta é do Climate Engine, que lê o gelo daqui com um tick de atraso.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.engines.hydrology.contracts import HydrologyEngineParams

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class WaterFluxes:
    """Os cinco fluxos do tick, cada um movendo massa entre dois reservatórios."""

    evaporation: float = 0.0
    precipitation: float = 0.0
    runoff: float = 0.0
    melt: float = 0.0
    freeze: float = 0.0


def water_fluxes(
    ocean: float,
    ice: float,
    vapour: float,
    freshwater: float,
    temperature: float,
    params: HydrologyEngineParams,
) -> WaterFluxes:
    """Calcula os fluxos, cada um limitado pelo reservatório de origem.

    O limite por origem é o que garante a não-negatividade ANTES da invariante:
    não se evapora mais oceano do que existe, nem se derrete mais gelo do que há.
    """
    excess = temperature - params.evaporation_reference_temperature
    evaporation = min(ocean, max(0.0, params.evaporation_coeff * excess * ocean))
    precipitation = min(vapour, params.precipitation_coeff * vapour)
    runoff = min(freshwater, params.runoff_coeff * freshwater)
    melt = min(ice, params.melt_coeff * max(0.0, temperature - params.melt_threshold) * ice)
    freeze = min(
        ocean - evaporation,
        params.freeze_coeff * max(0.0, params.freeze_threshold - temperature) * ocean,
    )
    return WaterFluxes(evaporation, precipitation, runoff, melt, max(0.0, freeze))


def apply_fluxes(
    ocean: float, ice: float, vapour: float, freshwater: float, fluxes: WaterFluxes
) -> tuple[float, float, float, float]:
    """Move a massa entre reservatórios. A SOMA não muda — só a distribuição."""
    return (
        ocean - fluxes.evaporation + fluxes.runoff + fluxes.melt - fluxes.freeze,
        ice + fluxes.freeze - fluxes.melt,
        vapour + fluxes.evaporation - fluxes.precipitation,
        freshwater + fluxes.precipitation - fluxes.runoff,
    )


def total_water(ocean: float, ice: float, vapour: float, freshwater: float) -> float:
    """A grandeza conservada: a soma dos quatro reservatórios."""
    return ocean + ice + vapour + freshwater


def target_salinity(ocean: float, params: HydrologyEngineParams) -> float:
    """Salinidade de equilíbrio: sal conservado diluído na água líquida."""
    return params.salt_content / max(ocean, _EPS)


def target_circulation(salinity: float, temperature: float, params: HydrologyEngineParams) -> float:
    """Circulação de equilíbrio pelo contraste de densidade mais as marés.

    Água fria e salgada afunda e fortalece a circulação; o aquecimento a
    enfraquece. As marés das luas somam mistura mecânica constante.
    """
    salt_term = params.salinity_sensitivity * (salinity - params.reference_salinity)
    heat_term = params.temperature_sensitivity * (temperature - params.reference_temperature)
    return params.circulation_baseline + salt_term - heat_term + params.tidal_forcing


def ice_fraction(ice: float, ocean: float, vapour: float, freshwater: float) -> float:
    """Fração da hidrosfera aprisionada em gelo — o que o albedo enxerga."""
    total = total_water(ocean, ice, vapour, freshwater)
    return ice / total if total > _EPS else 0.0
