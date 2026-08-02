"""Fatias e parâmetros do Evolution Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "evolution"

# Lê o ambiente já resolvido do tick: recurso (capacidade, água, nutriente,
# energia) e clima (temperatura). A pressão de predação vem da Ecology, que roda
# DEPOIS — leitura defasada e declarada, mesma técnica de quebra de ciclo do
# água<->clima do M2 (ADR 0016).
WRITES = SliceRef.BIOTA
READS: frozenset[SliceRef] = frozenset({SliceRef.RESOURCE, SliceRef.CLIMATE})
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.ECOLOGY})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class EvolutionEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    growth_rate: float
    metabolism_cost: float
    size_cost: float
    energy_reference: float
    crowding_weight: float
    predation_weight: float
    mutation_sigma: float
    reproduction_threshold: float
    speciation_threshold: float
    extinction_population: float
    abiogenesis_capacity: float
    founder_population: float
    max_species: int
    mass_mortality_threshold: float
    trait_shift_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> EvolutionEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    fields = {k: float(v) for k, v in raw.items() if k not in {"version", "budget", "max_species"}}
    return EvolutionEngineParams(
        version=int(raw["version"]),
        max_species=int(raw["max_species"]),
        max_duration_s=float(budget.get("max_duration_s", 0.10)),
        max_events=int(budget.get("max_events", 100)),
        **fields,
    )
