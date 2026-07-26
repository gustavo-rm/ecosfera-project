from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.create_planet import CreatePlanetUseCase
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError, RunTickUseCase
from ecosfera_ai.core.observability import simulation_ticks
from ecosfera_ai.domain.feedback.models import CausalExplanation
from ecosfera_ai.interfaces.http.deps import (
    get_create_planet_use_case,
    get_planet_repo,
    get_run_tick_use_case,
)
from ecosfera_ai.interfaces.http.schemas.feedback import CausalStepOut, ExplainResponse
from ecosfera_ai.interfaces.http.schemas.simulation import (
    CreatePlanetRequest,
    PlanetStateOut,
    StateDeltaOut,
    TickResponse,
)
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState, StateDelta

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _state_out(state: PlanetState) -> PlanetStateOut:
    return PlanetStateOut(
        planet_id=state.planet_id,
        seed=state.seed,
        tick=state.tick,
        temperature=state.temperature,
        co2=state.co2,
        water=state.water,
        ice_cover=state.ice_cover,
        biomass=state.biomass,
        energy=state.energy,
    )


def _delta_out(delta: StateDelta) -> StateDeltaOut:
    return StateDeltaOut(
        temperature=delta.d_temperature,
        co2=delta.d_co2,
        water=delta.d_water,
        ice_cover=delta.d_ice_cover,
        biomass=delta.d_biomass,
        energy=delta.d_energy,
    )


def _explanation_out(explanation: CausalExplanation) -> ExplainResponse:
    return ExplainResponse(
        planet_id=explanation.planet_id,
        summary=explanation.summary,
        chain=[
            CausalStepOut(
                cause=s.cause,
                effect=s.effect,
                direction=s.direction.value,
                rule_id=s.rule_id,
                explanation=s.explanation,
            )
            for s in explanation.chain
        ],
        grounded=explanation.grounded,
        source=explanation.source,
    )


@router.post("/planets", status_code=201, response_model=PlanetStateOut)
async def create_planet(
    req: CreatePlanetRequest,
    uc: CreatePlanetUseCase = Depends(get_create_planet_use_case),
) -> PlanetStateOut:
    """Cria e configura um planeta a partir de uma semente (RF-011/012)."""
    planet_id = req.planet_id or f"planet-{uuid4().hex[:12]}"
    state = await uc.execute(PlanetSeed(planet_id=planet_id, seed=req.seed))
    return _state_out(state)


@router.post("/planets/{planet_id}/tick", response_model=TickResponse)
async def run_tick(
    planet_id: str,
    uc: RunTickUseCase = Depends(get_run_tick_use_case),
) -> TickResponse:
    """Avança 1 tick determinístico: novo estado + cadeia causal (RF-013/014)."""
    outcome = await uc.execute(planet_id)  # PlanetNotFoundError -> 404 (handler)
    simulation_ticks.inc()
    return TickResponse(
        state=_state_out(outcome.state),
        delta=_delta_out(outcome.delta),
        explanation=_explanation_out(outcome.explanation),
    )


@router.get("/planets/{planet_id}", response_model=PlanetStateOut)
async def get_planet(
    planet_id: str,
    repo: PlanetRepository = Depends(get_planet_repo),
) -> PlanetStateOut:
    """Retorna o estado atual do planeta (último checkpoint persistido)."""
    state = await repo.load_latest(planet_id)
    if state is None:
        raise PlanetNotFoundError(planet_id)
    return _state_out(state)
