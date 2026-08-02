"""Montagem do planeta: registra os oito Engines e costura com os casos de uso.

Mora AQUI, e não em `engines/planet/`, de propósito: o Planet Engine não conhece
Engine algum — orquestra o que lhe entregam. Um contrato de import-linter faz
disso um erro de build. Este módulo é o oposto: ele conhece todos, e é o único
dentro de `engines/` que conhece.

`FrameworkTickOrchestrator` oferece a MESMA superfície do `Ticker` (`tick`,
`bounds`, `subsystem_names`) mas roda o tick pelo Planet Engine. Com isso, o
caminho de produção troca UM objeto na raiz de composição: nenhum caso de uso,
rota ou repositório muda de assinatura.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ecosfera_ai.engines.astronomy.service import AstronomyEngine
from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.chemistry.service import ChemistryEngine
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.ecology.service import EcologyEngine
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.engine import Engine, EngineGraphError, TickBudget
from ecosfera_ai.shared_kernel.observability import ObservabilitySink
from ecosfera_ai.shared_kernel.world_state import (
    BoundedFraction,
    ConservedTotal,
    Invariant,
    NonNegativeStocks,
    SliceRef,
)
from ecosfera_ai.simulation_engine.orchestrator import TickResult
from ecosfera_ai.simulation_engine.params import SimulationParams
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds

# Ordem canônica de acoplamento do tick (Spec §5.3, ADR 0012/0013). Cada posição
# tem uma razão física:
#
# 1. astronomy — a irradiância é a ENTRADA DE ENERGIA de tudo abaixo; não depende
#    de ninguém, e por isso abre.
# 2. geology   — desgaseifica o CO2 e expõe relevo ao intemperismo.
# 3. chemistry — consome o relevo recém-exposto e publica a troca ar<->oceano.
# 4. atmosphere— integra o estoque de carbono já debitado da troca com o oceano.
# 5. climate   — converte forçamento e insolação em temperatura.
# 6. hydrology — move a água segundo o calor recém-resolvido.
# 7. resource  — traduz o ambiente fechado em capacidade de suporte.
# 8. evolution — a comunidade se sustenta (ou não) nas condições que encontra e
#    gasta o orçamento; o genoma médio deriva na direção do ótimo LOCAL.
# 9. ecology   — reparte essa biomassa entre níveis tróficos e resolve a predação;
#    fecha o tick porque precisa da comunidade já resolvida (ADR 0016).
#
# A ordem é DADO verificável, não convenção implícita: `validate_graph` recusa no
# boot qualquer leitura para trás que não esteja declarada em `lagged_reads`.
#
# `ENGINE_ORDER` é a ÚNICA fonte da ordem — `build_planet_engine` instancia a
# partir dela. Manter uma lista de construtores em paralelo faria da constante
# mera documentação, que aqui é pior que nada: ela seguiria descrevendo uma ordem
# que o tick deixou de obedecer, e todo teste escrito contra ela passaria a
# atestar uma ficção. Trocar de posição aqui muda o tick de verdade.
ENGINE_ORDER: tuple[str, ...] = (
    "astronomy",
    "geology",
    "chemistry",
    "atmosphere",
    "climate",
    "hydrology",
    "resource",
    "evolution",
    "ecology",
)

# Construtores por identificador. O `engine_id` de cada Engine é o que casa com a
# chave — `_engines_in_order` confere isso no boot, para que um rename silencioso
# não desmonte a correspondência entre nome e posição.
_ENGINE_FACTORIES: Mapping[str, Callable[[], Engine]] = {
    "astronomy": AstronomyEngine,
    "geology": GeologyEngine,
    "chemistry": ChemistryEngine,
    "atmosphere": AtmosphereEngine,
    "climate": ClimateEngine,
    "hydrology": HydrologyEngine,
    "resource": ResourceEngine,
    "evolution": EvolutionEngine,
    "ecology": EcologyEngine,
}


def _engines_in_order() -> list[Engine]:
    """Instancia os Engines na ordem canônica, conferindo os identificadores."""
    missing = set(ENGINE_ORDER) - set(_ENGINE_FACTORIES)
    if missing:
        raise EngineGraphError(f"sem construtor para o(s) Engine(s): {sorted(missing)}")
    orphan = set(_ENGINE_FACTORIES) - set(ENGINE_ORDER)
    if orphan:
        raise EngineGraphError(f"Engine construído mas fora da ordem do tick: {sorted(orphan)}")

    engines = [_ENGINE_FACTORIES[name]() for name in ENGINE_ORDER]
    for name, engine in zip(ENGINE_ORDER, engines, strict=True):
        if engine.engine_id != name:
            raise EngineGraphError(
                f"a ordem do tick nomeia {name!r}, mas o Engine se identifica como "
                f"{engine.engine_id!r}: a posição deixaria de significar o que diz"
            )
    return engines


def planet_invariants(bounds: StateBounds, *, water_tolerance: float) -> tuple[Invariant, ...]:
    """Invariantes por fatia (Spec §3), com as faixas físicas versionadas.

    A conservação da água é a novidade do M2. Ela não corrige nada — apenas
    REGISTRA que a soma se moveu além da tolerância declarada, e o registro sobe
    pelo Canal B como `DiagnosticEvent`. Reparar automaticamente esconderia o
    defeito exatamente onde ele precisa ser visto.

    **Por que não há invariante de carbono aqui.** O carbono NÃO é conservado
    tick a tick neste modelo: tem uma fonte (desgaseificação vulcânica) e um
    sumidouro (absorção biótica), ambos legítimos. O que precisa valer é a
    identidade contábil da troca ar<->oceano — o que sai da atmosfera entra no
    oceano, sem sobrar nem faltar. Isso atravessa DUAS fatias com donos
    diferentes, e uma invariante que roda por delta, sobre uma fatia, não tem
    como enxergá-lo. Verificar por delta composto exigiria que o Planet Engine
    soubesse qual termo é fonte e qual é troca, isto é, que ele contivesse
    ciência — o que o ADR-ARCH-0001 proíbe.

    A identidade é verificada em teste de integração
    (`test_carbon_is_not_double_counted`), que é onde uma afirmação sobre a
    contabilidade ENTRE Engines pertence (ADR 0012).
    """
    return (
        NonNegativeStocks(
            {
                SliceRef.ASTRONOMY: ("solar_flux",),
                SliceRef.ATMOSPHERE: ("co2", "pressure"),
                SliceRef.GEOLOGY: ("volcanism", "co2_flux"),
                SliceRef.CLIMATE: ("energy",),
                SliceRef.HYDROLOGY: ("ocean", "ice", "vapour", "freshwater", "salinity"),
                SliceRef.CHEMISTRY: (
                    "ocean_carbon",
                    "soil_carbon",
                    "nitrogen",
                    "phosphorus",
                    "sulfur",
                    "nutrients",
                ),
                SliceRef.RESOURCE: (
                    "water_available",
                    "nutrients_available",
                    "energy_available",
                    "carrying_capacity",
                ),
                SliceRef.BIOTA: ("biomass", "species_richness"),
                SliceRef.ECOLOGY: (
                    "producer_biomass",
                    "herbivore_biomass",
                    "predator_biomass",
                    "total_population",
                ),
            }
        ),
        BoundedFraction(
            {SliceRef.HYDROLOGY: ("ice_fraction",)},
            low=bounds.ice_cover_min,
            high=bounds.ice_cover_max,
        ),
        BoundedFraction(
            {SliceRef.GEOLOGY: ("relief",)}, low=bounds.relief_min, high=bounds.relief_max
        ),
        BoundedFraction(
            {SliceRef.HYDROLOGY: ("ocean_circulation",)},
            low=bounds.ocean_circulation_min,
            high=bounds.ocean_circulation_max,
        ),
        # Água: os fluxos apenas MOVEM massa entre reservatórios, nunca a criam.
        ConservedTotal(
            name="water_conservation",
            slice_ref=SliceRef.HYDROLOGY,
            fields=("ocean", "ice", "vapour", "freshwater"),
            tolerance=water_tolerance,
        ),
    )


def build_planet_engine(
    params: SimulationParams,
    *,
    budget: TickBudget | None = None,
    sink: ObservabilitySink | None = None,
) -> PlanetEngine:
    """Registra os Engines na ordem canônica de acoplamento (`ENGINE_ORDER`).

    Não há mais adaptador nem fatia sem dono: desde o M2 TODA grandeza do
    world-state é escrita por um Engine (ADR 0014).
    """
    registry = EngineRegistry.of(_engines_in_order())
    # A tolerância é propriedade DECLARADA do Engine que detém a grandeza, e mora
    # no YAML dele — não num bloco global que ninguém saberia manter em dia.
    invariants = planet_invariants(
        params.bounds, water_tolerance=hydrology_params().conservation_tolerance
    )
    return PlanetEngine(registry, invariants=invariants, budget=budget, sink=sink)


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
        """Ordem de execução real — Engines, não mais subsistemas."""
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
            # Canal B do tick, repassado ao consumidor. Só a visão CIENTÍFICA: o
            # diagnóstico técnico (orçamento, invariante) é do desenvolvedor e
            # nunca chega ao aluno (ADR-ARCH-0002).
            events=tuple(e for e in outcome.events if not e.is_diagnostic),
        )
