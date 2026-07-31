from __future__ import annotations

from pydantic import BaseModel, Field

from ecosfera_ai.interfaces.http.schemas.biology import BiologySummaryOut, JobRefOut
from ecosfera_ai.interfaces.http.schemas.feedback import ExplainResponse
from ecosfera_ai.interfaces.http.schemas.simulation import PlanetStateOut, StateDeltaOut


class EventOut(BaseModel):
    tick: int
    event_type: str = Field(examples=["life_emerged"])
    payload: dict[str, float | str] = Field(default_factory=dict)


class CausalLinkOut(BaseModel):
    """Um elo causa->efeito do rastro (projeção do Event Store — ADR 0011)."""

    cause_event: str
    cause_type: str
    effect_event: str
    effect_type: str
    cause_code: str


class AdvanceEraResponse(BaseModel):
    era: int
    start_tick: int
    end_tick: int
    state: PlanetStateOut
    delta: StateDeltaOut
    events: list[EventOut]
    explanation: ExplainResponse
    # Camada emergente (Inc 3). Exatamente um dos dois vem preenchido: `biology`
    # quando a fila resolve inline (200) e `job` quando é assíncrona (202).
    biology: BiologySummaryOut | None = None
    job: JobRefOut | None = None
    # Rastro causa->efeito da era, quando ela produziu ocorrências notáveis. É o
    # "como chegamos aqui" que o Tutor precisa (ADR-ARCH-0002, Pilar 4).
    causal_trace: list[CausalLinkOut] = Field(default_factory=list)
    # "events" quando a era foi narrada a partir da trilha do Canal B;
    # "state_delta" quando não houve ocorrência notável e o recuo foi acionado.
    narrated_from: str = "state_delta"


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
