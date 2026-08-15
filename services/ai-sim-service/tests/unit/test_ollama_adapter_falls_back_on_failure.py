"""Toda falha vira o piso do M6.1 — e nenhuma exceção atravessa a porta.

A promessa do contrato de falha, exercitada modo a modo. O comportamento correto
quando o modelo não responde não é estourar: é entregar a explicação do M6.1, que
já é correta e auditável. Uma exceção escapando transformaria indisponibilidade
de infraestrutura em erro para o aluno, com uma resposta boa disponível o tempo
todo.
"""

from __future__ import annotations

import httpx
import pytest
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import (
    ExplodingModel,
    ScriptedModel,
    cascade_context,
    use_case,
)

from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice
from ecosfera_ai.domain.generation.prompt import AnchoredPrompt
from ecosfera_ai.infrastructure.llm.ollama import NullLanguageModel, OllamaLanguageModel

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()
PROMPT = AnchoredPrompt(system="sistema", user="usuário")


def _adapter(handler: httpx.MockTransport) -> OllamaLanguageModel:
    return OllamaLanguageModel(
        "llama3.1:8b", client=httpx.AsyncClient(transport=handler), timeout_seconds=1.0
    )


# --- Os modos de falha do adaptador -------------------------------------------


async def test_a_network_error_returns_none_with_a_reason() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    adapter = _adapter(httpx.MockTransport(refuse))
    assert await adapter.generate(PROMPT) is None
    assert "rede" in adapter.last_failure


