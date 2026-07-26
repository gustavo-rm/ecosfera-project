from __future__ import annotations

from pydantic import BaseModel, Field

from ecosfera_ai.interfaces.http.schemas.feedback import ExplainResponse
from ecosfera_ai.interfaces.http.schemas.simulation import PlanetStateOut, StateDeltaOut


class EventOut(BaseModel):
    tick: int
    event_type: str = Field(examples=["life_emerged"])
    payload: dict[str, float] = Field(default_factory=dict)


class AdvanceEraResponse(BaseModel):
    era: int
    start_tick: int
    end_tick: int
    state: PlanetStateOut
    delta: StateDeltaOut
    events: list[EventOut]
    explanation: ExplainResponse


class EraSummaryOut(BaseModel):
    era: int
    start_tick: int
    end_tick: int
    event_count: int


class TimelineResponse(BaseModel):
    planet_id: str
    eras: list[EraSummaryOut]


class EraStateResponse(BaseModel):
    era: int
    state: PlanetStateOut
    # Determinismo verificado em produção: o estado reconstruído bateu com o
    # checkpoint gravado na época (RF-016/023).
    matches_checkpoint: bool
