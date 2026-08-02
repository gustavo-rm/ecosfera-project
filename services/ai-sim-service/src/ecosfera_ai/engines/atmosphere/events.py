"""Vocabulário de evento do Atmosphere Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

GREENHOUSE_FORCING_CHANGED = "GreenhouseForcingChanged"


class AtmosphereCauseCode(CauseCodeEnum):
    """Causas estruturadas da atmosfera — código, nunca prosa pedagógica."""

    CO2_ACCUMULATION = "CO2_ACCUMULATION"
    CO2_DRAWDOWN = "CO2_DRAWDOWN"
