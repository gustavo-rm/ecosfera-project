"""Ecology Engine — reparte a comunidade em níveis tróficos e resolve a predação.

Porta a ciência do modelo trófico de `simulation_engine/biology/ecology.py` —
corrigido no M3 para atualização **síncrona**, com teto global de captura e ordem
estável — para aritmética pura sobre agregados por nível trófico.

**Não envolve o modelo por agente, e não importa `mesa`.** O ABM opera sobre
populações por espécie; este Engine opera sobre três agregados, que é o que cabe
no Canal A (aditivo, de floats). Envolvê-lo exigiria materializar a lista de
espécies a cada tick só para agregá-la de volta. A consequência prática é que os
nove Engines importam e rodam sem o extra `sim` instalado (ADR 0017); o ABM
segue vivo no caminho por era, atrás de fábrica preguiçosa.

## O que ele escreve, e o que NÃO escreve

Escreve a `EcologySlice`: biomassa por nível trófico, população total e a
pressão de predação que a Evolution lê defasada. **Não escreve a biomassa
total** — essa é da `BiotaSlice`, da Evolution. A ecologia redistribui o que
existe entre os níveis; não cria nem destrói o total (ADR 0016).

## Cadência

Roda `steps_per_tick` passos por tick (padrão 1), e não um lote por era. Com
`era_length: 10` o trabalho total por era é equivalente ao do modelo anterior,
mas a ecologia passa a responder a um ambiente atualizado entre os passos em vez
de a um instantâneo congelado no início da era.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.ecology.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    EcologyEngineParams,
    load_params,
)
from ecosfera_ai.engines.ecology.events import (
    POPULATION_DECLINED,
    TROPHIC_COLLAPSE,
    EcologyCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import EcologySlice, SliceRef, StateDelta

_EPS = 1e-9


@dataclass(slots=True)
class EcologyEngine:
    """Implementa a porta `Engine` (Spec §5.2) para a dinâmica trófica."""

    params: EcologyEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.ecology
        biomass = ctx.snapshot.biota.biomass
        capacity = ctx.snapshot.resource.carrying_capacity

        levels = _seeded_levels(current, biomass, self.params)
        for _ in range(max(0, self.params.steps_per_tick)):
            levels = _trophic_step(levels, capacity, self.params, ctx)

        # A biomassa total é da Evolution; a ecologia apenas a REPARTE. Renormalizar
        # é o que impede este Engine de virar uma segunda fonte de biomassa — a
        # dupla contagem que o ADR 0016 proíbe.
        levels = _renormalised(levels, biomass, self.params)
        pressure = _predation_pressure(levels, self.params)
        events = self._notable(ctx, current, levels, pressure)

        total = sum(levels)
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "producer_biomass": levels[0] - current.producer_biomass,
                    "herbivore_biomass": levels[1] - current.herbivore_biomass,
                    "predator_biomass": levels[2] - current.predator_biomass,
                    "predation_pressure": pressure - current.predation_pressure,
                    "total_population": total - current.total_population,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=3,  # três níveis tróficos agregados
        )

    def _notable(
        self,
        ctx: TickContext,
        current: EcologySlice,
        levels: tuple[float, float, float],
        pressure: float,
    ) -> tuple[DomainEvent, ...]:
        """Só travessia vira evento, e por NÍVEL — nunca por organismo (Corr.2)."""
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []
        before = (current.producer_biomass, current.herbivore_biomass, current.predator_biomass)
        names = ("producer", "herbivore", "predator")
        total = sum(levels)

        for index, (was, now) in enumerate(zip(before, levels, strict=True)):
            if was <= _EPS:
                continue
            share = now / total if total > _EPS else 0.0
            collapsed = (
                share
                < self.params.collapse_threshold
                <= (was / sum(before) if sum(before) > _EPS else 0.0)
            )
            if collapsed:
                events.append(
                    emitter.emit(
                        TROPHIC_COLLAPSE,
                        EcologyCauseCode.PREY_COLLAPSE
                        if index > 0
                        else EcologyCauseCode.RESOURCE_SCARCITY,
                        location={"region_id": "global"},
                        participants=[f"trophic:{names[index]}"],
                        environmental_factors=["ecology:trophic_level#collapsed"],
                        resources=["biomass"],
                        cause_detail={
                            "level": names[index],
                            "biomass": now,
                            "biomass_before": was,
                            "share": share,
                        },
                        causation_id=ctx.caused_by_slice(SliceRef.BIOTA),
                    )
                )
                continue
            if (was - now) / was >= self.params.decline_threshold:
                events.append(
                    emitter.emit(
                        POPULATION_DECLINED,
                        EcologyCauseCode.PREDATION_PRESSURE
                        if index < 2
                        else EcologyCauseCode.RESOURCE_SCARCITY,
                        location={"region_id": "global"},
                        participants=[f"trophic:{names[index]}"],
                        environmental_factors=["ecology:predation#high"],
                        resources=["biomass"],
                        cause_detail={
                            "level": names[index],
                            "biomass": now,
                            "biomass_before": was,
                            "predation_pressure": pressure,
                        },
                        causation_id=ctx.caused_by_slice(SliceRef.BIOTA),
                    )
                )
        return tuple(events)


def viability_threshold(params: EcologyEngineParams) -> float:
    """Biomassa do nível de BAIXO necessária para sustentar o nível de cima.

    Derivada das próprias taxas do modelo, não arbitrada: um consumidor ganha
    `conversão × predação × presa` por unidade de si e perde `mortalidade`. Ele
    só se sustenta quando

        conversão × predação × presa  >  mortalidade

    Calcular o limiar em vez de configurá-lo é o que impede que ele fique
    incoerente com as taxas quando alguém as recalibrar.
    """
    gain = params.conversion_efficiency * params.predation_rate
    return params.mortality_rate / gain if gain > _EPS else float("inf")


def _seeded_levels(
    current: EcologySlice, biomass: float, params: EcologyEngineParams
) -> tuple[float, float, float]:
    """Reparte a biomassa e deixa a SUCESSÃO ecológica ocupar níveis vazios.

    Uma comunidade recém-nascida chega como um número só. Níveis tróficos
    superiores não são semeados de saída: eles se **estabelecem** quando o nível
    de baixo passa a comportá-los (`viability_threshold`). Semeá-los antes disso
    seria plantar herbívoros num mundo que ainda não tem o que comer — eles
    morreriam no primeiro passo e nunca mais voltariam, porque o semeio só
    acontece uma vez.

    A sucessão é emergente: é a disponibilidade de recurso que abre o nicho, não
    um roteiro que decide quando cada nível aparece.
    """
    producer = current.producer_biomass
    herbivore = current.herbivore_biomass
    predator = current.predator_biomass
    existing = producer + herbivore + predator

    if existing <= _EPS:
        return (max(0.0, biomass), 0.0, 0.0)

    scale = biomass / existing
    producer, herbivore, predator = producer * scale, herbivore * scale, predator * scale

    threshold = viability_threshold(params)
    if herbivore <= _EPS and producer > threshold:
        herbivore = producer * params.herbivore_share
        producer -= herbivore
    if predator <= _EPS and herbivore > threshold:
        predator = herbivore * params.predator_share
        herbivore -= predator
    return (max(0.0, producer), max(0.0, herbivore), max(0.0, predator))


def _trophic_step(
    levels: tuple[float, float, float],
    capacity: float,
    params: EcologyEngineParams,
    ctx: TickContext,
) -> tuple[float, float, float]:
    """Um passo SÍNCRONO da cadeia, com teto global de predação por nível.

    Mesma correção do modelo por agente: todos leem a mesma fotografia e a
    captura é limitada ao estoque de presa — sem isso, predadores somados comem
    mais presa do que existe e a diferença vira biomassa do nada.
    """
    producer, herbivore, predator = levels

    grazed = min(producer, params.predation_rate * herbivore * producer)
    hunted = min(herbivore, params.predation_rate * predator * herbivore)

    if capacity > _EPS:
        growth = params.growth_rate * producer * (1.0 - producer / capacity)
    else:
        growth = -params.mortality_rate * producer

    noise = float(ctx.rng.normal(0.0, params.demographic_noise))
    new_producer = producer + growth - grazed + noise * producer
    new_herbivore = herbivore + params.conversion_efficiency * grazed
    new_herbivore -= params.mortality_rate * herbivore + hunted
    new_predator = predator + params.conversion_efficiency * hunted
    new_predator -= params.mortality_rate * predator

    return tuple(  # type: ignore[return-value]
        0.0 if value < params.min_viable_population else value
        for value in (max(0.0, new_producer), max(0.0, new_herbivore), max(0.0, new_predator))
    )


def _renormalised(
    levels: tuple[float, float, float], biomass: float, params: EcologyEngineParams
) -> tuple[float, float, float]:
    """Ajusta a repartição ao total que a Evolution publicou, SEM inverter a pirâmide.

    A ecologia decide a FORMA da pirâmide; o tamanho é da Evolution. Mas uma
    renormalização ingênua (escalar os três níveis pelo mesmo fator) tem um
    defeito medido: quando os produtores colapsam e os predadores sobrevivem, ela
    ESCALA OS PREDADORES PARA CIMA até absorverem todo o total — produzindo um
    planeta de predadores sem nada para comer.

    A pirâmide de biomassa não inverte (Elton, 1927): cada nível trófico carrega
    menos biomassa que o de baixo, porque a conversão dissipa energia. Aqui isso
    vira restrição explícita — os consumidores somados não passam de
    `max_consumer_share` do total, e o produtor é a BASE que absorve o restante.
    """
    producer, herbivore, predator = levels
    if biomass <= 0.0:
        return (0.0, 0.0, 0.0)

    consumers = herbivore + predator
    allowed = biomass * params.max_consumer_share
    if consumers > allowed and consumers > _EPS:
        scale = allowed / consumers
        herbivore, predator = herbivore * scale, predator * scale
        consumers = herbivore + predator
    producer = max(0.0, biomass - consumers)
    return (producer, herbivore, predator)


def _predation_pressure(levels: tuple[float, float, float], params: EcologyEngineParams) -> float:
    """Pressão que os consumidores exercem — o que a Evolution lê defasado."""
    del params
    total = sum(levels)
    if total <= _EPS:
        return 0.0
    return (levels[1] + levels[2]) / total
