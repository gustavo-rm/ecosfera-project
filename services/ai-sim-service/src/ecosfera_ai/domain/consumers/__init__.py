"""Modelos puros da camada de CONSUMIDORES read-side (Spec §1, ADR-ARCH-0001).

A Spec desenha os consumidores como uma camada própria
(`consumers/analytics|education|ai_tutor`). Este serviço os acomoda dentro da
estratificação hexagonal que ele de fato usa e que o `import-linter` verifica —
modelo puro em `domain/`, caso de uso em `application/` —, do mesmo jeito que já
fez com `platform/persistence` (que aqui é `infrastructure/persistence`) e com o
explicador de regras (`domain/feedback` + `application/feedback`).

Um pacote `consumers/` no topo seria o "pacote paralelo" que a estratificação
existe para evitar: uma segunda hierarquia com as mesmas responsabilidades, fora
dos contratos de camada. O que a Spec pede é a FRONTEIRA — consumidores só leem
o Event Store, nunca o world-state nem os Engines —, e essa fronteira é
verificada em `pyproject.toml`, não pelo nome do diretório.
"""

from __future__ import annotations

from ecosfera_ai.domain.consumers.causal_tree import (
    CausalNode,
    build_causal_forest,
    descendants_of,
)
from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    EraMarker,
    ExtinctionFact,
    ExtinctionNature,
    FactualContext,
    MalformedSpeciationError,
    SliceKind,
    SpeciationFact,
)

__all__ = [
    "CausalNode",
    "ContextSlice",
    "EraMarker",
    "ExtinctionFact",
    "ExtinctionNature",
    "FactualContext",
    "MalformedSpeciationError",
    "SliceKind",
    "SpeciationFact",
    "build_causal_forest",
    "descendants_of",
]
