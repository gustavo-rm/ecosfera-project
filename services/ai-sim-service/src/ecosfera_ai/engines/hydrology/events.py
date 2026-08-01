"""Vocabulário de evento do Hydrology Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

ICE_SHEET_CHANGED = "IceSheetChanged"
WATER_BALANCE_SHIFT = "WaterBalanceShift"


class HydrologyCauseCode(CauseCodeEnum):
    """Causas estruturadas da hidrologia — código, nunca prosa pedagógica."""

    TEMPERATURE_RISE = "TEMPERATURE_RISE"
    TEMPERATURE_FALL = "TEMPERATURE_FALL"
    PRECIPITATION_CHANGE = "PRECIPITATION_CHANGE"
