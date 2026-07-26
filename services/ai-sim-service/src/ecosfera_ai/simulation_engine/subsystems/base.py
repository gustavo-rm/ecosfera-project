"""Contrato de subsistema (padrão Strategy — Dossiê §15).

Cada subsistema é uma estratégia plugável no tick: recebe o estado atual e o RNG
semeado e devolve um `StateDelta`. O orquestrador compõe os subsistemas sem
conhecer seus detalhes, o que permite adicionar/trocar processos (ex.: ecologia
por ABM no Inc 4) sem alterar as camadas superiores (ADR 0001).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


class Subsystem(Protocol):
    """Processo planetário plugável que evolui o estado em um único passo."""

    name: str

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        """Calcula a variação do estado neste tick a partir do estado atual."""
        ...
