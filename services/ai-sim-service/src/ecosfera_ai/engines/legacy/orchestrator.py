"""Costura entre a moldura e os casos de uso existentes (Escopo C do M0).

`FrameworkTickOrchestrator` oferece a MESMA superfície do `TickOrchestrator`
(`tick`, `bounds`, `subsystem_names`) mas roda o tick pelo Planet Engine. Com
isso, ligar a moldura é trocar UM objeto na raiz de composição: nenhum caso de
uso, rota ou repositório muda de assinatura.

As invariantes do M0 são construídas a partir das MESMAS faixas físicas que o
núcleo determinístico já aplica (`StateBounds`, dado versionado). Elas são, por
construção, no-ops no caminho legado — o núcleo já recortou antes. Isso é
proposital: prova que a máquina de invariantes roda no caminho real sem alterar
um número, que é exatamente a paridade que o M0 precisa demonstrar.
"""

from __future__ import annotations

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
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds

# Estoques que não podem ficar negativos, com o piso vindo de `StateBounds`.
_STOCK_FIELDS: tuple[tuple[str, str], ...] = (
    ("co2", "co2_min"),
    ("water", "water_min"),
    ("biomass", "biomass_min"),
    ("energy", "energy_min"),
    ("solar_flux", "solar_flux_min"),
    ("volcanism", "volcanism_min"),
    ("salinity", "salinity_min"),
)

# Grandezas confinadas a uma faixa fechada, idem.
_BOUNDED_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("ice_cover", "ice_cover_min", "ice_cover_max"),
    ("relief", "relief_min", "relief_max"),
    ("ocean_circulation", "ocean_circulation_min", "ocean_circulation_max"),
)


def legacy_invariants(bounds: StateBounds) -> tuple[Invariant, ...]:
    """Traduz as faixas físicas versionadas em invariantes da moldura."""
    by_floor: dict[float, list[str]] = {}
    for field_name, floor_attr in _STOCK_FIELDS:
        by_floor.setdefault(float(getattr(bounds, floor_attr)), []).append(field_name)

    invariants: list[Invariant] = [
        NonNegativeStocks({SliceRef.LEGACY: tuple(names)}, floor=floor)
        for floor, names in sorted(by_floor.items())
    ]
    invariants.extend(
        BoundedFraction(
            {SliceRef.LEGACY: (field_name,)},
            low=float(getattr(bounds, low_attr)),
            high=float(getattr(bounds, high_attr)),
        )
        for field_name, low_attr, high_attr in _BOUNDED_FIELDS
    )
    return tuple(invariants)


def build_planet_engine(
    orchestrator: TickOrchestrator,
    *,
    budget: TickBudget | None = None,
    sink: ObservabilitySink | None = None,
) -> PlanetEngine:
    """Monta o Planet Engine com o único Engine que o M0 tem: o legado."""
    registry = EngineRegistry.of([LegacySubsystemAdapter(orchestrator)])
    return PlanetEngine(
        registry,
        invariants=legacy_invariants(orchestrator.bounds),
        budget=budget,
        sink=sink,
    )


class FrameworkTickOrchestrator:
    """Dirige o Planet Engine com a interface que os casos de uso já esperam."""

    def __init__(self, legacy: TickOrchestrator, planet: PlanetEngine) -> None:
        self._legacy = legacy
        self._planet = planet

    @property
    def bounds(self) -> StateBounds:
        return self._legacy.bounds

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        return self._legacy.subsystem_names

    @property
    def planet(self) -> PlanetEngine:
        """Acesso ao orquestrador da moldura (usado por replay e diagnóstico)."""
        return self._planet

    def tick(self, state: PlanetState) -> TickResult:
        outcome = self._planet.tick(snapshot_of(state))
        new_state = planet_state_of(outcome.snapshot)
        return TickResult(
            state=new_state,
            delta=new_state.delta_from(state),
            observations=new_state.observe(state),
        )
