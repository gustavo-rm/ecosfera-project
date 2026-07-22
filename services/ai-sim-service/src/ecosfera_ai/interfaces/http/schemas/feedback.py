from __future__ import annotations

from pydantic import BaseModel, Field


class ObservationIn(BaseModel):
    variable: str = Field(examples=["co2"])
    delta: float = Field(examples=[0.2])


class ExplainRequest(BaseModel):
    planet_id: str
    observations: list[ObservationIn]
    question: str | None = None  # usado pelo tutor LLM no Inc 6


class CausalStepOut(BaseModel):
    cause: str
    effect: str
    direction: str
    rule_id: str
    explanation: str


class ExplainResponse(BaseModel):
    planet_id: str
    summary: str
    chain: list[CausalStepOut]
    grounded: bool
    source: str
