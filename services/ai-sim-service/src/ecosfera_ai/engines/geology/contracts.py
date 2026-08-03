"""Fatias lidas/escritas e parâmetros científicos do Geology Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "geology"

# Escreve a própria fatia. Lê a água da hidrologia para calcular a erosão —
# leitura DEFASADA porque a Hydrology roda depois na ordem do tick, então o valor
# visto é o do tick anterior. A defasagem é declarada, não presumida (ADR 0008).
# No M2 a fonte mudou de `LegacySlice.water` para `HydrologySlice`; a defasagem
# continua sendo a mesma, e por isso o comportamento não muda (ADR 0014).
WRITES = SliceRef.GEOLOGY
READS: frozenset[SliceRef] = frozenset()
# A `EventSlice` traz o supervulcanismo, lido DEFASADO (o Event roda por último).
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.HYDROLOGY, SliceRef.EVENT})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class GeologyEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1, nunca hardcoded)."""

    version: int
    tectonic_activity: float
    volcanism_baseline: float
    volcanism_decay: float
    uplift_coeff: float
    erosion_coeff: float
    # Desgaseificação: fluxo de CO2 que o vulcanismo entrega à atmosfera.
    outgassing_base: float
    supervolcanic_multiplier: float
    volcanism_sensitivity: float
    # Acima deste vulcanismo o tick conta como erupção notável (Canal B).
    eruption_threshold: float
    max_duration_s: float
    max_events: int


def load_params(path: Path = PARAMS_PATH) -> GeologyEngineParams:
    """Lê os parâmetros do YAML co-locado ao Engine."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    return GeologyEngineParams(
        version=int(raw["version"]),
        tectonic_activity=float(raw["tectonic_activity"]),
        volcanism_baseline=float(raw["volcanism_baseline"]),
        volcanism_decay=float(raw["volcanism_decay"]),
        uplift_coeff=float(raw["uplift_coeff"]),
        erosion_coeff=float(raw["erosion_coeff"]),
        outgassing_base=float(raw["outgassing_base"]),
        supervolcanic_multiplier=float(raw["supervolcanic_multiplier"]),
        volcanism_sensitivity=float(raw["volcanism_sensitivity"]),
        eruption_threshold=float(raw["eruption_threshold"]),
        max_duration_s=float(budget.get("max_duration_s", 0.25)),
        max_events=int(budget.get("max_events", 100)),
    )
