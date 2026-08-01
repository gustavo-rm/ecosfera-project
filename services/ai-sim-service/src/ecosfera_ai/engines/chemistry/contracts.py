"""Fatias e parâmetros do Chemistry Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "chemistry"

# Lê a geologia no MESMO tick (intemperismo). Atmosfera e hidrologia rodam
# DEPOIS, então são leituras defasadas e declaradas: o fluxo ar<->oceano deste
# tick usa o CO2 atmosférico do tick anterior. É essa defasagem que quebra o
# ciclo chemistry<->atmosphere sem perder o acoplamento (ADR 0012).
WRITES = SliceRef.CHEMISTRY
READS: frozenset[SliceRef] = frozenset({SliceRef.GEOLOGY})
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.ATMOSPHERE, SliceRef.HYDROLOGY})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class ChemistryEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    solubility: float
    reference_co2: float
    ocean_carbon_capacity: float
    burial_coeff: float
    weathering_nutrient_yield: float
    nutrient_recycling: float
    nitrogen_yield: float
    phosphorus_yield: float
    sulfur_yield: float
    element_burial: float
    reference_ph: float
    ph_sensitivity: float
    reference_ocean_carbon: float
    acidification_threshold: float
    nutrient_depletion_threshold: float
    carbon_tolerance: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> ChemistryEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    fields = {k: float(v) for k, v in raw.items() if k not in {"version", "budget"}}
    return ChemistryEngineParams(
        version=int(raw["version"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 50)),
        **fields,
    )
