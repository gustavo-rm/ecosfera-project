"""Vocabulário de evento do Astronomy Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

INSOLATION_SHIFT = "InsolationShift"


class AstronomyCauseCode(CauseCodeEnum):
    """Causas estruturadas da astronomia — código, nunca prosa pedagógica."""

    ORBITAL_ECCENTRICITY = "ORBITAL_ECCENTRICITY"
