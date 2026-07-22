"""Porta de saída para o LLM. No MVP usa-se NullLLM; o adaptador Ollama entra no Inc 6.

Trocar de regras para LLM+RAG não altera as camadas superiores (Hexagonal): apenas
se injeta outro adaptador desta porta.
"""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    async def is_available(self) -> bool: ...
    async def generate(self, prompt: str, *, max_tokens: int = 512) -> str: ...
