# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Fatias e parâmetros do Biota Engine PROVISÓRIO (Spec §5.1).

Fronteira dura registrada no ADR 0013: este Engine contém **zero** evolução,
especiação, genoma, mutação ou ABM. Ele não importa `deap`, `mesa`, nem nada de
`simulation_engine/biology/` — e há contrato de import-linter que faz disso um
erro de build, não uma convenção.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "biota"

# Lê a capacidade que o Resource acabou de derivar, NO MESMO TICK (ele roda
# antes). É a única entrada: a biota consome o orçamento e não olha para a física
# diretamente — quem traduz física em orçamento é o Resource (ADR 0013).
WRITES = SliceRef.BIOTA
READS: frozenset[SliceRef] = frozenset({SliceRef.RESOURCE})
LAGGED_READS: frozenset[SliceRef] = frozenset()

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class BiotaEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    abiogenesis_capacity: float
    emergence_amount: float
    growth_rate: float
    growth_variability: float
    emergence_event_threshold: float
    collapse_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> BiotaEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    fields = {k: float(v) for k, v in raw.items() if k not in {"version", "budget"}}
    return BiotaEngineParams(
        version=int(raw["version"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 50)),
        **fields,
    )
