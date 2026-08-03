"""Evolution Engine — seleção natural emergente sobre a comunidade (M3).

Substitui o Biota Engine PROVISÓRIO do M2, que crescia biomassa por uma curva
logística determinística. Agora a biomassa é consequência de a comunidade se
sustentar (ou não) nas condições que encontra, e o genoma médio DERIVA na
direção do ótimo local.

## Por que a comunidade é representada pelo genoma médio

`tick()` precisa ser função pura do snapshot — é disso que o replay bit-a-bit
depende. Guardar a lista de espécies num atributo do Engine o tornaria estatal e
quebraria essa pureza; e a lista não cabe no Canal A, que é aditivo e de floats
(ADR 0016).

A saída é a formulação de **genética quantitativa**: a comunidade é seu genoma
médio, e a seleção move essa média na direção do ótimo local a uma taxa
proporcional ao desvio. É emergente e não-teleológica — a média RASTREIA o
ambiente, não persegue um alvo. A composição por espécie é materializada no
códex a partir dos eventos, que carregam o genoma no `cause_detail`.

## Fronteira com o Resource

O Resource é dono da **capacidade** (o teto que o ambiente oferece); este Engine
é dono da **biomassa** (a ocupação). Um é limite, o outro é preenchimento. Este
Engine nunca redefine capacidade; o Resource nunca escreve biomassa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.evolution.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    EvolutionEngineParams,
    load_params,
)
from ecosfera_ai.engines.evolution.domain import (
    LocalConditions,
    has_speciated,
    local_suitability,
    maintenance_cost,
    mutate,
    population_change,
    thermal_match,
)
from ecosfera_ai.engines.evolution.events import (
    LIFE_EMERGED,
    MASS_MORTALITY,
    SPECIATION_OCCURRED,
    SPECIES_EXTINCT,
    TRAIT_SHIFT,
    EvolutionCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import BiotaSlice, SliceRef, StateDelta
from ecosfera_ai.simulation_engine.biology.genome import Genome

_TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")


def _genome_of(biota: BiotaSlice) -> Genome:
    """Reconstrói o genoma médio a partir da fatia."""
    return Genome(**{name: float(getattr(biota, f"mean_{name}")) for name in _TRAITS})


def _founder(params: EvolutionEngineParams, temperature: float) -> Genome:
    """Genoma do primeiro colonizador: adaptado ao mundo que o recebeu.

    A vida não surge com um genoma arbitrário e depois "melhora" — ela surge de
    um ambiente que a comportava. Partir do ótimo local é a leitura correta, e é
    o oposto de semear um indivíduo ruim para um otimizador consertar.
    """
    del params
    return Genome(
        temp_optimum=temperature,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=1.0,
        trophic_level=1.0,
    ).clamped()


@dataclass(slots=True)
class EvolutionEngine:
    """Implementa a porta `Engine` (Spec §5.2) para a evolução emergente."""

    params: EvolutionEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.biota
        resource = ctx.snapshot.resource
        temperature = ctx.snapshot.climate.temperature

        conditions = LocalConditions(
            temperature=temperature,
            water_available=resource.water_available,
            energy_available=resource.energy_available,
            carrying_capacity=resource.carrying_capacity,
            occupied=current.biomass,
            # Leitura DEFASADA: a Ecology roda depois deste Engine.
            predation_pressure=ctx.snapshot.ecology.predation_pressure,
            # Leitura DEFASADA da EventSlice: a mesma catástrofe que a Ecology
            # aplicou é a que este Engine vê para atribuir a causa (ADR 0019).
            catastrophe=ctx.snapshot.event.catastrophic_mortality,
        )

        if current.biomass <= 0.0:
            return self._abiogenesis(ctx, conditions, temperature)
        return self._selection(ctx, current, conditions)

    # --- Surgimento -----------------------------------------------------------

    def _abiogenesis(
        self, ctx: TickContext, conditions: LocalConditions, temperature: float
    ) -> TickResult:
        """A primeira vida surge quando o ambiente a comporta.

        O marco `LIFE_EMERGED` da linha do tempo passa a ser emitido AQUI, e não
        mais pelo `life` legado nem pelo Biota provisório (ADR 0016).
        """
        if conditions.carrying_capacity < self.params.abiogenesis_capacity:
            return TickResult(
                delta=StateDelta(engine_id=self.engine_id, tick=ctx.tick, writes=self.writes)
            )

        founder = _founder(self.params, temperature)
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        event = emitter.emit(
            LIFE_EMERGED,
            EvolutionCauseCode.HABITABILITY_THRESHOLD,
            location={"region_id": "global"},
            participants=["species:founder"],
            environmental_factors=["resource:carrying_capacity#sufficient"],
            resources=["biomass"],
            genes=list(_TRAITS),
            cause_detail={
                "carrying_capacity": conditions.carrying_capacity,
                "temperature": temperature,
                **{f"gene_{k}": v for k, v in founder.to_dict().items()},
            },
            causation_id=ctx.caused_by_slice(SliceRef.RESOURCE),
        )
        values = {"biomass": self.params.founder_population, "species_richness": 1.0}
        values.update({f"mean_{name}": float(getattr(founder, name)) for name in _TRAITS})
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values=values,
                caused_by=(event.event_id,),
            ),
            events=(event,),
            entities_processed=1,
        )

    # --- Seleção --------------------------------------------------------------

    def _selection(
        self, ctx: TickContext, current: BiotaSlice, conditions: LocalConditions
    ) -> TickResult:
        genome = _genome_of(current)
        suitability = local_suitability(genome, conditions, self.params)
        d_biomass = population_change(genome, current.biomass, conditions, self.params)
        biomass = max(0.0, current.biomass + d_biomass)

        # CATÁSTROFE (Q8, ADR 0019): remove uma fração da comunidade SEM olhar
        # para o genoma dela. Não passa por `local_suitability`, não é atenuada
        # por adaptação, não poupa quem está no próprio ótimo — é o que torna
        # possível uma espécie bem adaptada ser extinta por um meteoro.
        #
        # Aplicada AQUI, e não na Ecology, porque a biomassa TOTAL é desta fatia:
        # tirá-la na Ecology faria a soma trófica descolar do total e a ecologia
        # virar um segundo sumidouro (a invariante que o M3 fixou).
        if conditions.catastrophe > 0.0:
            biomass = max(0.0, biomass * (1.0 - min(1.0, conditions.catastrophe)))

        # A média DERIVA na direção do ótimo local: quem está mais perto dele
        # deixa mais descendência, e o traço médio segue. Não há alvo global —
        # o ótimo é o do ambiente de AGORA, e muda quando ele muda.
        drifted = mutate(genome, ctx.rng, self.params)
        toward = _toward_local_optimum(genome, drifted, conditions, self.params)

        events = self._notable(ctx, current, genome, toward, biomass, suitability, conditions)

        values: dict[str, float] = {"biomass": biomass - current.biomass}
        values.update(
            {
                f"mean_{name}": float(getattr(toward, name)) - float(getattr(genome, name))
                for name in _TRAITS
            }
        )
        richness = _richness_change(current, biomass, genome, toward, self.params)
        if richness:
            values["species_richness"] = richness

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values=values,
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=max(1, int(current.species_richness)),
        )

    def _notable(
        self,
        ctx: TickContext,
        current: BiotaSlice,
        genome: Genome,
        drifted: Genome,
        biomass: float,
        suitability: float,
        conditions: LocalConditions,
    ) -> tuple[DomainEvent, ...]:
        """Traduz o tick em ocorrências notáveis — granularidade AGREGADA (§Corr.2)."""
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []

        # Extinção: a comunidade deixou de se sustentar. A CAUSA é diagnosticada
        # do fator local mais limitante — é ela que o Tutor traduz em explicação.
        if current.biomass > self.params.extinction_population >= biomass:
            cause = _limiting_cause(genome, conditions, self.params)
            events.append(
                emitter.emit(
                    SPECIES_EXTINCT,
                    cause,
                    location={"region_id": "global"},
                    participants=["species:community"],
                    environmental_factors=[_factor_of(cause)],
                    genes=list(_TRAITS),
                    resources=["biomass"],
                    cause_detail={
                        "biomass": biomass,
                        "biomass_before": current.biomass,
                        "suitability": suitability,
                        "temperature": conditions.temperature,
                        "thermal_match": thermal_match(genome, conditions.temperature),
                        "carrying_capacity": conditions.carrying_capacity,
                    },
                    # A cadeia aponta para o EVENTO quando a causa é
                    # catastrófica, e para o CLIMA quando é ecológica. É o elo
                    # que liga `MeteorImpact` a `SpeciesExtinct` e que o Tutor
                    # percorre (ADR 0019).
                    #
                    # Encadear uma morte por meteoro ao `TemperatureShift` faria
                    # o Tutor narrar a extinção como intolerância térmica — a
                    # concepção equivocada que este marco existe para desfazer,
                    # reintroduzida pela própria trilha causal.
                    causation_id=(
                        ctx.caused_by_slice(SliceRef.EVENT)
                        if cause is EvolutionCauseCode.CATASTROPHIC_EVENT
                        else ctx.caused_by_slice(SliceRef.CLIMATE)
                        or ctx.caused_by_slice(SliceRef.RESOURCE)
                    ),
                )
            )
            return tuple(events)

        # Mortandade em massa: a comunidade encolheu além do limiar declarado sem
        # se extinguir. É TRAVESSIA (compara antes e depois), não estado — e é o
        # caso que de fato acontece quando o ambiente vira contra a vida.
        if current.biomass > 0.0:
            lost = (current.biomass - biomass) / current.biomass
            if lost >= self.params.mass_mortality_threshold:
                cause = _limiting_cause(genome, conditions, self.params)
                events.append(
                    emitter.emit(
                        MASS_MORTALITY,
                        cause,
                        location={"region_id": "global"},
                        participants=["species:community"],
                        environmental_factors=[_factor_of(cause)],
                        genes=list(_TRAITS),
                        resources=["biomass"],
                        cause_detail={
                            "biomass": biomass,
                            "biomass_before": current.biomass,
                            "lost_fraction": lost,
                            "suitability": suitability,
                            "temperature": conditions.temperature,
                            "thermal_match": thermal_match(genome, conditions.temperature),
                            "carrying_capacity": conditions.carrying_capacity,
                        },
                        # A cadeia aponta para o EVENTO quando a causa é
                        # catastrófica — é o elo que liga MeteorImpact a
                        # SpeciesExtinct e o que o Tutor percorre (ADR 0019).
                        causation_id=(
                            ctx.caused_by_slice(SliceRef.EVENT)
                            if cause is EvolutionCauseCode.CATASTROPHIC_EVENT
                            else ctx.caused_by_slice(SliceRef.CLIMATE)
                            or ctx.caused_by_slice(SliceRef.RESOURCE)
                        ),
                    )
                )

        if has_speciated(drifted, genome, self.params):
            events.append(
                emitter.emit(
                    SPECIATION_OCCURRED,
                    EvolutionCauseCode.GENETIC_DIVERGENCE,
                    location={"region_id": "global"},
                    participants=["species:community"],
                    genes=list(_TRAITS),
                    resources=["biomass"],
                    cause_detail={
                        "distance": drifted.distance(genome),
                        "biomass": biomass,
                        **{f"gene_{k}": v for k, v in drifted.to_dict().items()},
                    },
                    causation_id=ctx.caused_by_slice(SliceRef.RESOURCE),
                )
            )

        shift = abs(drifted.temp_optimum - genome.temp_optimum)
        if shift >= self.params.trait_shift_threshold:
            events.append(
                emitter.emit(
                    TRAIT_SHIFT,
                    EvolutionCauseCode.DIRECTIONAL_SELECTION,
                    location={"region_id": "global"},
                    participants=["species:community"],
                    genes=["gene:temp_optimum"],
                    environmental_factors=["climate:temperature"],
                    cause_detail={
                        "trait": "temp_optimum",
                        "before": genome.temp_optimum,
                        "after": drifted.temp_optimum,
                        "temperature": conditions.temperature,
                    },
                    causation_id=events[0].event_id
                    if events
                    else ctx.caused_by_slice(SliceRef.CLIMATE),
                )
            )
        return tuple(events)


def _toward_local_optimum(
    genome: Genome,
    drifted: Genome,
    conditions: LocalConditions,
    params: EvolutionEngineParams,
) -> Genome:
    """Fica com a variante que se sustenta MELHOR nas condições de agora.

    Isto é seleção, não otimização: a comparação é entre a coorte e a variante
    dela mesma, contra o MESMO ambiente local — não entre espécies, nem contra um
    ótimo global, nem por ranking. Se o ambiente mudar, a escolha muda com ele.
    """
    if local_suitability(drifted, conditions, params) > local_suitability(
        genome, conditions, params
    ):
        return drifted
    return genome


def _richness_change(
    current: BiotaSlice,
    biomass: float,
    genome: Genome,
    drifted: Genome,
    params: EvolutionEngineParams,
) -> float:
    """Riqueza sobe por especiação e cai quando a comunidade colapsa."""
    if biomass <= params.extinction_population:
        return -current.species_richness
    if has_speciated(drifted, genome, params) and current.species_richness < params.max_species:
        return 1.0
    return 0.0


def _limiting_cause(
    genome: Genome, conditions: LocalConditions, params: EvolutionEngineParams
) -> EvolutionCauseCode:
    """Qual fator local matou a comunidade — o mais escasso, pela lei do mínimo.

    Nomear a causa é o que o Tutor consome; um `SpeciesExtinct` sem causa
    estruturada obrigaria o consumidor a recalcular ciência para explicar.
    """
    # A catástrofe vem PRIMEIRO, e não como mais um candidato a limitante: se
    # uma estava ativa quando a população cruzou o piso, foi ela que matou —
    # independentemente de quão bem adaptada a comunidade estivesse. Ordenar
    # assim é o que impede o diagnóstico de atribuir a um meteoro a "culpa" de
    # uma intolerância térmica que a comunidade nem chegou a sofrer.
    if conditions.catastrophe > 0.0:
        return EvolutionCauseCode.CATASTROPHIC_EVENT

    thermal = thermal_match(genome, conditions.temperature)
    predation = params.predation_weight * max(0.0, conditions.predation_pressure)
    resource_gap = 1.0 - min(1.0, conditions.carrying_capacity / max(1.0, conditions.occupied))

    if predation > maintenance_cost(genome, params) and predation > (1.0 - thermal):
        return EvolutionCauseCode.PREDATION_PRESSURE
    if thermal < 0.5:
        return EvolutionCauseCode.THERMAL_INTOLERANCE
    if resource_gap > 0.0 or conditions.carrying_capacity <= 0.0:
        return EvolutionCauseCode.RESOURCE_SCARCITY
    return EvolutionCauseCode.RESOURCE_SCARCITY


def _factor_of(cause: EvolutionCauseCode) -> str:
    """Referência ao fator ambiental (refs, não cópias — envelope §4)."""
    return {
        EvolutionCauseCode.THERMAL_INTOLERANCE: "climate:temperature#extreme",
        EvolutionCauseCode.PREDATION_PRESSURE: "ecology:predation#high",
        EvolutionCauseCode.RESOURCE_SCARCITY: "resource:carrying_capacity#low",
        EvolutionCauseCode.CATASTROPHIC_EVENT: "event:catastrophe#active",
    }.get(cause, "resource:carrying_capacity#low")
