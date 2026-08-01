# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Biota Engine PROVISÓRIO — biomassa agregada determinística (M2).

Porte do subsistema `life` para a moldura, sem alteração de ciência. Existe por
uma razão só: dar dono à `BiotaSlice` para que o LegacySubsystemAdapter possa ser
aposentado (ADR 0013/0014). É substituído pela evolução emergente no M3.

**Fronteira dura.** Zero evolução, especiação, genoma, mutação ou ABM. Nenhum
import de `deap`, `mesa` ou `simulation_engine/biology/` — e o import-linter faz
disso um erro de build, não uma convenção de revisão.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.biota.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    BiotaEngineParams,
    load_params,
)
from ecosfera_ai.engines.biota.domain import (
    demographic_noise,
    emergence,
    logistic_growth,
)
from ecosfera_ai.engines.biota.events import (
    ABIOGENESIS,
    BIOMASS_COLLAPSE,
    BiotaCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class BiotaEngine:
    """Implementa a porta `Engine` (Spec §5.2) para a biomassa agregada."""

    params: BiotaEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.biota
        # A capacidade vem PRONTA do Resource. Este Engine não sabe o que é
        # temperatura, água ou nutriente — e é por não saber que a fronteira
        # física/biologia se sustenta (ADR 0013).
        capacity = ctx.snapshot.resource.carrying_capacity
        biomass = current.biomass

        seeded = emergence(biomass, capacity, self.params)
        growth = logistic_growth(biomass, capacity, self.params)
        draw = float(ctx.rng.normal(0.0, self.params.growth_variability))
        noise = demographic_noise(biomass, draw)

        d_biomass = seeded + growth + noise
        after = max(0.0, biomass + d_biomass)

        events = self._notable(ctx, before=biomass, after=after, seeded=seeded, capacity=capacity)

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={"biomass": after - biomass},
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=1,  # um estoque agregado — sem agentes (ADR 0013)
        )

    def _notable(
        self,
        ctx: TickContext,
        *,
        before: float,
        after: float,
        seeded: float,
        capacity: float,
    ) -> tuple[DomainEvent, ...]:
        """Dois marcos, ambos travessias: a vida começar e a vida acabar."""
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []
        causation = ctx.caused_by_slice(SliceRef.RESOURCE)

        if seeded > 0.0 and after > self.params.emergence_event_threshold:
            events.append(
                emitter.emit(
                    ABIOGENESIS,
                    BiotaCauseCode.HABITABILITY_THRESHOLD,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=["habitability:high"],
                    resources=["biomass"],
                    cause_detail={"biomass": after, "carrying_capacity": capacity},
                    causation_id=causation,
                )
            )

        collapsed = before >= self.params.collapse_threshold > after
        if collapsed:
            events.append(
                emitter.emit(
                    BIOMASS_COLLAPSE,
                    BiotaCauseCode.CAPACITY_COLLAPSE,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=["habitability:low"],
                    resources=["biomass"],
                    cause_detail={
                        "biomass": after,
                        "biomass_before": before,
                        "carrying_capacity": capacity,
                    },
                    causation_id=causation,
                )
            )
        return tuple(events)
