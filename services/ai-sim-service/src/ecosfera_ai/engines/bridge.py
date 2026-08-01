"""Tradução entre o `PlanetState` persistido e o world-state da moldura.

Desde o M2 a tradução é uma **bijeção** nas fatias novas: o que entra volta
idêntico. Antes não era — a `LegacySlice` guardava o que ainda não tinha dono, e
tudo o mais era truncado a cada tick (ADR 0011 §4b).

## Por que o `PlanetState` cresceu

`FrameworkTickOrchestrator.tick()` faz o ciclo `snapshot -> tick -> PlanetState`
a CADA tick, porque é o `PlanetState` que a borda HTTP e a persistência guardam.
Um campo sem lugar no `PlanetState` volta a zero uma vez por tick. Com a
hidrologia, a química, o recurso e a biota novos, isso apagaria a metade da
ciência do M2 antes que ela pudesse realimentar qualquer coisa.

A saída foi ampliar o `PlanetState` com os ESTOQUES das fatias novas. É a
evolução que a persistência já previa: o estado é gravado como JSONB justamente
para que ganhar campos não exija migration, e a leitura tolera chaves
desconhecidas e preenche ausentes com o default da dataclass. Checkpoints
gravados antes do M2 continuam legíveis (ADR 0012).

Substituir o `PlanetState` inteiro pelo `WorldStateSnapshot` continua sendo
trabalho do **M5**; o que o M2 fez foi impedir que a truncagem comesse a ciência
nova enquanto isso não acontece.

## `water` e `ice_cover` continuam publicados

São grandezas AGREGADAS, derivadas dos reservatórios: `water` é a água líquida
(oceano + doce) e `ice_cover` é a fração congelada da hidrosfera. Elas seguem no
contrato HTTP e em `OBSERVABLE_VARIABLES` porque é assim que o aluno lê o
planeta — quem ganhou detalhe foi o modelo, não a interface.
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.world_state import (
    AstronomySlice,
    AtmosphereSlice,
    BiotaSlice,
    ChemistrySlice,
    ClimateSlice,
    EcologySlice,
    GeologySlice,
    HydrologySlice,
    ResourceSlice,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.state import PlanetState

_EPS = 1e-9


def _hydrology_of(state: PlanetState) -> HydrologySlice:
    """Reparte a água nos quatro reservatórios, hidratando estados agregados.

    Um `PlanetState` recém-criado (ou gravado antes do M2) traz só os agregados
    `water` e `ice_cover`. Nesse caso os reservatórios são derivados uma única
    vez, de modo que a fração de gelo resultante seja exatamente a declarada:

        gelo = água · cobertura / (1 − cobertura)   =>   gelo/(gelo + água) = cobertura

    A partir daí o detalhe viaja no próprio `PlanetState` e esta reidratação não
    volta a acontecer — o que preserva vapor e água doce, que o agregado não sabe
    representar.
    """
    reservoirs = state.ocean_water + state.ice_mass + state.vapour + state.freshwater
    if reservoirs > _EPS:
        return HydrologySlice(
            ocean=state.ocean_water,
            ice=state.ice_mass,
            vapour=state.vapour,
            freshwater=state.freshwater,
            salinity=state.salinity,
            ocean_circulation=state.ocean_circulation,
            ice_fraction=_ice_fraction(state.ice_mass, reservoirs),
            evaporation=state.evaporation,
            precipitation=state.precipitation,
        )

    cover = min(max(state.ice_cover, 0.0), 1.0 - _EPS)
    ice = state.water * cover / (1.0 - cover)
    total = state.water + ice
    return HydrologySlice(
        ocean=state.water,
        ice=ice,
        salinity=state.salinity,
        ocean_circulation=state.ocean_circulation,
        ice_fraction=_ice_fraction(ice, total),
    )


def _ice_fraction(ice: float, total: float) -> float:
    return ice / total if total > _EPS else 0.0


def snapshot_of(state: PlanetState, *, era: int = 0) -> WorldStateSnapshot:
    """Reparte um `PlanetState` pelas fatias dos seus Engines donos.

    `co2_flux`, `greenhouse_forcing` e `pressure` nascem em zero: são TAXAS e
    grandezas derivadas, funções puras de estoques que sobrevivem, recalculadas
    idênticas no primeiro tick (ADR 0011 §4b).
    """
    return WorldStateSnapshot(
        planet_id=state.planet_id,
        seed=state.seed,
        tick=state.tick,
        era=era,
        astronomy=AstronomySlice(
            orbital_x=state.orbital_x,
            orbital_y=state.orbital_y,
            orbital_vx=state.orbital_vx,
            orbital_vy=state.orbital_vy,
            solar_flux=state.solar_flux,
        ),
        geology=GeologySlice(relief=state.relief, volcanism=state.volcanism),
        atmosphere=AtmosphereSlice(co2=state.co2),
        climate=ClimateSlice(temperature=state.temperature, energy=state.energy),
        hydrology=_hydrology_of(state),
        chemistry=ChemistrySlice(
            ocean_carbon=state.ocean_carbon,
            soil_carbon=state.soil_carbon,
            nitrogen=state.nitrogen,
            phosphorus=state.phosphorus,
            sulfur=state.sulfur,
            nutrients=state.nutrients,
            ph=state.ph,
            air_sea_flux=state.air_sea_flux,
        ),
        resource=ResourceSlice(
            water_available=state.water_available,
            nutrients_available=state.nutrients_available,
            energy_available=state.energy_available,
            carrying_capacity=state.carrying_capacity,
            consumed=state.consumed,
        ),
        biota=BiotaSlice(
            biomass=state.biomass,
            species_richness=state.species_richness,
            mean_temp_optimum=state.mean_temp_optimum,
            mean_temp_tolerance=state.mean_temp_tolerance,
            mean_water_need=state.mean_water_need,
            mean_size=state.mean_size,
            mean_metabolism=state.mean_metabolism,
            mean_trophic_level=state.mean_trophic_level,
        ),
        ecology=EcologySlice(
            producer_biomass=state.producer_biomass,
            herbivore_biomass=state.herbivore_biomass,
            predator_biomass=state.predator_biomass,
            predation_pressure=state.predation_pressure,
            total_population=state.total_population,
        ),
    )


def planet_state_of(snapshot: WorldStateSnapshot) -> PlanetState:
    """Junta as fatias no `PlanetState` que a borda HTTP e a persistência esperam."""
    hydrology = snapshot.hydrology
    chemistry = snapshot.chemistry
    resource = snapshot.resource
    astronomy = snapshot.astronomy
    return PlanetState(
        planet_id=snapshot.planet_id,
        seed=snapshot.seed,
        tick=snapshot.tick,
        temperature=snapshot.climate.temperature,
        co2=snapshot.atmosphere.co2,
        # Agregados publicados: água LÍQUIDA e fração congelada da hidrosfera.
        water=hydrology.ocean + hydrology.freshwater,
        ice_cover=hydrology.ice_fraction,
        biomass=snapshot.biota.biomass,
        energy=snapshot.climate.energy,
        orbital_x=astronomy.orbital_x,
        orbital_y=astronomy.orbital_y,
        orbital_vx=astronomy.orbital_vx,
        orbital_vy=astronomy.orbital_vy,
        solar_flux=astronomy.solar_flux,
        relief=snapshot.geology.relief,
        volcanism=snapshot.geology.volcanism,
        salinity=hydrology.salinity,
        ocean_circulation=hydrology.ocean_circulation,
        # Detalhe das fatias do M2 — é o que impede a truncagem por tick.
        ocean_water=hydrology.ocean,
        ice_mass=hydrology.ice,
        vapour=hydrology.vapour,
        freshwater=hydrology.freshwater,
        evaporation=hydrology.evaporation,
        precipitation=hydrology.precipitation,
        ocean_carbon=chemistry.ocean_carbon,
        soil_carbon=chemistry.soil_carbon,
        nitrogen=chemistry.nitrogen,
        phosphorus=chemistry.phosphorus,
        sulfur=chemistry.sulfur,
        nutrients=chemistry.nutrients,
        ph=chemistry.ph,
        air_sea_flux=chemistry.air_sea_flux,
        water_available=resource.water_available,
        nutrients_available=resource.nutrients_available,
        energy_available=resource.energy_available,
        # Capacidade de suporte PUBLICADA: é daqui que o M3 a lê, e não de um
        # subsistema instanciado à parte (ADR 0013).
        carrying_capacity=resource.carrying_capacity,
        consumed=resource.consumed,
        species_richness=snapshot.biota.species_richness,
        mean_temp_optimum=snapshot.biota.mean_temp_optimum,
        mean_temp_tolerance=snapshot.biota.mean_temp_tolerance,
        mean_water_need=snapshot.biota.mean_water_need,
        mean_size=snapshot.biota.mean_size,
        mean_metabolism=snapshot.biota.mean_metabolism,
        mean_trophic_level=snapshot.biota.mean_trophic_level,
        producer_biomass=snapshot.ecology.producer_biomass,
        herbivore_biomass=snapshot.ecology.herbivore_biomass,
        predator_biomass=snapshot.ecology.predator_biomass,
        predation_pressure=snapshot.ecology.predation_pressure,
        total_population=snapshot.ecology.total_population,
    )
