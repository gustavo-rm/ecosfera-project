"""Vocabulário de evento do Climate Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

TEMPERATURE_SHIFT = "TemperatureShift"
CLIMATE_THRESHOLD_CROSSED = "ClimateThresholdCrossed"


class ClimateCauseCode(CauseCodeEnum):
    """Causas estruturadas do clima — código, nunca prosa pedagógica."""

    RADIATIVE_FORCING = "RADIATIVE_FORCING"
    ALBEDO_FEEDBACK = "ALBEDO_FEEDBACK"
