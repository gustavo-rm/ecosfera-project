"""Registro ordenado de Engines — sem descoberta mágica (Spec §5.3).

A ordem de execução é DADO explícito, não efeito colateral de import ou de
varredura de diretório. Um Engine só participa do tick se alguém o registrou, e
o grafo de dependências é validado no boot: erro de fronteira aparece ao subir o
serviço, não no meio de uma era.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ecosfera_ai.shared_kernel.engine import Engine, validate_graph
from ecosfera_ai.shared_kernel.world_state import SliceRef

# Ordem canônica de acoplamento da Spec §5.3. O registro real do M0 contém
# apenas os Engines que existem; a lista serve de referência para ordenar os que
# forem nascendo (M1/M2/M3) sem que a decisão vire folclore oral.
CANONICAL_ORDER: tuple[str, ...] = (
    "physics",
    "chemistry",
    "atmosphere",
    "climate",
    "geology",
    "hydrology",
    "resource",
    "evolution",
    "ecology",
    "event",
)


@dataclass(frozen=True, slots=True)
class EngineRegistry:
    """Lista imutável e validada dos Engines de um tick."""

    engines: tuple[Engine, ...]

    def __post_init__(self) -> None:
        validate_graph(self.engines)

    @classmethod
    def of(cls, engines: Sequence[Engine]) -> EngineRegistry:
        """Constrói o registro na ordem recebida (a ordem É a decisão)."""
        return cls(tuple(engines))

    @property
    def engine_ids(self) -> tuple[str, ...]:
        """Identificadores na ordem de execução — torna a ordem testável."""
        return tuple(engine.engine_id for engine in self.engines)

    @property
    def owned_slices(self) -> dict[SliceRef, str]:
        """Mapa fatia -> Engine dono, útil para diagnóstico e documentação."""
        return {engine.writes: engine.engine_id for engine in self.engines}
