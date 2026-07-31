"""Fatias lidas/escritas e parâmetros do Climate Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "climate"

# Lê o forçamento da atmosfera NO MESMO TICK (ela roda antes). Gelo, irradiância
# e circulação oceânica ainda vivem no legado, que roda depois — leitura
# defasada e declarada (migram no M2).
WRITES = SliceRef.CLIMATE
READS: frozenset[SliceRef] = frozenset({SliceRef.ATMOSPHERE})
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.LEGACY})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class ClimateEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    insolation: float
    base_albedo: float
    ice_albedo_coeff: float
    energy_to_temp: float
    climate_sensitivity: float
    equilibrium_offset: float
    thermal_inertia: float
    weather_variability: float
    ocean_heat_uptake: float
    ocean_reference_temperature: float
    temperature_bands: tuple[float, ...]
    shift_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> ClimateEngineParams:
    """Lê os parâmetros do YAML co-locado ao Engine."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    return ClimateEngineParams(
        version=int(raw["version"]),
        insolation=float(raw["insolation"]),
        base_albedo=float(raw["base_albedo"]),
        ice_albedo_coeff=float(raw["ice_albedo_coeff"]),
        energy_to_temp=float(raw["energy_to_temp"]),
        climate_sensitivity=float(raw["climate_sensitivity"]),
        equilibrium_offset=float(raw["equilibrium_offset"]),
        thermal_inertia=float(raw["thermal_inertia"]),
        weather_variability=float(raw["weather_variability"]),
        ocean_heat_uptake=float(raw["ocean_heat_uptake"]),
        ocean_reference_temperature=float(raw["ocean_reference_temperature"]),
        temperature_bands=tuple(float(v) for v in raw["temperature_bands"]),
        shift_threshold=float(raw["shift_threshold"]),
        max_duration_s=float(budget.get("max_duration_s", 0.25)),
        max_events=int(budget.get("max_events", 100)),
    )
