"""Ecology Engine — dinâmica trófica emergente sobre a comunidade (M3)."""

from ecosfera_ai.engines.ecology.contracts import (
    ENGINE_ID,
    EcologyEngineParams,
    load_params,
)
from ecosfera_ai.engines.ecology.events import (
    POPULATION_DECLINED,
    TROPHIC_COLLAPSE,
    EcologyCauseCode,
)
from ecosfera_ai.engines.ecology.service import EcologyEngine

__all__ = [
    "ENGINE_ID",
    "POPULATION_DECLINED",
    "TROPHIC_COLLAPSE",
    "EcologyCauseCode",
    "EcologyEngine",
    "EcologyEngineParams",
    "load_params",
]