async def test_a_timeout_returns_none_with_a_reason() -> None:
    def stall(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("demorou demais", request=request)

    adapter = _adapter(httpx.MockTransport(stall))
    assert await adapter.generate(PROMPT) is None
    assert "respondeu" in adapter.last_failure


async def test_an_http_error_returns_none_with_a_reason() -> None:
    """404 é o caso REAL mais provável: o modelo não foi baixado naquele host."""
    adapter = _adapter(httpx.MockTransport(lambda _r: httpx.Response(404, text="model not found")))
    assert await adapter.generate(PROMPT) is None
    assert "404" in adapter.last_failure


async def test_malformed_json_returns_none_with_a_reason() -> None:
    adapter = _adapter(httpx.MockTransport(lambda _r: httpx.Response(200, text="isto não é json")))
    assert await adapter.generate(PROMPT) is None
    assert "JSON" in adapter.last_failure


@pytest.mark.parametrize("body", [{}, {"response": ""}, {"response": "   "}, {"outro": "campo"}])
async def test_an_empty_or_shapeless_response_returns_none(body: dict[str, str]) -> None:
    """Corpo 200 e vazio é pior que erro: passaria como sucesso silencioso."""
    adapter = _adapter(httpx.MockTransport(lambda _r: httpx.Response(200, json=body)))
    assert await adapter.generate(PROMPT) is None
    assert adapter.last_failure


async def test_a_good_response_comes_back_stripped() -> None:
    """Contraprova: sem ela, "devolve None em tudo" passaria neste arquivo."""
    adapter = _adapter(
        httpx.MockTransport(lambda _r: httpx.Response(200, json={"response": "  a prosa  "}))
    )
    assert await adapter.generate(PROMPT) == "a prosa"
    assert adapter.last_failure == ""


async def test_the_disabled_model_behaves_like_a_failure() -> None:
    """LLM desligado percorre o MESMO caminho que LLM caído — de propósito."""
    null = NullLanguageModel()
    assert await null.generate(PROMPT) is None
    assert "desabilitada" in null.last_failure


# --- O caso de uso, que é onde o aluno é protegido ----------------------------


async def test_a_failed_generation_returns_the_floor_untouched() -> None:
    result = await use_case(ScriptedModel(None)).execute(floor=FLOOR, context=CONTEXT)

    assert result.fell_back
    assert result.text == FLOOR.summary
    assert result.floor_text == FLOOR.summary
    assert result.fallback_reason


async def test_an_exception_from_the_model_never_reaches_the_caller() -> None:
    """A porta promete `None`; o caso de uso não confia e prova.

    Um adaptador de terceiro — o harness adversarial do M6.4, por exemplo — pode
    não honrar o contrato. O aluno não pode pagar por isso.
    """
    with pytest.raises(RuntimeError):
        await ExplodingModel().generate(PROMPT)

    result = await use_case(ExplodingModel()).execute(floor=FLOOR, context=CONTEXT)
    assert result.fell_back
    assert result.text == FLOOR.summary


async def test_a_quiet_period_floor_is_still_worth_rewriting() -> None:
    """Uma fatia sem acontecimentos NÃO é um piso vazio, e a diferença importa.

    Escrever este arquivo revelou a confusão: `explain([])` parecia produzir
    "nada", e produz a frase de período tranquilo — prosa legítima, fundamentada
    na fatia inteira, que o M6.1 criou justamente para que o silêncio fosse um
    fato declarado em vez de uma lacuna. Reescrevê-la em registro melhor é
    trabalho válido do M6.3.
    """
    quiet = explain([])
    assert quiet.summary.strip(), "a fatia vazia deveria render a frase de período tranquilo"

    model = ScriptedModel("Naquele período, nada de especial aconteceu no planeta.")
    result = await use_case(model).execute(floor=quiet, context=cascade_context())

    assert model.prompts, "o piso de período tranquilo tem conteúdo e deveria ser reescrito"
    assert not result.fell_back


async def test_a_genuinely_empty_floor_never_calls_the_model() -> None:
    """Mandar `<fatos>` em branco é o pior caso, e ele é barrado antes da chamada.

    Um modelo que receba a seção de fatos vazia escreve ciência genérica
    plausível — a alucinação que o M6 existe para impedir, produzida pelo nosso
    próprio descuido em vez de pelo modelo. Hoje o renderizador do M6.1 não
    produz este piso; a guarda existe para que uma mudança futura lá não abra
    esse caminho aqui em silêncio.
    """
    empty = Explanation(
        planet_id="planet-m63",
        slice=ContextSlice.of_era(1),
        register=Register.STANDARD,
        facts=(),
        summary="",
    )
    model = ScriptedModel("texto que nunca deveria ser pedido")

    result = await use_case(model).execute(floor=empty, context=cascade_context())

    assert result.fell_back
    assert model.prompts == [], "o modelo foi chamado com um piso vazio"
    assert "vazio" in result.fallback_reason


async def test_a_network_fallback_is_not_counted_as_a_grounding_failure() -> None:
    """Indisponibilidade não é alucinação, e contá-las juntas engana o M6.4.

    Uma taxa de "geração reprovada" que somasse quedas de rede mediria a
    infraestrutura achando que mede o modelo.
    """
    result = await use_case(ScriptedModel(None)).execute(floor=FLOOR, context=CONTEXT)

    assert result.fell_back
    assert result.verdict.reasons == (), "não houve texto para verificar"
    assert not result.verdict.evaluated, "'não avaliado' não pode se disfarçar de 'reprovado'"
    assert "não avaliado" in result.verdict.summary


async def test_a_grounding_failure_is_marked_as_evaluated() -> None:
    """O outro lado do tri-estado: aqui HOUVE texto, e ele foi reprovado.

    O roteiro de fumaça encontrou a confusão: com o modelo desligado a inspeção
    dizia "veredito: reprovado", e não havia reprovação nenhuma. Distinguir os
    dois é o que impede o M6.4 de somar queda de rede à taxa de alucinação.
    """
    invented = "Uma erupção supervulcânica cobriu o céu naquele ciclo."
    result = await use_case(ScriptedModel(invented)).execute(floor=FLOOR, context=CONTEXT)

    assert result.fell_back
    assert result.verdict.evaluated
    assert not result.verdict.passed
    assert result.verdict.reasons
    assert result.verdict.summary == "reprovado"
