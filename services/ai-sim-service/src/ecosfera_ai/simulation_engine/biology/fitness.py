"""Funções de aptidão ambiental (TASK-0049).

Este módulo é a **ponte entre a ciência determinística e a biologia emergente**:
lê o `PlanetState` produzido pelos subsistemas físicos (que ele NUNCA modifica) e
devolve o quão apto um genoma está àquele ambiente. É a tradução de "o planeta
esquentou 6 °C" em "a espécie X perdeu aptidão e caminha para a extinção".

Todas as funções são PURAS (sem RNG, sem I/O, sem estado): a mesma entrada dá
sempre a mesma aptidão. A estocasticidade da evolução vive só em `evolution.py`,
o que mantém a fronteira determinístico × IA auditável (Dossiê §8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ecosfera_ai.simulation_engine.biology.genome import (
    TROPHIC_PRODUCER,
    Genome,
)
from ecosfera_ai.simulation_engine.state import PlanetState

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class FitnessParams:
    """Parâmetros das funções de aptidão (dados versionados)."""

    metabolism_cost: float  # penalidade de aptidão por unidade de metabolismo
    size_cost: float  # penalidade por corpo grande (mais recurso por indivíduo)
    energy_reference: float  # irradiância de referência para produtores
    crowding_weight: float  # peso da competição ao lotar a capacidade de suporte


def thermal_suitability(genome: Genome, state: PlanetState) -> float:
    """Aptidão térmica [0,1]: curva de sino centrada no ótimo da espécie.

    A tolerância do genoma é a largura da curva — espécies especialistas (janela
    estreita) despencam com pequenas variações; generalistas resistem mais. É o
    mecanismo pelo qual o aquecimento causa extinção.
    """
    offset = state.temperature - genome.temp_optimum
    return math.exp(-((offset / max(genome.temp_tolerance, _EPS)) ** 2))


def water_suitability(genome: Genome, state: PlanetState) -> float:
    """Aptidão hídrica [0,1]: satura quando há água suficiente para a espécie."""
    if genome.water_need <= 0.0:
        return 1.0
    return min(1.0, state.water / genome.water_need)


def energy_suitability(genome: Genome, state: PlanetState, params: FitnessParams) -> float:
    """Disponibilidade energética [0,1].

    Só os produtores dependem diretamente da irradiância; consumidores obtêm
    energia da cadeia trófica, resolvida no modelo ecológico (`ecology.py`).
    """
    if genome.trophic_class > TROPHIC_PRODUCER:
        return 1.0
    if params.energy_reference <= 0.0:
        return 1.0
    return min(1.0, state.solar_flux / params.energy_reference)


def maintenance_penalty(genome: Genome, params: FitnessParams) -> float:
    """Custo de manutenção [0,1]: corpo grande e metabolismo alto custam caro."""
    cost = params.metabolism_cost * genome.metabolism + params.size_cost * genome.size
    return 1.0 / (1.0 + max(0.0, cost))


def crowding_penalty(occupancy: float, params: FitnessParams) -> float:
    """Penalidade por competição: lotar a capacidade de suporte reduz a aptidão.

    `occupancy` é a fração da capacidade já ocupada pelas espécies vivas.
    """
    return 1.0 / (1.0 + params.crowding_weight * max(0.0, occupancy))


def environmental_fitness(
    genome: Genome,
    state: PlanetState,
    params: FitnessParams,
    *,
    occupancy: float = 0.0,
) -> float:
    """Aptidão total [0,1] de um genoma no ambiente determinístico atual.

    Produto dos fatores limitantes (lei do mínimo de Liebig, em versão suave):
    basta um fator ir a zero — frio extremo, seca — para a espécie inviabilizar,
    o que é o comportamento ecológico esperado.
    """
    return (
        thermal_suitability(genome, state)
        * water_suitability(genome, state)
        * energy_suitability(genome, state, params)
        * maintenance_penalty(genome, params)
        * crowding_penalty(occupancy, params)
    )
