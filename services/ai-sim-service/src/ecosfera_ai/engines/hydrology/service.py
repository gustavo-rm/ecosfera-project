"""Hydrology Engine — o ciclo da água e a criosfera (M2).

Substitui o subsystem legado `ocean` e absorve o ciclo gelo<->água que estava
embutido no `chemistry` (ADR 0012). Lê a temperatura do Climate no MESMO tick;
o Climate lê o gelo daqui com um tick de atraso, e é assim que o acoplamento
bidirecional se resolve sem ciclo no grafo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.hydrology.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    HydrologyEngineParams,
    load_params,
)
from ecosfera_ai.engines.hydrology.domain import (
    apply_fluxes,
    ice_fraction,
    target_circulation,
    target_salinity,
    water_fluxes,
)
from ecosfera_ai.engines.hydrology.events import (
    ICE_SHEET_CHANGED,
    WATER_BALANCE_SHIFT,
    HydrologyCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class HydrologyEngine:
    """Implementa a porta `Engine` (Spec §5.2) para o domínio hidrológico."""

    params: HydrologyEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.hydrology
        temperature = ctx.snapshot.climate.temperature

        fluxes = water_fluxes(
            current.ocean,
            current.ice,
            current.vapour,
            current.freshwater,
            temperature,
            self.params,
        )
        ocean, ice, vapour, freshwater = apply_fluxes(
            current.ocean, current.ice, current.vapour, current.freshwater, fluxes
        )

        d_salinity = self.params.salinity_relaxation * (
            target_salinity(ocean, self.params) - current.salinity
        )
        salinity = current.salinity + d_salinity
        mixing = float(ctx.rng.normal(0.0, self.params.circulation_variability))
        gap = target_circulation(salinity, temperature, self.params) - current.ocean_circulation
        d_circulation = self.params.circulation_relaxation * gap + mixing

        fraction = ice_fraction(ice, ocean, vapour, freshwater)
        events = self._notable(ctx, current.ice, ice, ocean, vapour, freshwater, temperature)

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "ocean": ocean - current.ocean,
                    "ice": ice - current.ice,
                    "vapour": vapour - current.vapour,
                    "freshwater": freshwater - current.freshwater,
                    "salinity": d_salinity,
                    "ocean_circulation": d_circulation,
                    # Publicada para o albedo do Climate: ele a LÊ em vez de
                    # recalculá-la, que seria importar outro Engine (ADR 0012).
                    "ice_fraction": fraction - current.ice_fraction,
                    "evaporation": fluxes.evaporation - current.evaporation,
                    "precipitation": fluxes.precipitation - current.precipitation,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=4,  # quatro reservatorios
        )

    def _notable(
        self,
        ctx: TickContext,
        ice_before: float,
        ice_after: float,
        ocean: float,
        vapour: float,
        freshwater: float,
        temperature: float,
    ) -> tuple[DomainEvent, ...]:
        """Só a travessia de patamar vira evento — nunca o contínuo do tick."""
        before = ice_fraction(ice_before, ocean, vapour, freshwater)
        after = ice_fraction(ice_after, ocean, vapour, freshwater)
        change = after - before
        if abs(change) < self.params.ice_event_threshold:
            return ()

        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        melting = change < 0.0
        cause = (
            HydrologyCauseCode.TEMPERATURE_RISE if melting else HydrologyCauseCode.TEMPERATURE_FALL
        )
        causation = ctx.caused_by_slice(SliceRef.CLIMATE)
        ice_event = emitter.emit(
            ICE_SHEET_CHANGED,
            cause,
            location={"region_id": "polar"},
            participants=[f"engine:{self.engine_id}"],
            environmental_factors=[f"temperature:{'high' if melting else 'low'}"],
            resources=["water"],
            cause_detail={
                "ice_fraction": after,
                "change": change,
                "temperature": temperature,
            },
            causation_id=causation,
        )
        balance = emitter.emit(
            WATER_BALANCE_SHIFT,
            HydrologyCauseCode.PRECIPITATION_CHANGE,
            location={"region_id": "global"},
            participants=[f"engine:{self.engine_id}"],
            resources=["water"],
            cause_detail={"ocean": ocean, "vapour": vapour, "freshwater": freshwater},
            causation_id=ice_event.event_id,
        )
        return (ice_event, balance)
