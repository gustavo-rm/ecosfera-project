"""Montagem da fatia vertical do M1 e a costura com os casos de uso existentes.

`FrameworkTickOrchestrator` oferece a MESMA superfície do `TickOrchestrator`
(`tick`, `bounds`, `subsystem_names`) mas roda o tick pelo Planet Engine. Com
isso, o caminho de produção troca UM objeto na raiz de composição: nenhum caso de
uso, rota ou repositório muda de assinatura.
"""

from __future__ import annotations

from dataclasses import replace

from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.legacy.adapter import LegacySubsystemAdapter
from ecosfera_ai.engines.legacy.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.shared_kernel.engine import TickBudget
from ecosfera_ai.shared_kernel.observability import ObservabilitySink
from ecosfera_ai.shared_kernel.world_state import (
    BoundedFraction,
    Invariant,
    NonNegativeStocks,
    SliceRef,
)
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator, TickResult
from ecosfera_ai.simulation_engine.params import SimulationParams
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds
from ecosfera_ai.simulation_engine.subsystems.base import Subsystem

# Subsistemas que sobraram no adaptador legado depois do M1. `geology` e
# `climate` saíram (viraram Engines); `chemistry` continua, mas só com o ciclo
# da água — o carbono migrou para a Atmosphere.
from ecosfera_ai.simulation_engine.subsystems.chemistry import ChemistrySubsystem
from ecosfera_ai.simulation_engine.subsystems.life import LifeSubsystem
from ecosfera_ai.simulation_engine.subsystems.ocean import OceanSubsystem
from ecosfera_ai.simulation_engine.subsystems.physics import PhysicsSubsystem


def reduced_params(params: SimulationParams) -> SimulationParams:
    """Zera na ORIGEM os termos cuja autoria migrou para os Engines do M1.

    Descartar o resultado no fim do tick não bastaria: o `life` legado roda
    depois do `chemistry` dentro do mesmo orquestrador e leria um CO2 fantasma,
    já somado e ainda não descartado. Zerando o parâmetro, o termo simplesmente
    não existe — a ciência foi MOVIDA, não duplicada nem mascarada (ADR 0010).
    """
    return replace(
        params,
        chemistry=replace(
            params.chemistry,
            # Ciclo do carbono inteiro -> Atmosphere Engine.
            outgassing=0.0,
            volcanism_sensitivity=0.0,
            carbon_uptake_coeff=0.0,
            weathering_coeff=0.0,
        ),
        # Sequestro de calor -> Climate Engine (temperatura tem um dono só).
        ocean=replace(params.ocean, heat_uptake=0.0),
    )


def build_legacy_orchestrator(params: SimulationParams) -> TickOrchestrator:
    """Monta só os subsistemas que o M1 não migrou, com os termos reduzidos."""
    reduced = reduced_params(params)
    subsystems: list[Subsystem] = [
        PhysicsSubsystem(reduced.physics),
        ChemistrySubsystem(reduced.chemistry),
        OceanSubsystem(reduced.ocean),
        LifeSubsystem(reduced.life),
    ]
    return TickOrchestrator(subsystems, reduced.bounds)


def m1_invariants(bounds: StateBounds) -> tuple[Invariant, ...]:
    """Invariantes por fatia, com as faixas físicas versionadas de sempre."""
    return (
        NonNegativeStocks(
            {
                SliceRef.ATMOSPHERE: ("co2", "pressure"),
                SliceRef.GEOLOGY: ("volcanism", "co2_flux"),
                SliceRef.CLIMATE: ("energy",),
                SliceRef.LEGACY: ("water", "biomass", "solar_flux", "salinity"),
            }
        ),
        BoundedFraction(
            {SliceRef.LEGACY: ("ice_cover",)},
            low=bounds.ice_cover_min,
            high=bounds.ice_cover_max,
        ),
        BoundedFraction(
            {SliceRef.GEOLOGY: ("relief",)}, low=bounds.relief_min, high=bounds.relief_max
        ),
        BoundedFraction(
            {SliceRef.LEGACY: ("ocean_circulation",)},
            low=bounds.ocean_circulation_min,
            high=bounds.ocean_circulation_max,
        ),
    )


def build_planet_engine(
    params: SimulationParams,
    *,
    budget: TickBudget | None = None,
    sink: ObservabilitySink | None = None,
) -> PlanetEngine:
    """Registra a fatia vertical do M1 na ordem de acoplamento geo→atmo→clima.

    A ordem é a decisão: a geologia desgaseifica, a atmosfera integra e irradia,
    o clima responde — tudo no MESMO tick, que é o que faz o feedback ser
    observável em vez de defasado. O adaptador legado fecha a fila porque lê as
    três fatias novas.
    """
    registry = EngineRegistry.of(
        [
            GeologyEngine(),
            AtmosphereEngine(),
            ClimateEngine(),
            LegacySubsystemAdapter(build_legacy_orchestrator(params)),
        ]
    )
    return PlanetEngine(registry, invariants=m1_invariants(params.bounds), budget=budget, sink=sink)


class FrameworkTickOrchestrator:
    """Dirige o Planet Engine com a interface que os casos de uso já esperam."""

    def __init__(self, planet: PlanetEngine, bounds: StateBounds, *, publish: bool = True) -> None:
        self._planet = planet
        self._bounds = bounds
        self._publish = publish

    def for_replay(self) -> FrameworkTickOrchestrator:
        """Variante que NÃO publica no Canal B — usada pela reconstrução de eras.

        Reconstruir uma era é reproduzir, não reocorrer. Sem isto, cada consulta
        a `GET /eras/{era}` reemitiria a trilha inteira daquela era no Event
        Store, e o Tutor passaria a ver erupções que nunca aconteceram duas
        vezes. O `stepper()` do Planet Engine já tinha essa proteção; o caminho
        pelo `Ticker` (que os casos de uso usam) não tinha.
        """
        return FrameworkTickOrchestrator(self._planet, self._bounds, publish=False)

    @property
    def bounds(self) -> StateBounds:
        return self._bounds

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        """Ordem de execução real — agora Engines, não mais subsistemas."""
        return self._planet.engine_ids

    @property
    def planet(self) -> PlanetEngine:
        """Acesso ao orquestrador da moldura (usado por replay e diagnóstico)."""
        return self._planet

    def tick(self, state: PlanetState) -> TickResult:
        outcome = self._planet.tick(snapshot_of(state), publish=self._publish)
        new_state = planet_state_of(outcome.snapshot)
        return TickResult(
            state=new_state,
            delta=new_state.delta_from(state),
            observations=new_state.observe(state),
        )
