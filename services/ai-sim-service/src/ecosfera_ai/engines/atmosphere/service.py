"""Atmosphere Engine — estoque de carbono e forçamento radiativo.

Elo do meio da fatia vertical do M1. Lê o fluxo desgaseificado na `GeologySlice`
(Canal A), integra o estoque de CO2 e publica o forçamento que o clima consome.
Dono ÚNICO do carbono desde o M1 (ADR 0010).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.atmosphere.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    AtmosphereEngineParams,
    load_params,
)
from ecosfera_ai.engines.atmosphere.domain import (
    co2_change,
    forcing_band,
    pressure,
    radiative_forcing,
)
from ecosfera_ai.engines.atmosphere.events import (
    GREENHOUSE_FORCING_CHANGED,
    AtmosphereCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class AtmosphereEngine:
    """Implementa a porta `Engine` (Spec §5.2) para o domínio atmosférico."""

    params: AtmosphereEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.atmosphere
        inflow = ctx.snapshot.geology.co2_flux
        biomass = ctx.snapshot.legacy.biomass

        d_co2 = co2_change(current.co2, inflow, biomass, self.params)
        co2 = max(0.0, current.co2 + d_co2)

        forcing = radiative_forcing(co2, self.params)
        after = forcing_band(forcing, self.params)
        # A faixa ANTERIOR é derivada do ESTOQUE, não do forçamento guardado na
        # fatia. Os dois valores são equivalentes enquanto o snapshot sobrevive
        # inteiro — mas na borda HTTP ele não sobrevive: o estado persistido
        # ainda é o `PlanetState` legado, que não tem campo para o forçamento.
        # Comparando contra um zero recém-nascido, a travessia de faixa seria
        # detectada em TODO tick, e o Canal B viraria ruído. Derivar do estoque
        # é robusto nos dois caminhos (ver ADR 0011, limitação conhecida).
        before = forcing_band(radiative_forcing(current.co2, self.params), self.params)

        events: tuple[DomainEvent, ...] = ()
        if after != before:
            emitter = EventEmitter(
                engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era
            )
            rising = after > before
            events = (
                emitter.emit(
                    GREENHOUSE_FORCING_CHANGED,
                    AtmosphereCauseCode.CO2_ACCUMULATION
                    if rising
                    else AtmosphereCauseCode.CO2_DRAWDOWN,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=[f"co2:{'high' if rising else 'low'}"],
                    resources=["co2"],
                    cause_detail={
                        "co2": co2,
                        "forcing": forcing,
                        "band_from": before,
                        "band_to": after,
                        "inflow": inflow,
                    },
                    # Encadeia com a erupção do MESMO tick, quando houve — a
                    # proveniência veio pelo Canal A, não por leitura do Canal B
                    # da geologia (Spec §2).
                    causation_id=ctx.caused_by_slice(SliceRef.GEOLOGY),
                ),
            )

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "co2": co2 - current.co2,
                    "greenhouse_forcing": forcing - current.greenhouse_forcing,
                    "pressure": pressure(co2, self.params) - current.pressure,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=1,
        )
