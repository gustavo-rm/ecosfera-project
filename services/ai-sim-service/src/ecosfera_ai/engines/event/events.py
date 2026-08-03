"""Vocabulário de evento do Event Engine (Canal B, envelope §4).

Os `cause_code` são enum e NUNCA prosa: o Engine entrega o esqueleto causal como
dado, e a frase pedagógica é do Tutor (ADR-ARCH-0002, Correção 1).
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

EVENT_FORECAST = "EventForecast"
METEOR_IMPACT = "MeteorImpact"
DROUGHT_BEGAN = "DroughtBegan"
DROUGHT_ENDED = "DroughtEnded"
WILDFIRE_IGNITED = "WildfireIgnited"
ICE_AGE_ONSET = "IceAgeOnset"
STORM_OCCURRED = "StormOccurred"
SUPERVOLCANIC_ERUPTION = "SupervolcanicEruption"


class EventCauseCode(CauseCodeEnum):
    """Causas estruturadas das ocorrências extraordinárias."""

    # O Diretor agendou: a causa é a decisão dele, não uma grandeza física.
    SCHEDULED_BY_DIRECTOR = "SCHEDULED_BY_DIRECTOR"
    # Anúncio antecipado (RF-019/020) — o aviso, não o acontecimento.
    FORECAST_ANNOUNCED = "FORECAST_ANNOUNCED"
    # O evento começou / terminou.
    EVENT_ONSET = "EVENT_ONSET"
    EVENT_SUBSIDED = "EVENT_SUBSIDED"
