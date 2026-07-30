from __future__ import annotations

from pydantic import BaseModel, Field


class GenomeOut(BaseModel):
    """Genoma inspecionável (RF-031): traços com nomes do domínio, não pesos opacos."""

    temp_optimum: float
    temp_tolerance: float
    water_need: float
    size: float
    metabolism: float
    trophic_level: float


class SpeciesOut(BaseModel):
    species_id: str
    genome: GenomeOut
    emerged_era: int
    extinct_era: int | None = None
    ancestor_id: str | None = None
    population: float
    fitness: float
    trophic_class: int = Field(examples=[1], description="1=produtor, 2=herbívoro, 3=predador")


class CodexResponse(BaseModel):
    planet_id: str
    species: list[SpeciesOut]
    living: int
    extinct: int


class PopulationOut(BaseModel):
    species_id: str
    population: float
    trophic_class: int


class EcologyResponse(BaseModel):
    """Snapshot populacional agregado por espécie (nunca agente a agente)."""

    planet_id: str
    carrying_capacity: float
    total_population: float
    populations: list[PopulationOut]


class BiologySummaryOut(BaseModel):
    era: int
    speciated: list[str]
    extinct: list[str]
    living: int
    generations: int


class JobRefOut(BaseModel):
    job_id: str
    job_name: str


class JobStatusResponse(BaseModel):
    job_id: str
    job_name: str
    status: str = Field(examples=["complete"])
    result: BiologySummaryOut | None = None
    error: str | None = None
