"""Carrega os parâmetros de simulação do YAML versionado (dados, não código).

Espelha `domain/feedback/rule_loader`: os parâmetros científicos vivem em
`configs/simulation_params.yaml` e são revisáveis por especialistas sem redeploy.
O campo `version` permite evoluir o esquema com rastreabilidade.

## O que saiu daqui no M2

A ciência de física, química, clima, geologia, oceano e vida deixou de morar
neste arquivo: cada Engine passou a carregar o próprio `params.yaml` versionado,
co-locado com o código que o consome (Spec §5.1). O que sobrou aqui é o que NÃO
pertence a um Engine — condições iniciais, faixas físicas, progressão de eras,
orçamento da moldura — mais os parâmetros da camada emergente do Inc 3, que não
é um Engine (ADR 0014).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.engines.astronomy.contracts import load_params as astronomy_params
from ecosfera_ai.engines.astronomy.domain import solar_flux_at
from ecosfera_ai.shared_kernel.engine import TickBudget
from ecosfera_ai.simulation_engine.biology.ecology import EcologyParams
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionParams
from ecosfera_ai.simulation_engine.biology.fitness import FitnessParams
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState, StateBounds


@dataclass(frozen=True, slots=True)
class InitialState:
    """Condições iniciais do planeta (dados versionados, nunca hardcoded).

    O estado orbital NÃO aparece aqui: ele é derivado dos parâmetros de física
    (órbita circular no raio configurado), evitando condições iniciais
    inconsistentes com a gravidade escolhida.
    """

    temperature: float
    co2: float
    water: float
    ice_cover: float
    biomass: float
    energy: float
    relief: float
    volcanism: float
    salinity: float
    ocean_circulation: float
    # Estoques de partida das fatias do M2. Todos com default para que um YAML
    # anterior ao M2 continue carregando (ADR 0012).
    ocean_carbon: float = 0.0
    nutrients: float = 0.0
    nitrogen: float = 0.0
    phosphorus: float = 0.0
    sulfur: float = 0.0


@dataclass(frozen=True, slots=True)
class TimelineParams:
    """Parâmetros da progressão de eras (dados versionados)."""

    era_length: int  # nº de ticks que compõem uma era


@dataclass(frozen=True, slots=True)
class SimulationParams:
    """Conjunto versionado de parâmetros que configuram o motor de simulação."""

    version: int
    initial_state: InitialState
    bounds: StateBounds
    timeline: TimelineParams
    # Camada emergente (Inc 3). Vive junto dos demais parâmetros porque a
    # biologia é subsistema de simulação, não de IA aplicada (ADR 0006), e
    # porque ela não é um Engine — não teria um `params.yaml` co-locado onde
    # morar (ADR 0014).
    fitness: FitnessParams
    evolution: EvolutionParams
    ecology: EcologyParams
    # Moldura de Engines (M0). Leitura TOLERANTE: um YAML anterior a esta seção
    # continua carregando, com o orçamento padrão do `TickBudget`.
    engine_budget: TickBudget = field(default_factory=TickBudget)


def load_params(path: Path) -> SimulationParams:
    """Lê e valida os parâmetros de simulação do YAML versionado."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    init = raw["initial_state"]
    bounds_raw = raw.get("bounds", {})
    ice_range = bounds_raw.get("ice_cover", [0.0, 1.0])
    relief_range = bounds_raw.get("relief", [0.0, 1.0])
    circulation_range = bounds_raw.get("ocean_circulation", [0.0, 1.0])
    return SimulationParams(
        version=int(raw.get("version", 1)),
        initial_state=InitialState(
            temperature=float(init["temperature"]),
            co2=float(init["co2"]),
            water=float(init["water"]),
            ice_cover=float(init["ice_cover"]),
            biomass=float(init["biomass"]),
            energy=float(init["energy"]),
            relief=float(init["relief"]),
            volcanism=float(init["volcanism"]),
            salinity=float(init["salinity"]),
            ocean_circulation=float(init["ocean_circulation"]),
            ocean_carbon=float(init.get("ocean_carbon", 0.0)),
            nutrients=float(init.get("nutrients", 0.0)),
            nitrogen=float(init.get("nitrogen", 0.0)),
            phosphorus=float(init.get("phosphorus", 0.0)),
            sulfur=float(init.get("sulfur", 0.0)),
        ),
        bounds=StateBounds(
            ice_cover_min=float(ice_range[0]),
            ice_cover_max=float(ice_range[1]),
            water_min=float(bounds_raw.get("water_min", 0.0)),
            co2_min=float(bounds_raw.get("co2_min", 0.0)),
            biomass_min=float(bounds_raw.get("biomass_min", 0.0)),
            energy_min=float(bounds_raw.get("energy_min", 0.0)),
            solar_flux_min=float(bounds_raw.get("solar_flux_min", 0.0)),
            relief_min=float(relief_range[0]),
            relief_max=float(relief_range[1]),
            volcanism_min=float(bounds_raw.get("volcanism_min", 0.0)),
            salinity_min=float(bounds_raw.get("salinity_min", 0.0)),
            ocean_circulation_min=float(circulation_range[0]),
            ocean_circulation_max=float(circulation_range[1]),
        ),
        timeline=TimelineParams(era_length=int(raw["timeline"]["era_length"])),
        fitness=FitnessParams(**_floats(raw["fitness"])),
        evolution=EvolutionParams(**_evolution_fields(raw["evolution"])),
        ecology=EcologyParams(**_ecology_fields(raw["ecology"])),
        engine_budget=_engine_budget(raw.get("engines", {})),
    )


