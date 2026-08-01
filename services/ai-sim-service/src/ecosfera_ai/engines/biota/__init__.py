# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Biota Engine PROVISÓRIO — biomassa agregada determinística (M2, ADR 0013)."""

from ecosfera_ai.engines.biota.contracts import (
    ENGINE_ID,
    BiotaEngineParams,
    load_params,
)
from ecosfera_ai.engines.biota.events import (
    ABIOGENESIS,
    BIOMASS_COLLAPSE,
    BiotaCauseCode,
)
from ecosfera_ai.engines.biota.service import BiotaEngine

__all__ = [
    "ABIOGENESIS",
    "BIOMASS_COLLAPSE",
    "ENGINE_ID",
    "BiotaCauseCode",
    "BiotaEngine",
    "BiotaEngineParams",
    "load_params",
]
