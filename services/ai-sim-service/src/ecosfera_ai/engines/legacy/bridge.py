"""Tradução entre o `PlanetState` do núcleo atual e o world-state da moldura.

Ponte de mão dupla e sem perda: a `LegacySlice` tem exatamente os campos
numéricos do `PlanetState`, e `planet_id`/`seed`/`tick` moram no cabeçalho do
snapshot. Traduzir não muda um número — se mudasse, a paridade determinística
que o M0 precisa provar não existiria.
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.world_state import LegacySlice, WorldStateSnapshot
from ecosfera_ai.simulation_engine.state import PlanetState


def legacy_slice_of(state: PlanetState) -> LegacySlice:
    """Projeta o estado do núcleo determinístico na fatia transitória."""
    return LegacySlice(
        temperature=state.temperature,
        co2=state.co2,
        water=state.water,
        ice_cover=state.ice_cover,
        biomass=state.biomass,
        energy=state.energy,
        orbital_x=state.orbital_x,
        orbital_y=state.orbital_y,
        orbital_vx=state.orbital_vx,
        orbital_vy=state.orbital_vy,
        solar_flux=state.solar_flux,
        relief=state.relief,
        volcanism=state.volcanism,
        salinity=state.salinity,
        ocean_circulation=state.ocean_circulation,
    )


def snapshot_of(state: PlanetState, *, era: int = 0) -> WorldStateSnapshot:
    """Constrói um snapshot da moldura a partir de um `PlanetState`."""
    return WorldStateSnapshot(
        planet_id=state.planet_id,
        seed=state.seed,
        tick=state.tick,
        era=era,
        legacy=legacy_slice_of(state),
    )


def planet_state_of(snapshot: WorldStateSnapshot) -> PlanetState:
    """Reconstrói o `PlanetState` a partir do snapshot (operação inversa)."""
    legacy = snapshot.legacy
    return PlanetState(
        planet_id=snapshot.planet_id,
        seed=snapshot.seed,
        tick=snapshot.tick,
        temperature=legacy.temperature,
        co2=legacy.co2,
        water=legacy.water,
        ice_cover=legacy.ice_cover,
        biomass=legacy.biomass,
        energy=legacy.energy,
        orbital_x=legacy.orbital_x,
        orbital_y=legacy.orbital_y,
        orbital_vx=legacy.orbital_vx,
        orbital_vy=legacy.orbital_vy,
        solar_flux=legacy.solar_flux,
        relief=legacy.relief,
        volcanism=legacy.volcanism,
        salinity=legacy.salinity,
        ocean_circulation=legacy.ocean_circulation,
    )
