"""Subsistema de clima: balanço de energia + efeito estufa (determinístico).

Modelo de balanço de energia de caixa única (energy balance model), o mais
simples que ainda é fisicamente coerente: a energia solar absorvida depende do
albedo (o gelo reflete mais), o CO2 adiciona forçamento radiativo (efeito estufa)
e a temperatura relaxa para o equilíbrio com inércia térmica. É a base científica
do 'CO2↑ -> temperatura↑' que o motor causal narra ao aluno (RF-013).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class ClimateParams:
    """Parâmetros do balanço de energia (dados versionados)."""

    insolation: float
    base_albedo: float
    ice_albedo_coeff: float
    greenhouse_coeff: float
    energy_to_temp: float
    equilibrium_offset: float
    thermal_inertia: float
    weather_variability: float


class ClimateSubsystem:
    """Estratégia de clima parametrizada por dados (`ClimateParams`)."""

    name = "climate"

    def __init__(self, params: ClimateParams) -> None:
        self._p = params

    def incident_flux(self, state: PlanetState) -> float:
        """Irradiância incidente no topo da atmosfera.

        Vem da física orbital (`solar_flux`) quando ela está ativa no pipeline;
        na ausência dela usa-se a insolação de referência dos parâmetros, o que
        permite exercitar o clima isoladamente nos testes de unidade.
        """
        return state.solar_flux if state.solar_flux > 0.0 else self._p.insolation

    def absorbed_energy(self, state: PlanetState) -> float:
        """Energia solar absorvida: insolação menos a parcela refletida (albedo)."""
        albedo = self._p.base_albedo + self._p.ice_albedo_coeff * state.ice_cover
        return self.incident_flux(state) * (1.0 - albedo)

    def equilibrium_temperature(self, state: PlanetState) -> float:
        """Temperatura de equilíbrio: energia absorvida + forçamento do CO2."""
        greenhouse = self._p.greenhouse_coeff * state.co2
        return (
            self._p.equilibrium_offset
            + self._p.energy_to_temp * self.absorbed_energy(state)
            + greenhouse
        )

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        absorbed = self.absorbed_energy(state)
        target = self.equilibrium_temperature(state)
        # Relaxação para o equilíbrio (inércia térmica) + variação meteorológica.
        drift = self._p.thermal_inertia * (target - state.temperature)
        weather = float(rng.normal(0.0, self._p.weather_variability))
        return StateDelta(
            d_temperature=drift + weather,
            d_energy=absorbed - state.energy,
        )
