"""Resource Engine — converte estado físico em orçamento biológico (M2).

Último elo determinístico da cadeia: lê as quatro fatias físicas já resolvidas
no tick e publica a `carrying_capacity`, que é o ÚNICO acoplamento entre a
física e a biologia (ADR 0006/0013). A biologia gasta dentro do orçamento e
nunca escreve de volta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.resource.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    ResourceEngineParams,
    load_params,
)
from ecosfera_ai.engines.resource.domain import (
    carrying_capacity,
    consumption,
    energy_available,
    habitability,
    nutrients_available,
    water_available,
)
from ecosfera_ai.engines.resource.events import (
    CARRYING_CAPACITY_SHIFT,
    RESOURCE_SCARCITY,
    ResourceCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta

_EPS = 1e-9


@dataclass(slots=True)
class ResourceEngine:
    """Implementa a porta `Engine` (Spec §5.2) para a disponibilidade de recurso."""

    params: ResourceEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.resource
        hydrology = ctx.snapshot.hydrology
        chemistry = ctx.snapshot.chemistry
        temperature = ctx.snapshot.climate.temperature
        solar_flux = ctx.snapshot.astronomy.solar_flux

        water = water_available(hydrology.ocean, hydrology.freshwater, self.params)
        nutrients = nutrients_available(
            chemistry.nutrients,
            chemistry.nitrogen,
            chemistry.phosphorus,
            chemistry.sulfur,
            self.params,
        )
        energy = energy_available(solar_flux, self.params)

        index = habitability(temperature, water, nutrients, energy, self.params)
        capacity = carrying_capacity(index, self.params)
        # Leitura DEFASADA: o Biota roda depois deste Engine, então a biomassa que
        # consome recurso aqui é a do tick anterior. Declarada em `lagged_reads`.
        consumed = consumption(ctx.snapshot.biota.biomass, self.params)

        events = self._notable(
            ctx,
            capacity_before=current.carrying_capacity,
            capacity_after=capacity,
            before=(current.water_available, current.nutrients_available, current.energy_available),
            after=(water, nutrients, energy),
            index=index,
        )

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "water_available": water - current.water_available,
                    "nutrients_available": nutrients - current.nutrients_available,
                    "energy_available": energy - current.energy_available,
                    "carrying_capacity": capacity - current.carrying_capacity,
                    "consumed": consumed - current.consumed,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=3,  # água, nutriente, energia
        )

    def _notable(
        self,
        ctx: TickContext,
        *,
        capacity_before: float,
        capacity_after: float,
        before: tuple[float, float, float],
        after: tuple[float, float, float],
        index: float,
    ) -> tuple[DomainEvent, ...]:
        """Só a mudança relevante vira evento — nunca o estado contínuo.

        A capacidade é comparada em variação RELATIVA porque a escala absoluta é
        arbitrária (o `max_carrying_capacity` é um parâmetro). Uma variação de
        cinco unidades significa coisas opostas num planeta de capacidade 10 e
        num de capacidade 500.

        Um planeta ainda sem medida (capacidade anterior zero) não gera evento de
        variação: sair de zero é o nascimento da leitura, não uma mudança.
        """
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []

        if capacity_before > _EPS:
            relative = (capacity_after - capacity_before) / capacity_before
            if abs(relative) >= self.params.capacity_event_threshold:
                gained = relative > 0.0
                events.append(
                    emitter.emit(
                        CARRYING_CAPACITY_SHIFT,
                        ResourceCauseCode.HABITABILITY_GAIN
                        if gained
                        else ResourceCauseCode.HABITABILITY_LOSS,
                        location={"region_id": "global"},
                        participants=[f"engine:{self.engine_id}"],
                        environmental_factors=[f"habitability:{'high' if gained else 'low'}"],
                        resources=["water", "nutrients", "energy"],
                        cause_detail={
                            "carrying_capacity": capacity_after,
                            "capacity_before": capacity_before,
                            "change": relative,
                            "habitability": index,
                        },
                        # A capacidade caiu/subiu porque o CLIMA mudou: é dele que
                        # vem a causa pelo Canal A na esmagadora maioria dos casos.
                        causation_id=ctx.caused_by_slice(SliceRef.CLIMATE),
                    )
                )

        # A escassez é reportada quando o LIMITANTE MUDA — não enquanto ele dura.
        # Um planeta pobre em fósforo é pobre em fósforo para sempre; dizer isso a
        # cada tick afogaria a trilha. O que muda a história é o limitante passar
        # a existir, deixar de existir, ou trocar de identidade.
        scarce_before = self._limiting(before)
        scarce_after = self._limiting(after)
        if scarce_after is not None and scarce_after[1] != (
            scarce_before[1] if scarce_before else None
        ):
            cause, resource_name, value = scarce_after
            events.append(
                emitter.emit(
                    RESOURCE_SCARCITY,
                    cause,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=[f"{resource_name}:scarce"],
                    resources=[resource_name],
                    cause_detail={
                        "resource": resource_name,
                        "available": value,
                        "carrying_capacity": capacity_after,
                    },
                    causation_id=events[0].event_id if events else None,
                )
            )
        return tuple(events)

    def _limiting(
        self, availability: tuple[float, float, float]
    ) -> tuple[ResourceCauseCode, str, float] | None:
        """O recurso mais escasso frente ao PRÓPRIO requisito, ou nada.

        A escassez é medida em fração do requisito, e não em valor absoluto: água,
        nutriente e energia vivem em escalas diferentes, e um único limiar
        absoluto declararia um deles permanentemente escasso num planeta normal.

        Devolve UM recurso, não três: o que a lei do mínimo diz é que existe um
        limitante, e nomear o limitante é a informação pedagógica. Três eventos
        simultâneos diriam ao aluno que há três problemas, quando há um.
        """
        water, nutrients, energy = availability
        fraction = self.params.scarcity_fraction
        candidates = (
            (
                water / max(self.params.water_requirement, _EPS),
                ResourceCauseCode.WATER_SHORTAGE,
                "water",
                water,
            ),
            (
                nutrients / max(self.params.nutrient_requirement, _EPS),
                ResourceCauseCode.NUTRIENT_SHORTAGE,
                "nutrients",
                nutrients,
            ),
            (
                energy / max(self.params.energy_requirement, _EPS),
                ResourceCauseCode.ENERGY_SHORTAGE,
                "energy",
                energy,
            ),
        )
        below = [c for c in candidates if c[0] < fraction]
        if not below:
            return None
        _, cause, name, value = min(below, key=lambda c: c[0])
        return cause, name, value
