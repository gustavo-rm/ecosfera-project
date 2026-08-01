"""Fatias e parâmetros do Ecology Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "ecology"

# Lê a comunidade que a Evolution acabou de resolver (mesmo tick) e o orçamento
# que o Resource publicou. Fecha a ordem do tick, então não precisa de defasagem.
WRITES = SliceRef.ECOLOGY
READS: frozenset[SliceRef] = frozenset({SliceRef.BIOTA, SliceRef.RESOURCE})
LAGGED_READS: frozenset[SliceRef] = frozenset()

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class EcologyEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    steps_per_tick: int
    growth_rate: float
    predation_rate: float
    conversion_efficiency: float
    mortality_rate: float
    demographic_noise: float
    min_viable_population: float
    herbivore_share: float
    predator_share: float
    max_consumer_share: float
    collapse_threshold: float
    decline_threshold: float
    max_agents: int
    max_steps: int
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> EcologyEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    ints = {"steps_per_tick", "max_agents", "max_steps"}
    fields = {k: float(v) for k, v in raw.items() if k not in ints | {"version", "budget"}}
    return EcologyEngineParams(
        version=int(raw["version"]),
        steps_per_tick=int(raw["steps_per_tick"]),
        max_agents=int(raw["max_agents"]),
        max_steps=int(raw["max_steps"]),
        max_duration_s=float(budget.get("max_duration_s", 0.25)),
        max_events=int(budget.get("max_events", 100)),
        **fields,
    )
