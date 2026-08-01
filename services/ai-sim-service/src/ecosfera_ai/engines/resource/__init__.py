"""Resource Engine — disponibilidade de recurso e capacidade de suporte (M2)."""

from ecosfera_ai.engines.resource.contracts import (
    ENGINE_ID,
    ResourceEngineParams,
    load_params,
)
from ecosfera_ai.engines.resource.events import (
    CARRYING_CAPACITY_SHIFT,
    RESOURCE_SCARCITY,
    ResourceCauseCode,
)
from ecosfera_ai.engines.resource.service import ResourceEngine

__all__ = [
    "CARRYING_CAPACITY_SHIFT",
    "ENGINE_ID",
    "RESOURCE_SCARCITY",
    "ResourceCauseCode",
    "ResourceEngine",
    "ResourceEngineParams",
    "load_params",
]
