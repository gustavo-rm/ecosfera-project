"""A porta do modelo de linguagem — estreita de propósito.

Uma operação: dado um prompt ancorado, devolver prosa. Não há `chat`, não há
histórico, não há "pergunte qualquer coisa". A superfície é pequena porque tudo o
que ela não oferece é coisa que o M6.3 não quer que exista no caminho do aluno —
e porque o M6.4 vai precisar trocar a implementação por uma adversarial sem tocar
na lógica de ancoragem.

## O contrato de falha faz parte da porta

`generate` devolve `str | None`. `None` significa "não houve geração utilizável",
e é a ÚNICA forma de falha que atravessa esta fronteira: rede caída, tempo
esgotado, resposta malformada, corpo vazio — tudo vira `None`, com o motivo
registrado pelo adaptador.

A alternativa seria deixar a exceção subir. Ela foi rejeitada porque o
comportamento correto do sistema quando o modelo falha não é estourar: é entregar
o piso do M6.1, que já é uma explicação correta. Uma exceção que escapasse
transformaria indisponibilidade de LLM em erro para o aluno, quando existe
resposta boa disponível o tempo todo.
"""

from __future__ import annotations

from typing import Protocol

from ecosfera_ai.domain.generation.prompt import AnchoredPrompt


class LanguageModelPort(Protocol):
    """Prompt ancorado entra, prosa sai — ou `None` se não deu."""

    @property
    def model_name(self) -> str: ...

    async def generate(self, prompt: AnchoredPrompt) -> str | None: ...


class GenerationUnavailable(Exception):
    """Sinaliza, DENTRO do adaptador, que a geração não pode ser usada.

    Nunca atravessa a porta: o adaptador a captura e devolve `None`. Existe para
    que o próprio adaptador possa distinguir seus modos de falha ao registrar o
    motivo, sem espalhar `try/except` pela aplicação.
    """


__all__ = ["GenerationUnavailable", "LanguageModelPort"]
