from __future__ import annotations

from pydantic import BaseModel, Field

from ecosfera_ai.interfaces.http.schemas.feedback import ExplainResponse


class CreatePlanetRequest(BaseModel):
    seed: int = Field(ge=0, examples=[42], description="Semente do RNG (RF-023).")
    planet_id: str | None = Field(default=None, description="Opcional; gerado se ausente.")


class PlanetStateOut(BaseModel):
    """Estado do planeta exposto ao cliente.

    As coordenadas orbitais ficam de fora: são estado interno do integrador. O
    que o cliente precisa da física é a irradiância recebida (`solar_flux`).
    """

    planet_id: str
    seed: int
    tick: int
    temperature: float
    co2: float
    water: float
    ice_cover: float
    biomass: float
    energy: float
    solar_flux: float
    relief: float
    volcanism: float
    salinity: float
    ocean_circulation: float


class StateDeltaOut(BaseModel):
    temperature: float
    co2: float
    water: float
    ice_cover: float
    biomass: float
    energy: float
    solar_flux: float
    relief: float
    volcanism: float
    salinity: float
    ocean_circulation: float


class TickResponse(BaseModel):
    state: PlanetStateOut
    delta: StateDeltaOut
    explanation: ExplainResponse
