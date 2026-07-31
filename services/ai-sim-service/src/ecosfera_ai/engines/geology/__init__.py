"""Geology Engine — vulcanismo, relevo e a fonte de carbono (M1)."""

from ecosfera_ai.engines.geology.contracts import ENGINE_ID, GeologyEngineParams, load_params
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION, GeologyCauseCode
from ecosfera_ai.engines.geology.service import GeologyEngine

__all__ = [
    "ENGINE_ID",
    "VOLCANIC_ERUPTION",
    "GeologyCauseCode",
    "GeologyEngine",
    "GeologyEngineParams",
    "load_params",
]
