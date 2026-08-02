"""Evolution Engine — seleção natural emergente, sem fitness global (M3)."""

from ecosfera_ai.engines.evolution.contracts import (
    ENGINE_ID,
    EvolutionEngineParams,
    load_params,
)
from ecosfera_ai.engines.evolution.events import (
    LIFE_EMERGED,
    SPECIATION_OCCURRED,
    SPECIES_EXTINCT,
    TRAIT_SHIFT,
    EvolutionCauseCode,
)
from ecosfera_ai.engines.evolution.service import EvolutionEngine

__all__ = [
    "ENGINE_ID",
    "LIFE_EMERGED",
    "SPECIATION_OCCURRED",
    "SPECIES_EXTINCT",
    "TRAIT_SHIFT",
    "EvolutionCauseCode",
    "EvolutionEngine",
    "EvolutionEngineParams",
    "load_params",
]
