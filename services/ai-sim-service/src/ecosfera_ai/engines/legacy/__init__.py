"""Adaptador transitório do que ainda não virou Engine, e a montagem do M1.

Some quando hidrologia, astronomia e biota tiverem seus próprios Engines (M2/M3).
"""

from ecosfera_ai.engines.legacy.adapter import LEGACY_ENGINE_ID, LegacySubsystemAdapter
from ecosfera_ai.engines.legacy.bridge import legacy_slice_of, planet_state_of, snapshot_of
from ecosfera_ai.engines.legacy.orchestrator import (
    FrameworkTickOrchestrator,
    build_legacy_orchestrator,
    build_planet_engine,
    m1_invariants,
    reduced_params,
)

__all__ = [
    "LEGACY_ENGINE_ID",
    "FrameworkTickOrchestrator",
    "LegacySubsystemAdapter",
    "build_legacy_orchestrator",
    "build_planet_engine",
    "legacy_slice_of",
    "m1_invariants",
    "planet_state_of",
    "reduced_params",
    "snapshot_of",
]
