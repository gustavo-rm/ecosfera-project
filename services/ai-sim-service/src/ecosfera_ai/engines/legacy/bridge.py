"""Tradução entre o `PlanetState` do núcleo atual e o world-state da moldura.

Desde o M1 a tradução é uma **junção**, não um espelho: o `PlanetState` que os
subsistemas legados consomem é montado a partir de VÁRIAS fatias — temperatura e
energia do Climate, CO2 da Atmosphere, relevo e vulcanismo da Geology, e o resto
da `LegacySlice`.

É essa junção que permite ao `chemistry` legado continuar derretendo gelo com a
temperatura de verdade, sem que ele seja dono dela. Ele LÊ o mundo inteiro e
ESCREVE só a sua parte — exatamente o que a Spec §3 pede de qualquer Engine.
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.world_state import (
    AtmosphereSlice,
    ClimateSlice,
    GeologySlice,
    LegacySlice,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.state import PlanetState


def legacy_slice_of(state: PlanetState) -> LegacySlice:
    """Projeta em `LegacySlice` só o que ainda não tem Engine dono."""
    return LegacySlice(
        water=state.water,
        ice_cover=state.ice_cover,
        biomass=state.biomass,
        orbital_x=state.orbital_x,
        orbital_y=state.orbital_y,
        orbital_vx=state.orbital_vx,
        orbital_vy=state.orbital_vy,
        solar_flux=state.solar_flux,
        salinity=state.salinity,
        ocean_circulation=state.ocean_circulation,
    )


def snapshot_of(state: PlanetState, *, era: int = 0) -> WorldStateSnapshot:
    """Reparte um `PlanetState` pelas fatias dos seus donos atuais.

    `co2_flux` nasce em zero: é uma grandeza NOVA do M1 (fluxo, não estoque) que
    o `PlanetState` nunca teve. O Geology Engine a preenche no primeiro tick.
    """
    return WorldStateSnapshot(
        planet_id=state.planet_id,
        seed=state.seed,
        tick=state.tick,
        era=era,
        geology=GeologySlice(relief=state.relief, volcanism=state.volcanism),
        atmosphere=AtmosphereSlice(co2=state.co2),
        climate=ClimateSlice(
            temperature=state.temperature, ice_cover=state.ice_cover, energy=state.energy
        ),
        legacy=legacy_slice_of(state),
    )


def planet_state_of(snapshot: WorldStateSnapshot) -> PlanetState:
    """Junta as fatias no `PlanetState` que o legado e a borda HTTP esperam."""
    legacy = snapshot.legacy
    return PlanetState(
        planet_id=snapshot.planet_id,
        seed=snapshot.seed,
        tick=snapshot.tick,
        temperature=snapshot.climate.temperature,
        co2=snapshot.atmosphere.co2,
        water=legacy.water,
        ice_cover=legacy.ice_cover,
        biomass=legacy.biomass,
        energy=snapshot.climate.energy,
        orbital_x=legacy.orbital_x,
        orbital_y=legacy.orbital_y,
        orbital_vx=legacy.orbital_vx,
        orbital_vy=legacy.orbital_vy,
        solar_flux=legacy.solar_flux,
        relief=snapshot.geology.relief,
        volcanism=snapshot.geology.volcanism,
        salinity=legacy.salinity,
        ocean_circulation=legacy.ocean_circulation,
    )