def _engine_budget(raw: dict[str, Any]) -> TickBudget:
    """Lê o orçamento por tick da moldura, caindo no padrão quando ausente."""
    budget = raw.get("budget", {})
    default = TickBudget()
    return TickBudget(
        max_duration_s=float(budget.get("max_duration_s", default.max_duration_s)),
        max_events=int(budget.get("max_events", default.max_events)),
        max_entities=int(budget.get("max_entities", default.max_entities)),
    )


def initial_state(seed: PlanetSeed, params: SimulationParams) -> PlanetState:
    """Constrói o estado inicial de um planeta a partir da semente e dos parâmetros.

    A órbita parte de uma condição circular no raio configurado: posição (R, 0) e
    velocidade perpendicular de módulo sqrt(GM/R), opcionalmente perturbada por
    `eccentricity_kick` para gerar uma órbita elíptica (estações mais marcadas).

    Os parâmetros orbitais vêm do **Astronomy Engine**, que é o dono deles desde
    o M2. Derivar a órbita inicial de outra fonte permitiria que o estado de
    partida fosse incoerente com a gravidade que o integrador de fato usa.
    """
    i = params.initial_state
    p = astronomy_params()
    radius = p.orbital_radius
    circular_speed = math.sqrt(p.gravitational_parameter / radius) if radius > 0.0 else 0.0
    return PlanetState(
        planet_id=seed.planet_id,
        seed=seed.seed,
        tick=0,
        temperature=i.temperature,
        co2=i.co2,
        water=i.water,
        ice_cover=i.ice_cover,
        biomass=i.biomass,
        energy=i.energy,
        orbital_x=radius,
        orbital_y=0.0,
        orbital_vx=0.0,
        orbital_vy=circular_speed * (1.0 + p.eccentricity_kick),
        solar_flux=solar_flux_at(radius, 0.0, p),
        relief=i.relief,
        volcanism=i.volcanism,
        salinity=i.salinity,
        ocean_circulation=i.ocean_circulation,
        ocean_carbon=i.ocean_carbon,
        nutrients=i.nutrients,
        nitrogen=i.nitrogen,
        phosphorus=i.phosphorus,
        sulfur=i.sulfur,
    )


def _floats(raw: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in raw.items()}


# Alguns parâmetros da camada emergente são contagens (gerações, tetos), não
# grandezas contínuas: convertê-los para int mantém os tipos honestos.
_EVOLUTION_INTS = frozenset({"population_size", "generations", "tournament_size", "max_species"})
_ECOLOGY_INTS = frozenset({"steps", "max_agents", "max_steps"})


def _evolution_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return {k: (int(v) if k in _EVOLUTION_INTS else float(v)) for k, v in raw.items()}


def _ecology_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return {k: (int(v) if k in _ECOLOGY_INTS else float(v)) for k, v in raw.items()}
