"""Guarda de disponibilidade do Ollama — o mesmo padrão do Docker, para o LLM.

O M6.2 aprendeu, e o ADR 0027 registrou, que um falso pode concordar com o
adaptador enquanto a biblioteca real diverge: o carregador injetado implementava
exatamente o método que o adaptador chamava, e os dois se davam bem enquanto o
`sentence-transformers` já tinha renomeado a função. O defeito só apareceu ao
rodar contra o modelo de verdade.

Aqui o risco é maior, porque o não-determinismo é a matéria-prima. Os testes com
`ScriptedModel` afirmam que o portão reage a saídas escolhidas a dedo; nenhum
deles afirma que um LLM de verdade, com este prompt, produz saídas que passam.
São perguntas diferentes, e só a segunda diz se a camada serve para alguma coisa.

`ECOSFERA_REQUIRE_OLLAMA=1` (ligada no job do CI) transforma "sem Ollama" em
FALHA, e não em pulo — mesma inversão que `ECOSFERA_REQUIRE_POSTGRES` faz para a
persistência, e pelo mesmo motivo: o pulo continua onde é honesto e some onde
seria esconderijo.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest

DEFAULT_BASE_URL = "http://localhost:11434"
# O modelo que o job do CI baixa. Vive aqui, e não em cada teste, pela lição da
# imagem do Postgres: uma constante repetida diverge, e a cópia errada é
# descoberta pelo CI muito depois de quem a escreveu ter esquecido.
REQUIRED_MODEL = "llama3.2:1b"


def base_url() -> str:
    return os.environ.get("ECOSFERA_OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def ollama_available() -> bool:
    """Um daemon VIVO responde `/api/tags` — não basta o host resolver.

    A distinção é a que o portão do embedder ensinou: `registry.ollama.ai`
    respondia 404 no runner, o que prova alcance de rede e não prova serviço
    algum. Aqui se pergunta ao daemon o que ele tem.
    """
    try:
        with urllib.request.urlopen(f"{base_url()}/api/tags", timeout=5) as response:
            return bool(response.status == 200)
    except (urllib.error.URLError, OSError, ValueError):
        return False


def ollama_required() -> bool:
    """O ambiente EXIGE geração de verdade? (o job do CI liga; dev não.)"""
    return os.environ.get("ECOSFERA_REQUIRE_OLLAMA", "").strip().lower() in {"1", "true", "yes"}


def requires_ollama() -> pytest.MarkDecorator:
    """Marca para testes que precisam de um Ollama real, com modelo baixado."""
    if ollama_available():
        return pytest.mark.skipif(False, reason="")
    if ollama_required():
        return pytest.mark.fail_without_ollama
    return pytest.mark.skipif(True, reason="daemon Ollama indisponível para geração real")
