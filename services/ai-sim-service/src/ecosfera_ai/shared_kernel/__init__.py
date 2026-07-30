"""Moldura comum de Engines: contratos que todo Engine de simulação partilha.

Reúne o que a Spec do Framework define como comum (ADR-ARCH-0001, Emenda 4):
world-state e deltas (§3), envelope de evento (§4), porta `Engine` e contexto de
tick (§5.2), RNG semeado, contrato de observabilidade (§6) e replay (§7).

Este pacote é **puro**: não importa `infrastructure` nem `interfaces`, e nenhum
Engine importa outro. As duas regras são verificadas por `import-linter` no
pipeline de qualidade (`make lint-imports`).
"""

from ecosfera_ai.shared_kernel.engine import (
    Engine,
    EngineGraphError,
    PerfSample,
    TickBudget,
    TickContext,
    TickResult,
    validate_graph,
)
from ecosfera_ai.shared_kernel.events import (
    CauseCodeEnum,
    CoreCauseCode,
    DomainEvent,
    EventEmitter,
    Granularity,
    SimulationTime,
    deterministic_id,
    diagnostic_event,
)
from ecosfera_ai.shared_kernel.observability import (
    CompositeSink,
    InMemoryEventStore,
    NullSink,
    ObservabilitySink,
    PrometheusMetricsSink,
    StructlogSink,
)
from ecosfera_ai.shared_kernel.replay import ReplayReport, StepOutcome, replay, verify_replay
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    BoundedFraction,
    Invariant,
    InvariantBreach,
    NonNegativeStocks,
    SliceRef,
    StateDelta,
    WorldStateSnapshot,
    compose,
)

__all__ = [
    "BoundedFraction",
    "CauseCodeEnum",
    "CompositeSink",
    "CoreCauseCode",
    "DomainEvent",
    "Engine",
    "EngineGraphError",
    "EventEmitter",
    "Granularity",
    "InMemoryEventStore",
    "Invariant",
    "InvariantBreach",
    "NonNegativeStocks",
    "NullSink",
    "ObservabilitySink",
    "PerfSample",
    "PrometheusMetricsSink",
    "ReplayReport",
    "SimulationTime",
    "SliceRef",
    "StateDelta",
    "StepOutcome",
    "StructlogSink",
    "TickBudget",
    "TickContext",
    "TickResult",
    "WorldStateSnapshot",
    "compose",
    "deterministic_id",
    "diagnostic_event",
    "replay",
    "rng_for",
    "validate_graph",
    "verify_replay",
]
