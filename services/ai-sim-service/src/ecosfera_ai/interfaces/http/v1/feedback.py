from __future__ import annotations

from fastapi import APIRouter, Depends

from ecosfera_ai.application.feedback.explain_causal import ExplainCausalUseCase
from ecosfera_ai.core.observability import feedback_requests
from ecosfera_ai.domain.feedback.models import Observation
from ecosfera_ai.interfaces.http.deps import get_explain_use_case
from ecosfera_ai.interfaces.http.schemas.feedback import (
    CausalStepOut,
    ExplainRequest,
    ExplainResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain", response_model=ExplainResponse)
async def explain(
    req: ExplainRequest,
    uc: ExplainCausalUseCase = Depends(get_explain_use_case),
) -> ExplainResponse:
    """Explicação causal (RF-033/039). MVP: regras determinísticas. Inc 6: LLM+RAG."""
    obs = [Observation(variable=o.variable, delta=o.delta) for o in req.observations]
    result = uc.execute(req.planet_id, obs)
    feedback_requests.labels(source=result.source).inc()
    return ExplainResponse(
        planet_id=result.planet_id,
        summary=result.summary,
        chain=[
            CausalStepOut(
                cause=s.cause,
                effect=s.effect,
                direction=s.direction.value,
                rule_id=s.rule_id,
                explanation=s.explanation,
            )
            for s in result.chain
        ],
        grounded=result.grounded,
        source=result.source,
    )
