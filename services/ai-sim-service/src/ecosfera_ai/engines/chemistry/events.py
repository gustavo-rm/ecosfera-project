"""Vocabulário de evento do Chemistry Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

NUTRIENT_DEPLETION = "NutrientDepletion"
OCEAN_ACIDIFICATION = "OceanAcidification"
CARBON_FLUX_SHIFT = "CarbonFluxShift"


class ChemistryCauseCode(CauseCodeEnum):
    """Causas estruturadas da química — código, nunca prosa pedagógica."""

    CARBON_DISSOLUTION = "CARBON_DISSOLUTION"
    CARBON_OUTGASSING = "CARBON_OUTGASSING"
    NUTRIENT_EXHAUSTION = "NUTRIENT_EXHAUSTION"
