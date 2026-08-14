"""Adaptador Ollama — a única coisa neste serviço que fala com um LLM.

`import-linter` garante a exclusividade: nenhum outro módulo alcança um cliente de
LLM. É o que permite ao M6.4 trocar a implementação por uma adversarial, e a
qualquer marco futuro trocar de modelo, sem tocar na lógica de ancoragem.

## Toda falha vira `None`, e nenhuma sobe

Rede caída, tempo esgotado, HTTP não-2xx, JSON malformado, corpo vazio: tudo é
capturado aqui e vira `None`, com o motivo em `last_failure` para quem registra.
Nada disso é erro do ponto de vista do produto — o sistema tem, o tempo todo, uma
explicação correta para entregar, que é o piso do M6.1. Deixar a exceção subir
transformaria indisponibilidade de infraestrutura em erro para o aluno.

## `stream: false` e `temperature` baixa

A resposta vem inteira: não há consumidor de streaming aqui, e o texto precisa
estar completo antes da verificação de fundamentação — publicar token a token
significaria mandar ao aluno prosa que ainda não passou pelo portão.

A temperatura é baixa porque a tarefa é REESCREVER um texto dado, não inventar.
Criatividade, nesta posição, é literalmente o modo de falha.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ecosfera_ai.application.generation.language_model import GenerationUnavailable
from ecosfera_ai.domain.generation.prompt import AnchoredPrompt

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2


class OllamaLanguageModel:
    """`LanguageModelPort` sobre a API HTTP do Ollama."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        temperature: float = DEFAULT_TEMPERATURE,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._client = client
        self.last_failure: str = ""

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: AnchoredPrompt) -> str | None:
        """Gera, ou devolve `None` com o motivo em `last_failure`."""
        self.last_failure = ""
        payload: dict[str, Any] = {
            "model": self._model,
            "system": prompt.system,
            "prompt": prompt.user,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        try:
            return await self._request(payload)
        except GenerationUnavailable as unavailable:
            self.last_failure = str(unavailable)
            return None
        except httpx.TimeoutException:
            self.last_failure = f"o modelo não respondeu em {self._timeout:.0f}s"
            return None
        except httpx.HTTPError as error:
            self.last_failure = f"falha de rede ao falar com o Ollama: {error}"
            return None

    async def _request(self, payload: dict[str, Any]) -> str:
        if self._client is not None:
            response = await self._client.post(
                f"{self._base_url}/api/generate", json=payload, timeout=self._timeout
            )
            return _text_of(response)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/generate", json=payload)
            return _text_of(response)


def _text_of(response: httpx.Response) -> str:
    """Extrai a prosa, tratando toda forma inesperada como indisponibilidade."""
    if response.status_code >= 400:
        raise GenerationUnavailable(
            f"o Ollama respondeu {response.status_code} — modelo ausente ou serviço indisponível"
        )
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError) as malformed:
        raise GenerationUnavailable(f"resposta do Ollama não é JSON: {malformed}") from malformed

    if not isinstance(body, dict):
        raise GenerationUnavailable("resposta do Ollama não é um objeto JSON")
    generated = body.get("response")
    if not isinstance(generated, str) or not generated.strip():
        raise GenerationUnavailable("o Ollama devolveu resposta vazia ou sem o campo 'response'")
    return generated.strip()


class NullLanguageModel:
    """O modelo desligado — `ECOSFERA_LLM_ENABLED=false`, o padrão até aqui.

    Sucede o `NullLLM` do MVP, que tinha porta própria (`LLMClient`), nenhum ponto
    de uso e uma assinatura de string crua com `max_tokens`. Manter as duas
    deixaria no serviço duas abstrações de LLM ao mesmo tempo, e a antiga trazia
    justamente a superfície de "peça qualquer coisa" que o contrato de ancoragem
    existe para não ter. Um porto declarado que ninguém exercita é a família de
    defeito que este serviço já pagou duas vezes (`atmosphere.oxygen`, o filtro
    fantasma de `planet_id`), então ele foi substituído, e não duplicado.

    Devolver `None` em vez de estourar é o que faz "LLM desligado" percorrer
    exatamente o mesmo caminho que "LLM caiu": o aluno recebe o piso do M6.1.
    """

    def __init__(self, model_name: str = "null") -> None:
        self._model_name = model_name
        self.last_failure = "geração desabilitada (ECOSFERA_LLM_ENABLED=false)"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: AnchoredPrompt) -> str | None:
        del prompt
        return None


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TEMPERATURE",
    "NullLanguageModel",
    "OllamaLanguageModel",
]
