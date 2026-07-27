"""LLM no-op usado até o Inc 6. Mantém a porta satisfeita sem dependência de Ollama."""

from __future__ import annotations


class NullLLM:
    async def is_available(self) -> bool:
        return False

    async def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        raise RuntimeError("LLM não habilitado neste incremento (ver ADR 0002).")
