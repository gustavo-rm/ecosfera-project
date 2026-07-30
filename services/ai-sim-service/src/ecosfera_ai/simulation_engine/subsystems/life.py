"""Subsistema de vida: surgimento e crescimento logístico básico.

Sem AG/ABM (adiados para os Inc 3/4): a vida é um estoque agregado de biomassa
que só surge quando há água e temperatura viáveis (abiogênese) e então cresce de
forma logística até a capacidade de suporte modulada pela habitabilidade. É a
versão determinística mínima que fecha o acoplamento clima -> química -> vida.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class LifeParams:
    """Parâmetros da dinâmica de vida (dados versionados)."""

    optimal_temperature: float
    temperature_tolerance: float
    water_requirement: float
    abiogenesis_threshold: float
    emergence_amount: float
    carrying_capacity: float
    growth_rate: float
    growth_variability: float


class LifeSubsystem:
    """Estratégia de vida parametrizada por dados (`LifeParams`)."""

    name = "life"

    def __init__(self, params: LifeParams) -> None:
        self._p = params

    def habitability(self, state: PlanetState) -> float:
        """Índice [0,1] de aptidão do ambiente à vida (temperatura x água)."""
        temp_offset = state.temperature - self._p.optimal_temperature
        temp_term = temp_offset / self._p.temperature_tolerance
        temp_suitability = math.exp(-(temp_term**2))
        if self._p.water_requirement > 0.0:
            water_suitability = min(1.0, state.water / self._p.water_requirement)
        else:
            water_suitability = 1.0
        return temp_suitability * water_suitability

    def carrying_capacity(self, state: PlanetState) -> float:
        """Capacidade de suporte biótica do ambiente, em unidades de biomassa.

        Publicada de propósito: é o ÚNICO acoplamento entre a camada
        determinística e a biologia emergente do Inc 3 (ADR 0006). O motor de
        evolução/ecologia consome esta capacidade como orçamento e distribui
        espécies DENTRO dela, sem jamais escrever no `PlanetState` — por isso a
        camada determinística continua bit-a-bit reproduzível com a biologia
        ligada ou desligada.
        """
        return self._p.carrying_capacity * self.habitability(state)

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        h = self.habitability(state)
        biomass = state.biomass

        # Abiogênese: a vida só surge com habitabilidade acima do limiar (RF-014).
        emergence = (
            self._p.emergence_amount
            if biomass <= 0.0 and h >= self._p.abiogenesis_threshold
            else 0.0
        )

        # Crescimento logístico modulado pela habitabilidade; ambiente inviável
        # (capacidade nula) leva a vida existente ao declínio.
        capacity = self._p.carrying_capacity * h
        if capacity > 0.0:
            growth = self._p.growth_rate * biomass * (1.0 - biomass / capacity)
        else:
            growth = -self._p.growth_rate * biomass

        # Estocasticidade demográfica: proporcional à população, para que a
        # abiogênese "pegue" (ruído desprezível perto de zero) e a variação cresça
        # com a biomassa — trajetórias ainda divergem por semente via o clima.
        noise = float(rng.normal(0.0, self._p.growth_variability)) * biomass
        return StateDelta(d_biomass=emergence + growth + noise)
