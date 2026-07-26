"""Subsistema de química: ciclos de carbono e água como estoques e fluxos.

Modela o CO2 como um estoque alimentado por desgaseificação (vulcanismo) e
drenado por intemperismo e pela absorção da vida (fotossíntese), e a troca
gelo<->água governada pela temperatura (derretimento acima do limiar,
congelamento abaixo). Mantém as variáveis em faixas físicas por construção: os
fluxos são proporcionais aos estoques disponíveis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class ChemistryParams:
    """Parâmetros dos ciclos biogeoquímicos (dados versionados)."""

    outgassing: float
    carbon_uptake_coeff: float
    weathering_coeff: float
    melt_coeff: float
    freeze_coeff: float
    melt_threshold: float
    freeze_threshold: float
    water_ice_exchange: float


class ChemistrySubsystem:
    """Estratégia de química parametrizada por dados (`ChemistryParams`)."""

    name = "chemistry"

    def __init__(self, params: ChemistryParams) -> None:
        self._p = params

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        # Carbono: fonte (desgaseificação) menos sumidouros (intemperismo + vida).
        uptake = self._p.carbon_uptake_coeff * state.biomass
        weathering = self._p.weathering_coeff * state.co2
        d_co2 = self._p.outgassing - uptake - weathering

        # Água: o gelo derrete acima do limiar; a água congela abaixo. A massa é
        # conservada trocando entre os estoques (gelo->água no degelo e vice-versa).
        melt = (
            self._p.melt_coeff
            * max(0.0, state.temperature - self._p.melt_threshold)
            * state.ice_cover
        )
        freeze = (
            self._p.freeze_coeff
            * max(0.0, self._p.freeze_threshold - state.temperature)
            * state.water
        )
        d_ice = freeze - melt
        d_water = self._p.water_ice_exchange * (melt - freeze)

        return StateDelta(d_co2=d_co2, d_ice_cover=d_ice, d_water=d_water)
