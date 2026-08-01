"""Fatias e parâmetros do Hydrology Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "hydrology"

# Lê a temperatura do Climate NO MESMO TICK (ele roda antes): evaporação e degelo
# são função direta do calor recém-resolvido, sem defasagem. O Climate, por sua
# vez, lê o gelo daqui com UM tick de atraso — é assim que o acoplamento
# bidirecional água<->clima se resolve sem ciclo (ADR 0012).
WRITES = SliceRef.HYDROLOGY
READS: frozenset[SliceRef] = frozenset({SliceRef.CLIMATE})
LAGGED_READS: frozenset[SliceRef] = frozenset()

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class HydrologyEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    evaporation_coeff: float
    evaporation_reference_temperature: float
    precipitation_coeff: float
    melt_coeff: float
    freeze_coeff: float
    melt_threshold: float
    freeze_threshold: float
    runoff_coeff: float
    salt_content: float
    salinity_relaxation: float
    reference_salinity: float
    reference_temperature: float
    salinity_sensitivity: float
    temperature_sensitivity: float
    tidal_forcing: float
    circulation_baseline: float
    circulation_relaxation: float
    circulation_variability: float
    ice_event_threshold: float
    conservation_tolerance: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> HydrologyEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    fields = {k: float(v) for k, v in raw.items() if k not in {"version", "budget"}}
    return HydrologyEngineParams(
        version=int(raw["version"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 50)),
        **fields,
    )
