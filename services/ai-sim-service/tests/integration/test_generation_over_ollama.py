"""A geração contra um LLM DE VERDADE — verificada no CI, não localmente.

**Por que este arquivo tem de existir.** Todos os outros testes do M6.3 usam um
modelo roteirizado, e isso é certo: as propriedades têm de valer para saídas
escolhidas a dedo, inclusive as maliciosas que um modelo real quase nunca produz.
Mas nenhum deles responde à pergunta que decide se a camada serve: *com este
prompt, um modelo de verdade produz texto que PASSA?*

O ADR 0027 registrou o preço de não perguntar. Lá, um carregador injetado
implementava exatamente o método que o adaptador chamava, os dois concordavam, e
a biblioteca real já tinha renomeado a função havia tempo. O falso concordava
consigo mesmo.

Aqui o risco é maior. Se o prompt for ambíguo, se o modelo escolhido ignorar a
instrução, ou se o verificador for estrito demais para qualquer saída real, o
sintoma é o mesmo: recuo em 100% das gerações. O aluno lê o piso do M6.1 — que é
correto, então nada quebra — e a camada inteira vira custo puro, indistinguível
de sucesso em toda suíte roteirizada.

**Ambiente.** Exige um daemon Ollama com o modelo baixado. Sem ele este arquivo
PULA; com `ECOSFERA_REQUIRE_OLLAMA` ligada (o job do CI), a ausência vira FALHA —
mesma política que a persistência tem desde o M5.
"""

from __future__ import annotations

import pytest
from tests.ollama_guard import REQUIRED_MODEL, base_url, requires_ollama
from tests.support_context import branching_cascade
from tests.support_explanation import explain
from tests.support_generation import cascade_context, sibling_passages, spec, use_case

from ecosfera_ai.domain.consumers.wording import (
    absolute_fitness_phrases_in,
    teleological_phrases_in,
)
from ecosfera_ai.infrastructure.llm.ollama import OllamaLanguageModel

pytestmark = requires_ollama()

FLOOR = explain(list(branching_cascade()))
CONTEXT = cascade_context()

# Quantas gerações se observa. Não é um número mágico: com temperatura baixa e um
# modelo pequeno, três amostras já mostram se a instrução está sendo seguida, e
# cada uma custa segundos de CI. O que se afirma é INVARIANTE, então mais
# amostras aumentariam a confiança sem mudar a natureza da afirmação.
SAMPLES = 3


def _model() -> OllamaLanguageModel:
    return OllamaLanguageModel(REQUIRED_MODEL, base_url=base_url(), timeout_seconds=120.0)


async def test_the_daemon_has_the_model_this_suite_needs() -> None:
    """Pergunta ao daemon, e não ao DNS.

    O portão do embedder ensinou a diferença: `registry.ollama.ai` respondia 404
    no runner, o que prova alcance de rede e não prova serviço. Um 404 aqui
    significaria "o modelo não foi baixado", e o sintoma seria recuo em tudo —
    com toda a suíte verde, porque recuar é comportamento correto.
    """
    prompt = spec().build(floor_text="Diga apenas: ok.", register_guidance="")
    generated = await _model().generate(prompt)

    assert generated is not None, (
        f"o Ollama em {base_url()} não gerou com {REQUIRED_MODEL!r} — "
        "sem isto, todo teste abaixo mediria o caminho de recuo"
    )
    assert generated.strip()


@pytest.mark.parametrize("attempt", range(SAMPLES))
async def test_a_real_generation_holds_the_invariants(attempt: int) -> None:
    """As mesmas propriedades dos testes roteirizados, agora sobre saída real.

    Note o que NÃO se afirma: nada sobre o texto em si. Duas execuções produzem
    prosa diferente e nenhuma é a "certa" — é a mudança de método que o ADR 0028
    registra, de igualdade exata para invariante.
    """
    del attempt
    rule, correction = sibling_passages()
    result = await use_case(_model()).execute(
        floor=FLOOR, context=CONTEXT, passages=[rule, correction]
    )

    # Qualquer que tenha sido o caminho, o que chega ao aluno está limpo.
    assert teleological_phrases_in(result.text) == ()
    assert absolute_fitness_phrases_in(result.text) == ()
    assert result.text.strip()

    if result.fell_back:
        assert result.text == FLOOR.summary, "o recuo entrega o piso, e não meio piso"
        assert result.fallback_reason
    else:
        assert result.verdict.passed
        assert result.model_name == REQUIRED_MODEL


async def test_at_least_one_real_generation_survives_the_gate() -> None:
    """O teste que impede a camada de ser custo puro e parecer sucesso.

    Se o prompt, o modelo e o verificador não conseguirem concordar NENHUMA vez,
    o M6.3 não está entregando nada — e sem esta asserção isso passaria como
    verde, porque recuar é comportamento correto.

    A barra é deliberadamente baixa: uma em `SAMPLES`. Medir taxa de aprovação é
    trabalho do M6.4, com conjunto de avaliação de verdade. Aqui só se afirma que
    o caminho feliz EXISTE.
    """
    results = []
    for _ in range(SAMPLES):
        results.append(await use_case(_model()).execute(floor=FLOOR, context=CONTEXT))

    approved = [result for result in results if not result.fell_back]
    assert approved, (
        "nenhuma das gerações reais passou pela verificação. Motivos observados: "
        + " | ".join(result.fallback_reason for result in results)
    )


async def test_a_real_generation_does_not_invent_the_catastrophe_away() -> None:
    """A invariante pedagógica de maior risco, sobre texto que ninguém escreveu."""
    result = await use_case(_model()).execute(floor=FLOOR, context=CONTEXT)
    lowered = result.text.lower()

    for blame in ("era inferior", "não era boa o suficiente", "perdeu a competição"):
        assert blame not in lowered
