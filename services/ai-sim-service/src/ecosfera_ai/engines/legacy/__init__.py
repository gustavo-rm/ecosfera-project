"""Adaptador transitório do núcleo determinístico atual para a moldura.

Some quando os Engines científicos de M1/M2 assumirem a autoria das suas fatias.
"""

from ecosfera_ai.engines.legacy.adapter import LEGACY_ENGINE_ID, LegacySubsystemAdapter
from ecosfera_ai.engines.legacy.bridge import legacy_slice_of, planet_state_of, snapshot_of
from ecosfera_ai.engines.legacy.orchestrator import (
    FrameworkTickOrchestrator,
    build_planet_engine,
    legacy_invariants,
)

__all__ = [
    "LEGACY_ENGINE_ID",
    "FrameworkTickOrchestrator",
    "LegacySubsystemAdapter",
    "build_planet_engine",
    "legacy_invariants",
    "legacy_slice_of",
    "planet_state_of",
    "snapshot_of",
]
