"""Física pura do clima: balanço de energia de caixa única.

## Fenômeno modelado

O modelo mais simples que ainda é fisicamente coerente (*energy balance model*,
Budyko 1969; Sellers 1969):

    absorvida   = irradiância · (1 − albedo(gelo))
    equilíbrio  = offset + k_energia · absorvida + λ · ΔF
    dT/dt       = inércia · (equilíbrio − T) + tempo + oceano

`ΔF` é o forçamento radiativo em W/m², que chega **pronto da atmosfera** pelo
Canal A. λ é a sensibilidade climática em °C por W/m². O clima não recalcula o
efeito estufa — se recalculasse, o CO2 teria dois donos (ADR 0010).

O **albedo do gelo** é a retroalimentação positiva clássica: gelo reflete, o
planeta esfria, forma-se mais gelo. Fica explícita porque é um dos raciocínios
que o aluno precisa reconstruir.

O **sequestro de calor oceânico** veio do subsystem `ocean`: a circulação
termohalina leva calor da superfície para o fundo, amortecendo a resposta. É
retroalimentação negativa. Mudou de dono, não de física — `temperature` precisa
de um escritor único.
"""

from __future__ import annotations

from ecosfera_ai.engines.climate.contracts import ClimateEngineParams


def albedo(ice_cover: float, params: ClimateEngineParams) -> float:
    """Refletividade planetária: base mais a contribuição da criosfera."""
    return params.base_albedo + params.ice_albedo_coeff * ice_cover


def incident_flux(solar_flux: float, params: ClimateEngineParams) -> float:
    """Irradiância no topo da atmosfera, com recuo para a insolação de referência.

    O recuo permite exercitar o clima isoladamente nos testes de unidade, sem
    montar a física orbital inteira.
    """
    return solar_flux if solar_flux > 0.0 else params.insolation


def absorbed_energy(solar_flux: float, ice_cover: float, params: ClimateEngineParams) -> float:
    """Energia solar efetivamente absorvida pelo planeta."""
    return incident_flux(solar_flux, params) * (1.0 - albedo(ice_cover, params))


def equilibrium_temperature(absorbed: float, forcing: float, params: ClimateEngineParams) -> float:
    """Temperatura de equilíbrio: energia absorvida mais o forçamento da estufa."""
    return (
        params.equilibrium_offset
        + params.energy_to_temp * absorbed
        + params.climate_sensitivity * forcing
    )


def ocean_heat_flux(
    temperature: float, ocean_circulation: float, params: ClimateEngineParams
) -> float:
    """Calor retirado da superfície pela circulação — sempre amortecedor."""
    return (
        -params.ocean_heat_uptake
        * ocean_circulation
        * (temperature - params.ocean_reference_temperature)
    )


def temperature_band(temperature: float, params: ClimateEngineParams) -> int:
    """Faixa climática do planeta (0 = abaixo do primeiro limiar)."""
    band = 0
    for threshold in params.temperature_bands:
        if temperature >= threshold:
            band += 1
    return band
