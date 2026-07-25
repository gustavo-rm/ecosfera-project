"""Carrega os parâmetros dos subsistemas do YAML versionado (dados, não código).

Espelha `domain/feedback/rule_loader`: os parâmetros científicos vivem em
`configs/simulation_params.yaml` e são revisáveis por especialistas sem redeploy.
O campo `version` permite evoluir o esquema com rastreabilidade. Aqui também mora
a fábrica que compõe os dados no `TickOrchestrator` (padrão Strategy).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState, StateBounds
from ecosfera_ai.simulation_engine.subsystems.base import Subsystem
from ecosfera_ai.simulation_engine.subsystems.chemistry import ChemistryParams, ChemistrySubsystem
from ecosfera_ai.simulation_engine.subsystems.climate import ClimateParams, ClimateSubsystem
from ecosfera_ai.simulation_engine.subsystems.life import LifeParams, LifeSubsystem


@dataclass(frozen=True, slots=True)
class InitialState:
    """Condições iniciais do planeta (dados versionados, nunca hardcoded)."""

    temperature: float
    co2: float
    water: float
    ice_cover: float
    biomass: float
    energy: float


@dataclass(frozen=True, slots=True)
class SimulationParams:
    """Conjunto versionado de parâmetros que configuram o motor de simulação."""

    version: int
    initial_state: InitialState
    bounds: StateBounds
    climate: ClimateParams
    chemistry: ChemistryParams
    life: LifeParams


def load_params(path: Path) -> SimulationParams:
    """Lê e valida os parâmetros de simulação do YAML versionado."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    init = raw["initial_state"]
    bounds_raw = raw.get("bounds", {})
    ice_range = bounds_raw.get("ice_cover", [0.0, 1.0])
    return SimulationParams(
        version=int(raw.get("version", 1)),
        initial_state=InitialState(
            temperature=float(init["temperature"]),
            co2=float(init["co2"]),
            water=float(init["water"]),
            ice_cover=float(init["ice_cover"]),
            biomass=float(init["biomass"]),
            energy=float(init["energy"]),
        ),
        bounds=StateBounds(
            ice_cover_min=float(ice_range[0]),
            ice_cover_max=float(ice_range[1]),
            water_min=float(bounds_raw.get("water_min", 0.0)),
            co2_min=float(bounds_raw.get("co2_min", 0.0)),
            biomass_min=float(bounds_raw.get("biomass_min", 0.0)),
            energy_min=float(bounds_raw.get("energy_min", 0.0)),
        ),
        climate=ClimateParams(**_floats(raw["climate"])),
        chemistry=ChemistryParams(**_floats(raw["chemistry"])),
        life=LifeParams(**_floats(raw["life"])),
    )


def initial_state(seed: PlanetSeed, params: SimulationParams) -> PlanetState:
    """Constrói o estado inicial de um planeta a partir da semente e dos parâmetros."""
    i = params.initial_state
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
    )


def build_orchestrator(params: SimulationParams) -> TickOrchestrator:
    """Fábrica: injeta os parâmetros nos subsistemas e monta o orquestrador."""
    subsystems: list[Subsystem] = [
        ClimateSubsystem(params.climate),
        ChemistrySubsystem(params.chemistry),
        LifeSubsystem(params.life),
    ]
    return TickOrchestrator(subsystems, params.bounds)


def _floats(raw: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in raw.items()}
