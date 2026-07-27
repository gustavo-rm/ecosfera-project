"""Subsistema de oceano: ciclo da água, salinidade e circulação termohalina.

Três processos acoplados:

1. **Ciclo da água fechado.** Na média global a evaporação retorna como
   precipitação, então o oceano não cria nem destrói água — quem move água entre
   os estoques (gelo <-> líquido) é a química. Isso preserva a conservação
   aproximada da hidrosfera, invariante verificada nos testes.
2. **Salinidade como concentração.** O sal é conservado; a salinidade é a razão
   entre esse sal e a água líquida disponível. Degelo dilui o oceano, congelamento
   o concentra — acoplamento direto com a química.
3. **Circulação termohalina.** Movida pelo contraste de densidade: água fria e
   salgada afunda e fortalece a circulação; o aquecimento a enfraquece. As marés
   das luas somam uma mistura mecânica constante. A circulação, por sua vez,
   sequestra calor da superfície — retroalimentação negativa sobre o clima, que
   por isso roda ANTES do oceano na ordem do tick.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class OceanParams:
    """Parâmetros de hidrologia e circulação oceânica (dados versionados)."""

    salt_content: float  # massa de sal conservada no oceano
    salinity_relaxation: float  # velocidade de reequilíbrio da salinidade
    reference_salinity: float  # salinidade de referência da circulação
    reference_temperature: float  # °C de referência da circulação
    salinity_sensitivity: float  # quanto o sal fortalece a circulação
    temperature_sensitivity: float  # quanto o calor enfraquece a circulação
    tidal_forcing: float  # mistura mecânica das marés (luas)
    circulation_baseline: float  # circulação de repouso
    circulation_relaxation: float  # velocidade de reequilíbrio da circulação
    circulation_variability: float  # desvio-padrão do ruído de mistura
    heat_uptake: float  # calor retirado da superfície pela circulação


class OceanSubsystem:
    """Estratégia de oceano parametrizada por dados (`OceanParams`)."""

    name = "ocean"

    def __init__(self, params: OceanParams) -> None:
        self._p = params

    def target_salinity(self, state: PlanetState) -> float:
        """Salinidade de equilíbrio: sal conservado diluído na água líquida."""
        return self._p.salt_content / max(state.water, _EPS)

    def target_circulation(self, state: PlanetState) -> float:
        """Circulação de equilíbrio pelo contraste de densidade + marés."""
        salt_term = self._p.salinity_sensitivity * (state.salinity - self._p.reference_salinity)
        heat_term = self._p.temperature_sensitivity * (
            state.temperature - self._p.reference_temperature
        )
        return self._p.circulation_baseline + salt_term - heat_term + self._p.tidal_forcing

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        d_salinity = self._p.salinity_relaxation * (self.target_salinity(state) - state.salinity)

        mixing_noise = float(rng.normal(0.0, self._p.circulation_variability))
        circulation_gap = self.target_circulation(state) - state.ocean_circulation
        d_circulation = self._p.circulation_relaxation * circulation_gap + mixing_noise

        # Sequestro de calor: proporcional à circulação e ao desvio térmico.
        d_temperature = (
            -self._p.heat_uptake
            * state.ocean_circulation
            * (state.temperature - self._p.reference_temperature)
        )

        return StateDelta(
            d_temperature=d_temperature,
            d_salinity=d_salinity,
            d_ocean_circulation=d_circulation,
        )
