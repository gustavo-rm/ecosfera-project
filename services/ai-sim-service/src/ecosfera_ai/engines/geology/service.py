"""Geology Engine — vulcanismo, relevo e a FONTE de carbono do planeta.

Primeiro elo da fatia vertical do M1. Publica o fluxo de CO2 desgaseificado na
própria fatia; a atmosfera o lê pelo Canal A. Em nenhum momento escreve na
`AtmosphereSlice` — é isso que faz a seta vulcanismo→CO2 respeitar a regra de
ouro da Spec §2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.geology.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    GeologyEngineParams,
    load_params,
)
from ecosfera_ai.engines.geology.domain import (
    is_eruption,
    outgassing_flux,
    relief_change,
    volcanism_change,
)
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION, GeologyCauseCode
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class GeologyEngine:
    """Implementa a porta `Engine` (Spec §5.2) para o domínio geológico."""

    params: GeologyEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.geology
        # A erosão responde à água LÍQUIDA em contato com o relevo: oceano e água
        # doce. Vapor e gelo não erodem rocha na escala deste modelo.
        hydrology = ctx.snapshot.hydrology
        water = hydrology.ocean + hydrology.freshwater

        pulse = float(ctx.rng.normal(0.0, self.params.tectonic_activity))
        d_volcanism = volcanism_change(current.volcanism, pulse, self.params)
        volcanism = current.volcanism + d_volcanism

        d_relief = relief_change(current.volcanism, current.relief, water, self.params)
        # FRONTEIRA basal x catastrófico (ADR 0018). O supervulcanismo é evento
        # extraordinário, mas o carbono que ele injeta é carbono VULCÂNICO — e
        # quem detém o fluxo vulcânico é este Engine. O Event publica a
        # INTENSIDADE na `EventSlice`; a soma acontece aqui, num único termo.
        #
        # A alternativa — o Event publicar um pulso de CO2 que a atmosfera
        # somasse ao lado de `geology.co2_flux` — criaria DUAS entradas de
        # carbono vulcânico no mundo, e a dupla contagem passaria a depender de
        # disciplina em vez de estrutura. O M2 já pagou esse preço uma vez.
        supervolcanic = ctx.snapshot.event.supervolcanic_intensity
        flux = outgassing_flux(volcanism, self.params) * (
            1.0 + supervolcanic * self.params.supervolcanic_multiplier
        )

        events: tuple[DomainEvent, ...] = ()
        if is_eruption(volcanism, self.params):
            emitter = EventEmitter(
                engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era
            )
            events = (
                emitter.emit(
                    VOLCANIC_ERUPTION,
                    GeologyCauseCode.TECTONIC_PULSE,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    resources=["co2"],
                    cause_detail={
                        "volcanism": volcanism,
                        "pulse": abs(pulse),
                        "co2_flux": flux,
                    },
                ),
            )

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "volcanism": d_volcanism,
                    "relief": d_relief,
                    # O fluxo é um VALOR do tick, não um acumulado: o delta o
                    # reposiciona substituindo o do tick anterior.
                    "co2_flux": flux - current.co2_flux,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=1,
        )
