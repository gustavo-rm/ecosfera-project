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
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.engines.geology.contracts import load_params as geology_params
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.observability import ObservabilitySink
from ecosfera_ai.simulation_engine.params import SimulationParams, load_params

PARAMS_PATH = Path("configs/simulation_params.yaml")


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


def scripted_event_engine(kind: EventKind, *, lead: int = 3) -> EventEngine:
    """Event Engine que agenda SEMPRE o mesmo evento — cenário declarado.

    O Diretor sorteia, e sorteio não serve de fixture: um teste que espera o
    meteoro cair na janela certa passa ou falha por semente, não por regressão.
    Aqui a probabilidade vai a 1 e o catálogo fica com um evento só, então o
    QUE acontece é declarado e o QUANDO é previsível. É o mesmo princípio do
    `build_volcanic_planet` do M2.
    """
    base = event_params()
    profile = base.catalog[kind]
    return EventEngine(
        replace(
            base,
            scheduling_probability=1.0,
            quiet_ticks_after=0,
            catalog={kind: replace(profile, forecast_lead=lead)},
        )
    )


def build_scripted_planet(
    kind: EventKind, *, lead: int = 3, sink: ObservabilitySink | None = None
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
        scripted_event_engine(kind, lead=lead),
    ]
    return PlanetEngine(
        EngineRegistry.of(engines),
        invariants=planet_invariants(
            params.bounds, water_tolerance=hydrology_params().conservation_tolerance
        ),
        budget=params.engine_budget,
        sink=sink,
    )
