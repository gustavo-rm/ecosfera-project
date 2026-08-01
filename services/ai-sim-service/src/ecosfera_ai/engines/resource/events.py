"""Vocabulário de evento do Resource Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

CARRYING_CAPACITY_SHIFT = "CarryingCapacityShift"
RESOURCE_SCARCITY = "ResourceScarcity"


class ResourceCauseCode(CauseCodeEnum):
    """Causas estruturadas do recurso — código, nunca prosa pedagógica."""

    HABITABILITY_GAIN = "HABITABILITY_GAIN"
    HABITABILITY_LOSS = "HABITABILITY_LOSS"
    WATER_SHORTAGE = "WATER_SHORTAGE"
    NUTRIENT_SHORTAGE = "NUTRIENT_SHORTAGE"
    ENERGY_SHORTAGE = "ENERGY_SHORTAGE"
