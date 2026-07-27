"""Subsistema de física: órbita, gravidade e radiação incidente.

Integra a órbita do planeta em torno da estrela com **velocity Verlet**, um
integrador simplético: ao contrário de Euler, ele conserva a energia orbital ao
longo de milhares de passos (a órbita não decai nem escapa), o que é condição
para uma simulação estável e reprodutível (RF-023).

A entrega deste subsistema para o resto do motor é a **irradiância incidente**
(`solar_flux`), que cai com o quadrado da distância à estrela e alimenta o
balanço de energia do clima. É 100% determinístico: não consome o RNG.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class PhysicsParams:
    """Parâmetros orbitais e de radiação (dados versionados)."""

    gravitational_parameter: float  # GM da estrela (UA³/tick²)
    timestep: float  # dt de integração por tick
    luminosity: float  # luminosidade da estrela (irradiância a 1 UA)
    orbital_radius: float  # raio inicial da órbita (UA)
    eccentricity_kick: float  # fração da velocidade circular (0 = órbita circular)


class PhysicsSubsystem:
    """Estratégia de física orbital parametrizada por dados (`PhysicsParams`)."""

    name = "physics"

    def __init__(self, params: PhysicsParams) -> None:
        self._p = params

    def _acceleration(self, x: float, y: float) -> tuple[float, float]:
        """Aceleração gravitacional newtoniana apontando para a estrela na origem."""
        r2 = x * x + y * y
        r = math.sqrt(r2)
        if r <= 0.0:
            return (0.0, 0.0)
        factor = -self._p.gravitational_parameter / (r2 * r)
        return (factor * x, factor * y)

    def solar_flux_at(self, x: float, y: float) -> float:
        """Irradiância recebida: lei do inverso do quadrado da distância."""
        r2 = x * x + y * y
        if r2 <= 0.0:
            return 0.0
        return self._p.luminosity / r2

    def orbital_energy(self, state: PlanetState) -> float:
        """Energia orbital específica (cinética + potencial), invariante do Verlet."""
        r = math.hypot(state.orbital_x, state.orbital_y)
        kinetic = 0.5 * (state.orbital_vx**2 + state.orbital_vy**2)
        potential = -self._p.gravitational_parameter / r if r > 0.0 else 0.0
        return kinetic + potential

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        dt = self._p.timestep
        x, y = state.orbital_x, state.orbital_y
        vx, vy = state.orbital_vx, state.orbital_vy

        # Velocity Verlet: meio passo de velocidade -> passo de posição -> meio passo.
        ax, ay = self._acceleration(x, y)
        new_x = x + vx * dt + 0.5 * ax * dt * dt
        new_y = y + vy * dt + 0.5 * ay * dt * dt
        new_ax, new_ay = self._acceleration(new_x, new_y)
        new_vx = vx + 0.5 * (ax + new_ax) * dt
        new_vy = vy + 0.5 * (ay + new_ay) * dt

        return StateDelta(
            d_orbital_x=new_x - x,
            d_orbital_y=new_y - y,
            d_orbital_vx=new_vx - vx,
            d_orbital_vy=new_vy - vy,
            d_solar_flux=self.solar_flux_at(new_x, new_y) - state.solar_flux,
        )
