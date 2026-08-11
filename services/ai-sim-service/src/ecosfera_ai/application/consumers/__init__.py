"""Casos de uso da camada de CONSUMIDORES read-side (Spec §1, §2).

Assinam o Event Store pelo contrato de leitura do M5 e nunca alcançam o
world-state nem os Engines de simulação — fronteira verificada pelo
`import-linter`, não confiada à disciplina de quem escreve.
"""

from __future__ import annotations

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler

__all__ = ["ContextAssembler"]
