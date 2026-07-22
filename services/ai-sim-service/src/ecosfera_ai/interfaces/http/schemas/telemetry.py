from __future__ import annotations

from pydantic import BaseModel, Field


class TelemetryEventIn(BaseModel):
    student_id: str
    planet_id: str
    action: str = Field(examples=["intervene"])
    payload: dict[str, float | str | bool] = Field(default_factory=dict)
    consent: bool = False


class EvidenceOut(BaseModel):
    student_id: str
    competency_hint: str
    strength: float
    source_action: str
