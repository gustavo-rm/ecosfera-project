"""Vocabulário de evento do Ecology Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

POPULATION_DECLINED = "PopulationDeclined"
TROPHIC_COLLAPSE = "TrophicCollapse"


class EcologyCauseCode(CauseCodeEnum):
    """Causas estruturadas da ecologia — código, nunca prosa pedagógica."""

    PREDATION_PRESSURE = "PREDATION_PRESSURE"
    PREY_COLLAPSE = "PREY_COLLAPSE"
    RESOURCE_SCARCITY = "RESOURCE_SCARCITY"
