from __future__ import annotations

from fastapi import APIRouter, Depends

from ecosfera_ai.application.ports.job_queue import JobQueue
from ecosfera_ai.application.ports.planet_repo import PlanetRepository
from ecosfera_ai.application.simulation.evolve_biology import SpeciesNotFoundError
from ecosfera_ai.application.simulation.replay_state import EraNotFoundError
from ecosfera_ai.application.simulation.run_tick import PlanetNotFoundError
from ecosfera_ai.interfaces.http.deps import (
    get_job_queue,
    get_life_subsystem,
    get_planet_repo,
)
from ecosfera_ai.interfaces.http.schemas.biology import (
    BiologySummaryOut,
    CodexResponse,
    EcologyResponse,
    GenomeOut,
    JobStatusResponse,
    PopulationOut,
    SpeciesOut,
)
from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem

router = APIRouter(prefix="/simulation", tags=["biology"])


def species_out(record: SpeciesRecord) -> SpeciesOut:
    return SpeciesOut(
        species_id=record.species_id,
        genome=GenomeOut(**record.genome.to_dict()),
        emerged_era=record.emerged_era,
        extinct_era=record.extinct_era,
        ancestor_id=record.ancestor_id,
        population=record.population,
        fitness=record.fitness,
        trophic_class=record.genome.trophic_class,
    )


@router.get("/planets/{planet_id}/species", response_model=CodexResponse)
async def get_codex(
    planet_id: str,
    repo: PlanetRepository = Depends(get_planet_repo),
) -> CodexResponse:
    """Códex de espécies do planeta — o catálogo que se preenche (GDD §11)."""
    catalog = await repo.load_species(planet_id)
    return CodexResponse(
        planet_id=planet_id,
        species=[species_out(record) for record in catalog],
        living=sum(1 for record in catalog if not record.is_extinct),
        extinct=sum(1 for record in catalog if record.is_extinct),
    )


@router.get("/planets/{planet_id}/species/{species_id}", response_model=SpeciesOut)
async def get_species(
    planet_id: str,
    species_id: str,
    repo: PlanetRepository = Depends(get_planet_repo),
) -> SpeciesOut:
    """Genoma inspecionável de uma espécie (RF-031)."""
    record = await repo.load_species_by_id(planet_id, species_id)
    if record is None:
        raise SpeciesNotFoundError(f"{planet_id}/{species_id}")
    return species_out(record)


@router.get("/planets/{planet_id}/ecology", response_model=EcologyResponse)
async def get_ecology(
    planet_id: str,
    repo: PlanetRepository = Depends(get_planet_repo),
    life: LifeSubsystem = Depends(get_life_subsystem),
) -> EcologyResponse:
    """Snapshot populacional atual e a capacidade de suporte que o ambiente oferece."""
    state = await repo.load_latest(planet_id)
    if state is None:
        raise PlanetNotFoundError(planet_id)

    catalog = [record for record in await repo.load_species(planet_id) if not record.is_extinct]
    return EcologyResponse(
        planet_id=planet_id,
        carrying_capacity=life.carrying_capacity(state),
        total_population=sum(record.population for record in catalog),
        populations=[
            PopulationOut(
                species_id=record.species_id,
                population=record.population,
                trophic_class=record.genome.trophic_class,
            )
            for record in catalog
        ],
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    jobs: JobQueue = Depends(get_job_queue),
) -> JobStatusResponse:
    """Andamento do job de evolução (padrão 202 do backend assíncrono — ADR 0007)."""
    result = await jobs.get_status(job_id)
    if result is None:
        raise EraNotFoundError(job_id)
    payload = result.result
    return JobStatusResponse(
        job_id=result.job_id,
        job_name=result.job_name,
        status=str(result.status),
        result=BiologySummaryOut(**payload) if payload else None,
        error=result.error,
    )
