"""Fatias lidas/escritas e parâmetros do Atmosphere Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "atmosphere"

# Lê a geologia NO MESMO TICK (ela roda antes): é assim que a desgaseificação
# vira estoque sem defasagem. A biomassa vem do legado, que roda depois — logo,
# leitura defasada e declarada.
WRITES = SliceRef.ATMOSPHERE
READS: frozenset[SliceRef] = frozenset({SliceRef.GEOLOGY})
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.LEGACY})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class AtmosphereEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    reference_co2: float
    weathering_coeff: float
    carbon_uptake_coeff: float
    forcing_coefficient: float
    base_pressure: float
    co2_to_pressure: float
    forcing_bands: tuple[float, ...]
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> AtmosphereEngineParams:
    """Lê os parâmetros do YAML co-locado ao Engine."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    return AtmosphereEngineParams(
        version=int(raw["version"]),
        reference_co2=float(raw["reference_co2"]),
        weathering_coeff=float(raw["weathering_coeff"]),
        carbon_uptake_coeff=float(raw["carbon_uptake_coeff"]),
        forcing_coefficient=float(raw["forcing_coefficient"]),
        base_pressure=float(raw["base_pressure"]),
        co2_to_pressure=float(raw["co2_to_pressure"]),
        forcing_bands=tuple(float(v) for v in raw["forcing_bands"]),
        max_duration_s=float(budget.get("max_duration_s", 0.25)),
        max_events=int(budget.get("max_events", 100)),
    )
