"""Fatias, parâmetros e catálogo do Event Engine (Spec §5.1, §8)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.engines.event.domain import EventKind, EventProfile
from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "event"

# O Event Engine roda por ÚLTIMO (Spec §5.3). Ele lê o mundo JÁ RESOLVIDO deste
# tick para decidir se um evento cabe no contexto — leituras do mesmo tick, sem
# defasagem, porque clima, recurso e biota correm todos antes dele.
#
# A defasagem está do OUTRO lado: quem lê a `EventSlice` a lê do tick anterior,
# e declara isso em `lagged_reads`. Um evento decidido no tick N perturba o mundo
# em N+1 (ADR 0018).
WRITES = SliceRef.EVENT
READS: frozenset[SliceRef] = frozenset({SliceRef.CLIMATE, SliceRef.RESOURCE, SliceRef.BIOTA})
LAGGED_READS: frozenset[SliceRef] = frozenset()

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class EventEngineParams:
    """Ciência e ritmo como DADO versionado (Spec §5.1)."""

    version: int
    scheduling_probability: float
    quiet_ticks_after: int
    max_active_events: int
    catalog: dict[EventKind, EventProfile]
    ice_age_max_temperature: float
    drought_min_temperature: float
    wildfire_min_biomass: float
    max_duration_s: float
    max_events: int

    def profile(self, kind: EventKind) -> EventProfile:
        return self.catalog[kind]


def load_params(path: Path = PARAMS_PATH) -> EventEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    context = raw.get("context", {})

    catalog: dict[EventKind, EventProfile] = {}
    for entry in raw.get("catalog", {}).values():
        kind = EventKind(int(entry["kind"]))
        catalog[kind] = EventProfile(
            kind=kind,
            duration=int(entry["duration"]),
            decay=float(entry["decay"]),
            dust=float(entry["dust"]),
            cooling=float(entry["cooling"]),
            drought=float(entry["drought"]),
            impact=float(entry["impact"]),
            mortality=float(entry["mortality"]),
            supervolcanic=float(entry["supervolcanic"]),
            forecast_lead=int(entry["forecast_lead"]),
            weight=float(entry["weight"]),
        )

    return EventEngineParams(
        version=int(raw["version"]),
        scheduling_probability=float(raw["scheduling_probability"]),
        quiet_ticks_after=int(raw["quiet_ticks_after"]),
        max_active_events=int(raw["max_active_events"]),
        catalog=catalog,
        ice_age_max_temperature=float(context["ice_age_max_temperature"]),
        drought_min_temperature=float(context["drought_min_temperature"]),
        wildfire_min_biomass=float(context["wildfire_min_biomass"]),
        max_duration_s=float(budget.get("max_duration_s", 0.05)),
        max_events=int(budget.get("max_events", 20)),
    )
