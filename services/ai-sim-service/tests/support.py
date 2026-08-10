"""Montagem do motor para os testes — um lugar só, e não um por arquivo.

Antes do M2 os testes chamavam `build_orchestrator(params)`, a fábrica do
`TickOrchestrator` monolítico. Ele foi removido junto com o adaptador legado
(ADR 0014), e o motor passou a ser sempre o mesmo: os oito Engines pelo Planet
Engine.

Centralizar aqui não é conveniência: enquanto cada teste montava o próprio
orquestrador, mudar a composição exigia tocar em quinze arquivos, e um deles
inevitavelmente ficaria para trás montando um motor que a produção não usa mais.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ecosfera_ai.engines.astronomy.service import AstronomyEngine
from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.chemistry.service import ChemistryEngine
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.composition import (
    FrameworkTickOrchestrator,
    build_planet_engine,
    planet_invariants,
)
from ecosfera_ai.engines.ecology.service import EcologyEngine
from ecosfera_ai.engines.event.contracts import load_params as event_params
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.engines.event.service import EventEngine
from ecosfera_ai.engines.evolution.contracts import load_params as evolution_params
from ecosfera_ai.engines.evolution.events import SPECIATION_OCCURRED
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.engines.geology.contracts import load_params as geology_params
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import ObservabilitySink
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    BiotaSlice,
    ClimateSlice,
    EcologySlice,
    EventSlice,
    ResourceSlice,
    WorldStateSnapshot,
)
from ecosfera_ai.simulation_engine.biology.genome import Genome
from ecosfera_ai.simulation_engine.params import SimulationParams, load_params

PARAMS_PATH = Path("configs/simulation_params.yaml")

TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")


def test_params() -> SimulationParams:
    """Os parâmetros versionados de produção — testar outros testaria outra coisa."""
    return load_params(PARAMS_PATH)


def build_orchestrator(
    params: SimulationParams, *, sink: ObservabilitySink | None = None
) -> FrameworkTickOrchestrator:
    """O motor de produção: oito Engines na ordem canônica (ADR 0012/0013)."""
    planet = build_planet_engine(params, budget=params.engine_budget, sink=sink)
    return FrameworkTickOrchestrator(planet, params.bounds)


def build_volcanic_planet(sink: ObservabilitySink | None = None) -> PlanetEngine:
    """Um planeta VULCANICAMENTE ATIVO — cenário declarado, não sorteado.

    A cadeia erupção→forçamento→clima é uma propriedade ESTRUTURAL (os Engines se
    encadeiam por `causation_id` sem se conhecerem), mas só é OBSERVÁVEL quando os
    três elos disparam. Esperar que a trajetória aleatória de um planeta calmo
    produza os três é um sorteio: os pulsos tectônicos são estocásticos, e desde
    que o oceano passou a amortecer o carbono (ADR 0012) as travessias de faixa de
    forçamento ficaram raras na linha de base.

    Declarar o cenário torna o teste determinístico quanto ao FENÔMENO, e não
    apenas quanto à semente. É a mesma composição de produção — só os parâmetros
    da geologia mudam, exatamente como num planeta diferente.
    """
    params = test_params()
    engines = [
        AstronomyEngine(),
        GeologyEngine(
            replace(
                geology_params(),
                tectonic_activity=0.35,
                volcanism_baseline=2.0,
                outgassing_base=9.0,
            )
        ),
        ChemistryEngine(),
        AtmosphereEngine(),
        ClimateEngine(),
        HydrologyEngine(),
        ResourceEngine(),
        EvolutionEngine(),
        EcologyEngine(),
        EventEngine(),
    ]
    return PlanetEngine(
        EngineRegistry.of(engines),
        invariants=planet_invariants(
            params.bounds, water_tolerance=hydrology_params().conservation_tolerance
        ),
        budget=params.engine_budget,
        sink=sink,
    )


def quiet_event_engine() -> EventEngine:
    """Event Engine com o Diretor MUDO: nunca agenda nada.

    A linha de base do planeta é FÍSICA — o que ela afirma é que nada se move sem
    causa. Um evento extraordinário é, por definição, uma causa: deixar o Diretor
    sorteando durante o teste de quase-estacionariedade mediria outra coisa (que
    um supervulcão injeta carbono, o que já é afirmado em outro lugar) e a
    baseline passaria a falhar por semente, não por regressão.

    O Engine continua no registro — a fatia precisa de dono e a ordem do tick não
    muda. O que se silencia é a DECISÃO, não a moldura.
    """
    return EventEngine(replace(event_params(), scheduling_probability=0.0))


def build_quiet_planet() -> PlanetEngine:
    """Composição de produção, com o Diretor mudo (linha de base física)."""
    params = test_params()
    engines = [
        AstronomyEngine(),
        GeologyEngine(),
        ChemistryEngine(),
        AtmosphereEngine(),
        ClimateEngine(),
        HydrologyEngine(),
        ResourceEngine(),
        EvolutionEngine(),
        EcologyEngine(),
        quiet_event_engine(),
    ]
    return PlanetEngine(
        EngineRegistry.of(engines),
        invariants=planet_invariants(
            params.bounds, water_tolerance=hydrology_params().conservation_tolerance
        ),
        budget=params.engine_budget,
    )


def scripted_event_engine(
    kind: EventKind, *, lead: int = 3, mortality: float | None = None
) -> EventEngine:
    """Event Engine que agenda SEMPRE o mesmo evento — cenário declarado.

    O Diretor sorteia, e sorteio não serve de fixture: um teste que espera o
    meteoro cair na janela certa passa ou falha por semente, não por regressão.
    Aqui a probabilidade vai a 1 e o catálogo fica com um evento só, então o
    QUE acontece é declarado e o QUANDO é previsível. É o mesmo princípio do
    `build_volcanic_planet` do M2.
    """
    base = event_params()
    profile = base.catalog[kind]
    if mortality is not None:
        # Severidade DECLARADA. O catálogo de produção calibra o meteoro para
        # ferir sem aniquilar, que é o certo para o jogo; um teste da cadeia
        # meteoro->EXTINÇÃO precisa do caso letal, e esperá-lo do sorteio seria
        # voltar à loteria que este helper existe para evitar.
        profile = replace(profile, mortality=mortality)
    return EventEngine(
        replace(
            base,
            scheduling_probability=1.0,
            quiet_ticks_after=0,
            catalog={kind: replace(profile, forecast_lead=lead)},
        )
    )


def build_scripted_planet(
    kind: EventKind,
    *,
    lead: int = 3,
    mortality: float | None = None,
    sink: ObservabilitySink | None = None,
) -> PlanetEngine:
    """Composição de produção com um evento DECLARADO no lugar do sorteio."""
    params = test_params()
    engines = [
        AstronomyEngine(),
        GeologyEngine(),
        ChemistryEngine(),
        AtmosphereEngine(),
        ClimateEngine(),
        HydrologyEngine(),
        ResourceEngine(),
        EvolutionEngine(),
        EcologyEngine(),
        scripted_event_engine(kind, lead=lead, mortality=mortality),
    ]
    return PlanetEngine(
        EngineRegistry.of(engines),
        invariants=planet_invariants(
            params.bounds, water_tolerance=hydrology_params().conservation_tolerance
        ),
        budget=params.engine_budget,
        sink=sink,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Especiação sob demanda (Fase 0, BIO-001/BIO-002)
#
# Com o limiar de produção (0,12) a especiação é praticamente INALCANÇÁVEL num
# tick: a distância de um único passo de mutação vale ~0,02, e chegar a 0,12
# exigiria um desvio de ~6 sigma. Esperá-la de uma corrida seria esperar um
# sorteio, e um teste que depende de sorteio não afirma nada.
#
# O limiar entra como PARÂMETRO — é dado versionado, e baixá-lo num teste é a
# mesma técnica de `build_volcanic_planet`: declarar o cenário em vez de torcer
# por ele. A mecânica sob teste continua sendo a de produção.
#
# Que o evento seja raro com o limiar real é dívida DECLARADA do BIO-002
# (mecânica gradual, pós-M6), registrada no ADR 0023 — não algo que esta fase
# conserta, e não algo que este helper esconde.
# ─────────────────────────────────────────────────────────────────────────────


def community_genome(**over: float) -> Genome:
    """Genoma médio de uma comunidade acomodada, com os desvios que se pedir."""
    base = {
        "temp_optimum": 20.0,
        "temp_tolerance": 15.0,
        "water_need": 0.2,
        "size": 1.0,
        "metabolism": 1.0,
        "trophic_level": 1.0,
    }
    return Genome(**{**base, **over}).clamped()


def speciation_snapshot(
    genome: Genome | None = None,
    *,
    seed: int = 2027,
    tick: int = 7,
    temperature: float = 20.0,
    capacity: float = 500.0,
    biomass: float = 40.0,
) -> WorldStateSnapshot:
    """Um mundo onde a comunidade vive folgada — nada a matando, só divergindo.

    O ótimo térmico do residente fica DESLOCADO do ambiente de propósito. Com a
    comunidade exatamente no próprio ótimo, nenhuma variante mutada se sustenta
    melhor que ela (a adequação local depende só da distância ao ótimo), a
    seleção rejeita toda divergência e não há especiação alguma a observar —
    caso, aliás, cientificamente correto: sem gradiente não há para onde divergir.
    """
    resident = genome if genome is not None else community_genome(temp_optimum=26.0)
    return WorldStateSnapshot(
        planet_id="speciation",
        seed=seed,
        tick=tick,
        era=0,
        climate=ClimateSlice(temperature=temperature),
        resource=ResourceSlice(
            water_available=0.9,
            nutrients_available=1.0,
            energy_available=0.2,
            carrying_capacity=capacity,
        ),
        biota=BiotaSlice(
            biomass=biomass,
            species_richness=1.0,
            **{f"mean_{n}": float(getattr(resident, n)) for n in TRAITS},
        ),
        ecology=EcologySlice(),
        event=EventSlice(),
    )


def speciation_event(
    snapshot: WorldStateSnapshot | None = None,
    *,
    threshold: float = 0.005,
    tries: int = 64,
) -> DomainEvent:
    """Roda o Evolution Engine até uma `SpeciationOccurred` de fato sair.

    Cada tentativa é um tick diferente, logo um fluxo de RNG diferente: a
    divergência só vira evento quando a variante mutada se sustenta melhor que a
    ancestral, o que não acontece em todo passo.
    """
    world = snapshot if snapshot is not None else speciation_snapshot()
    engine = EvolutionEngine(replace(evolution_params(), speciation_threshold=threshold))
    params = test_params()
    for step in range(tries):
        tick = world.tick + step
        result = engine.tick(
            TickContext(
                snapshot=world,
                rng=rng_for(world.seed, engine.engine_id, tick),
                tick=tick,
                era=world.era,
                budget=params.engine_budget,
            )
        )
        for event in result.events:
            if event.event_type == SPECIATION_OCCURRED:
                return event
    raise AssertionError(
        f"nenhuma especiação em {tries} tentativas com limiar {threshold} — "
        "o cenário deixou de produzir divergência"
    )
