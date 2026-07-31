"""Física pura da atmosfera: ciclo do carbono e forçamento radiativo.

## Fenômeno modelado

**Estoque de CO2.** Um reservatório com uma fonte e dois sumidouros:

    dC/dt = desgaseificação − intemperismo(C) − absorção biótica(biomassa)

A fonte chega pronta da geologia pelo Canal A. O intemperismo é proporcional ao
próprio estoque — é o termostato de longo prazo do ciclo carbonato-silicato
(Walker, Hays & Kasting, 1981): mais CO2 → mais intemperismo → remoção maior. A
absorção biótica entra quando houver biomassa (M3); até lá o termo é nulo porque
a biomassa é zero.

**Forçamento radiativo.** Usa-se a relação logarítmica de Myhre et al. (1998),
*New estimates of radiative forcing due to well mixed greenhouse gases*,
Geophysical Research Letters 25(14):

    ΔF = α · ln(C/C₀),   α = 5.35 W/m²

Por que logarítmica e não linear: as bandas de absorção do CO2 **saturam**. Cada
duplicação do estoque acrescenta aproximadamente o MESMO forçamento (~3,7 W/m²),
não o dobro. O subsystem `climate` legado usava `coeficiente × CO2`, que não
satura e ensinaria ao aluno uma resposta climática que a física não tem — motivo
científico da troca registrado no ADR 0010.
"""

from __future__ import annotations

import math

from ecosfera_ai.engines.atmosphere.contracts import AtmosphereEngineParams

# Piso do estoque usado no logaritmo. ln(0) é -infinito: sem o piso, um planeta
# que perdesse todo o carbono produziria forçamento infinito em vez de "muito
# frio". O piso é numérico, não físico, e por isso mora aqui e não no YAML.
_CO2_FLOOR = 1e-6


def carbon_sinks(co2: float, biomass: float, params: AtmosphereEngineParams) -> float:
    """Remoção de CO2 no tick: intemperismo (∝ estoque) + absorção biótica."""
    weathering = params.weathering_coeff * co2
    uptake = params.carbon_uptake_coeff * biomass
    return weathering + uptake


def co2_change(co2: float, inflow: float, biomass: float, params: AtmosphereEngineParams) -> float:
    """Variação do estoque: o que entra da geologia menos o que sai."""
    return inflow - carbon_sinks(co2, biomass, params)


def radiative_forcing(co2: float, params: AtmosphereEngineParams) -> float:
    """Forçamento radiativo em W/m² relativo ao CO2 de referência (Myhre 1998)."""
    ratio = max(co2, _CO2_FLOOR) / params.reference_co2
    return params.forcing_coefficient * math.log(ratio)


def pressure(co2: float, params: AtmosphereEngineParams) -> float:
    """Pressão atmosférica: base mais a contribuição parcial do CO2."""
    return params.base_pressure + params.co2_to_pressure * co2


def forcing_band(forcing: float, params: AtmosphereEngineParams) -> int:
    """Faixa de forçamento em que o planeta está (0 = abaixo da primeira).

    Trabalhar em FAIXAS, e não em variação por tick, é o que impede a explosão de
    eventos: o Canal B registra a travessia de um patamar, não o ruído contínuo
    (ADR-ARCH-0002, Correção 2).
    """
    band = 0
    for threshold in params.forcing_bands:
        if forcing >= threshold:
            band += 1
    return band
