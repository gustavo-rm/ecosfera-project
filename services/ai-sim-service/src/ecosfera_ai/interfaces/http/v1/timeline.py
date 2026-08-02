from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.advance_era import AdvanceEraUseCase
from ecosfera_ai.application.simulation.replay_state import ReplayStateUseCase
from ecosfera_ai.core.observability import simulation_eras, simulation_replays
from ecosfera_ai.interfaces.http.deps import (
    get_advance_era_use_case,
    get_planet_repo,
    get_replay_state_use_case,
)
from ecosfera_ai.interfaces.http.schemas.biology import BiologySummaryOut, JobRefOut
from ecosfera_ai.interfaces.http.schemas.timeline import (
    AdvanceEraResponse,
    CausalLinkOut,
    EraStateResponse,
    EraSummaryOut,
    EventOut,
    TimelineResponse,
)
from ecosfera_ai.interfaces.http.v1.simulation import delta_out, explanation_out, state_out

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/planets/{planet_id}/advance-era", response_model=AdvanceEraResponse)
async def advance_era(
    planet_id: str,
    response: Response,
    uc: AdvanceEraUseCase = Depends(get_advance_era_use_case),
) -> AdvanceEraResponse:
    """Avança uma era completa: checkpoint append-only + cadeia causal (RF-013/016).

    Com a fila inline a biologia resolve na hora e a resposta é 200. Com o backend
    ARQ o job de evolução é enfileirado e a resposta vira 202 + referência do job,
    consultável em `/simulation/jobs/{job_id}` (ADR 0007).
    """
    outcome = await uc.execute(planet_id)  # PlanetNotFoundError -> 404 (handler)
    simulation_eras.inc()
    if outcome.job is not None:
        response.status_code = 202
    return AdvanceEraResponse(
        era=outcome.era,
        start_tick=outcome.start_tick,
        end_tick=outcome.end_tick,
        state=state_out(outcome.state),
        delta=delta_out(outcome.delta),
        events=[
            EventOut(tick=e.tick, event_type=e.event_type, payload=dict(e.payload))
            for e in outcome.events
        ],
        explanation=explanation_out(outcome.explanation),
        biology=(
            BiologySummaryOut(**outcome.biology.to_dict()) if outcome.biology is not None else None
        ),
        job=(
            JobRefOut(job_id=outcome.job.job_id, job_name=outcome.job.job_name)
            if outcome.job is not None
            else None
        ),
        causal_trace=[
            CausalLinkOut(
                cause_event=link.cause_event,
                cause_type=link.cause_type,
                effect_event=link.effect_event,
                effect_type=link.effect_type,
                cause_code=link.cause_code,
            )
            for link in outcome.causal_trace
        ],
        narrated_from=outcome.narrated_from,
    )


@router.get("/planets/{planet_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    planet_id: str,
    repo: PlanetRepository = Depends(get_planet_repo),
) -> TimelineResponse:
    """Lista as eras já fechadas do planeta e seus metadados (Dossiê §9)."""
    eras = await repo.get_timeline(planet_id)
    return TimelineResponse(
        planet_id=planet_id,
        eras=[
            EraSummaryOut(
                era=e.era,
                start_tick=e.start_tick,
                end_tick=e.end_tick,
                event_count=e.event_count,
            )
            for e in eras
        ],
    )


@router.get("/planets/{planet_id}/eras/{era}", response_model=EraStateResponse)
async def get_era_state(
    planet_id: str,
    era: int,
    uc: ReplayStateUseCase = Depends(get_replay_state_use_case),
) -> EraStateResponse:
    """Reconstrói o estado de uma era por replay determinístico (RF-016/023)."""
    outcome = await uc.execute(planet_id, era)  # EraNotFoundError -> 404 (handler)
    simulation_replays.labels(matched=str(outcome.matches_checkpoint).lower()).inc()
    return EraStateResponse(
        era=outcome.era,
        state=state_out(outcome.state),
        matches_checkpoint=outcome.matches_checkpoint,
    )
