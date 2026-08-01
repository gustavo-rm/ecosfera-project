"""Fatias e parâmetros do Resource Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "resource"

# Lê as quatro fatias físicas NO MESMO TICK: todas rodam antes na ordem canônica,
# e a capacidade de suporte só faz sentido sobre o ambiente já resolvido. O
# consumo da biota vem DEFASADO porque o Biota roda depois — declarado, portanto,
# e não um ciclo escondido (ADR 0012).
WRITES = SliceRef.RESOURCE
READS: frozenset[SliceRef] = frozenset(
    {SliceRef.ASTRONOMY, SliceRef.CLIMATE, SliceRef.HYDROLOGY, SliceRef.CHEMISTRY}
)
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.BIOTA})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class ResourceEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    ocean_accessibility: float
    energy_conversion: float
    nitrogen_demand: float
    phosphorus_demand: float
    sulfur_demand: float
    optimal_temperature: float
    temperature_tolerance: float
    water_requirement: float
    nutrient_requirement: float
    energy_requirement: float
    max_carrying_capacity: float
    consumption_per_biomass: float
    capacity_event_threshold: float
    scarcity_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> ResourceEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    fields = {k: float(v) for k, v in raw.items() if k not in {"version", "budget"}}
    return ResourceEngineParams(
        version=int(raw["version"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 50)),
        **fields,
    )
