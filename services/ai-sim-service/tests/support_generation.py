"""Montagem da camada de geração para os testes — um lugar só.

Mesma disciplina de `support_explanation`: a especificação do prompt vem do
arquivo DE PRODUÇÃO, e não de uma versão sintética. O que se quer garantir é o
comportamento do prompt que o aluno realmente recebe.

O modelo, esse sim, é falso na maioria dos testes — e isso é o ponto. As
propriedades que este marco promete (fundamentação, recuo, ordem do prompt) têm
de valer para QUALQUER saída, inclusive as que um modelo real raramente produz.
Um falso roteirizado é o único jeito de exercitar a saída maliciosa de propósito.

**E é por isso que ele não basta sozinho.** O ADR 0027 registrou o preço de
confiar só em falso: um carregador injetado concordava com o adaptador enquanto a
biblioteca real já avisava que o método tinha outro nome. Aqui a contrapartida é
`test_generation_over_ollama.py`, que fala com um Ollama de verdade no CI.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.application.generation.generate_explanation import (
    GenerateAnchoredExplanationUseCase,
)
from ecosfera_ai.application.generation.language_model import LanguageModelPort
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.generation.prompt import AnchoredPrompt, PromptSpec, load_prompt_spec
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.passage import RetrievedPassage
from tests.support_context import branching_cascade

SPEC_PATH = Path("configs/generation_prompt.yaml")


def spec() -> PromptSpec:
    return load_prompt_spec(SPEC_PATH)


class ScriptedModel:
    """Um modelo que devolve exatamente o que o teste mandar.

    `prompts` guarda tudo o que passou por ele: vários testes precisam afirmar o
    que FOI PEDIDO ao modelo, e não só o que ele respondeu.
    """

    def __init__(self, *replies: str | None, model_name: str = "modelo-de-teste") -> None:
        self._replies = list(replies) or [None]
        self._model_name = model_name
        self.prompts: list[AnchoredPrompt] = []
        self.last_failure = ""

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: AnchoredPrompt) -> str | None:
        self.prompts.append(prompt)
        reply = self._replies[min(len(self.prompts) - 1, len(self._replies) - 1)]
        if reply is None:
            self.last_failure = "modelo de teste configurado para falhar"
        return reply


class ExplodingModel:
    """Um modelo que ESTOURA — o que a porta promete que nunca atravessa.

    Existe porque "o adaptador captura tudo" é afirmação sobre o adaptador, e o
    caso de uso precisa da sua própria prova de que uma implementação mal
    comportada não derruba a explicação do aluno.
    """

    def __init__(self, model_name: str = "modelo-que-estoura") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: AnchoredPrompt) -> str | None:
        del prompt
        raise RuntimeError("o serviço de LLM caiu no meio da chamada")


def cascade_context() -> FactualContext:
    """O planeta com meteoro, extinção catastrófica e extinção ecológica."""
    events = branching_cascade()
    return FactualContext.of("planet-m63", ContextSlice.of_era(1), tuple(events))


def passage(
    entry_id: str,
    category: CorpusCategory,
    text: str,
    *,
    similarity: float = 0.5,
    source: str = "docs/decisions/tassia-validation.md",
) -> RetrievedPassage:
    return RetrievedPassage(
        entry_id=entry_id,
        category=category,
        source=source,
        text=text,
        similarity=similarity,
        embedding_model="ecosfera-deterministic-v1",
    )


def sibling_passages() -> tuple[RetrievedPassage, RetrievedPassage]:
    """As duas irmãs do achado do ADR 0027: mesma regra, categorias distintas."""
    rule = passage(
        "VOC-006",
        CorpusCategory.VOCABULARY_RULE,
        "Extinção catastrófica e extinção ecológica não se misturam. A catastrófica é "
        "abrupta e INDEPENDENTE de aptidão: um evento extremo não seleciona, elimina.",
        similarity=0.399,
        source="docs/adr/0019-extincao-catastrofica-vs-ecologica.md",
    )
    correction = passage(
        "VAL-Q8",
        CorpusCategory.VALIDATED_CORRECTION,
        "Validado: nem toda extinção tem causa adaptativa. A extinção catastrófica é "
        "independente de aptidão — uma espécie bem adaptada pode morrer num evento extremo.",
        similarity=0.322,
    )
    return rule, correction


def use_case(
    model: LanguageModelPort, *, prompt_spec: PromptSpec | None = None
) -> GenerateAnchoredExplanationUseCase:
    """O caso de uso com a especificação de produção, salvo indicação contrária.

    O parâmetro é tipado como a PORTA: é assim que o `mypy` confirma, de graça e
    em todo teste, que os modelos falsos daqui satisfazem o contrato que a
    produção exige — se um deles divergir da assinatura, a checagem de tipos
    reclama antes de qualquer teste rodar.
    """
    return GenerateAnchoredExplanationUseCase(model, prompt_spec or spec())
