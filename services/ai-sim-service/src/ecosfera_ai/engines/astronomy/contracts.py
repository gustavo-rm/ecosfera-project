"""Fatias e parâmetros do Astronomy Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "astronomy"

# Abre o tick e não lê ninguém: a órbita é condição de contorno externa, não
# resposta ao planeta. É por isso que a insolação pode alimentar todo o resto.
WRITES = SliceRef.ASTRONOMY
READS: frozenset[SliceRef] = frozenset()
LAGGED_READS: frozenset[SliceRef] = frozenset()

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class AstronomyEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    gravitational_parameter: float
    timestep: float
    luminosity: float
    orbital_radius: float
    eccentricity_kick: float
    insolation_shift_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> AstronomyEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    return AstronomyEngineParams(
        version=int(raw["version"]),
        gravitational_parameter=float(raw["gravitational_parameter"]),
        timestep=float(raw["timestep"]),
        luminosity=float(raw["luminosity"]),
        orbital_radius=float(raw["orbital_radius"]),
        eccentricity_kick=float(raw["eccentricity_kick"]),
        insolation_shift_threshold=float(raw["insolation_shift_threshold"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 50)),
    )
