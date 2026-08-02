"""Física pura da órbita: velocity Verlet e irradiância incidente.

## Fenômeno modelado

A órbita é integrada por **velocity Verlet**, um integrador **simplético**: ao
contrário de Euler, ele conserva a energia orbital ao longo de milhares de
passos — a órbita não decai nem escapa. Essa conservação é condição para a
simulação ser estável e reprodutível (RF-023), e é verificada em teste.

A entrega deste Engine ao resto do motor é a **irradiância incidente**, que cai
com o quadrado da distância à estrela (lei do inverso do quadrado) e alimenta o
balanço de energia do clima. É 100% determinístico: não consome o RNG.
"""

from __future__ import annotations

import math

from ecosfera_ai.engines.astronomy.contracts import AstronomyEngineParams


def acceleration(x: float, y: float, params: AstronomyEngineParams) -> tuple[float, float]:
    """Aceleração gravitacional newtoniana apontando para a estrela na origem."""
    r2 = x * x + y * y
    r = math.sqrt(r2)
    if r <= 0.0:
        return (0.0, 0.0)
    factor = -params.gravitational_parameter / (r2 * r)
    return (factor * x, factor * y)


def solar_flux_at(x: float, y: float, params: AstronomyEngineParams) -> float:
    """Irradiância recebida: lei do inverso do quadrado da distância."""
    r2 = x * x + y * y
    if r2 <= 0.0:
        return 0.0
    return params.luminosity / r2


def orbital_energy(
    x: float, y: float, vx: float, vy: float, params: AstronomyEngineParams
) -> float:
    """Energia orbital específica (cinética + potencial) — invariante do Verlet."""
    r = math.hypot(x, y)
    kinetic = 0.5 * (vx * vx + vy * vy)
    potential = -params.gravitational_parameter / r if r > 0.0 else 0.0
    return kinetic + potential


def integrate(
    x: float, y: float, vx: float, vy: float, params: AstronomyEngineParams
) -> tuple[float, float, float, float]:
    """Um passo de velocity Verlet: meio passo de v, passo de x, meio passo de v."""
    dt = params.timestep
    ax, ay = acceleration(x, y, params)
    new_x = x + vx * dt + 0.5 * ax * dt * dt
    new_y = y + vy * dt + 0.5 * ay * dt * dt
    new_ax, new_ay = acceleration(new_x, new_y, params)
    return (new_x, new_y, vx + 0.5 * (ax + new_ax) * dt, vy + 0.5 * (ay + new_ay) * dt)
