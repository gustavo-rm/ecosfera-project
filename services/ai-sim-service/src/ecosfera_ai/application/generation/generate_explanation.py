"""O caso de uso da geração ancorada — e o recuo que nunca deixa de existir.

Junta as três metades do M6: o dossiê (M6.0) vira piso (M6.1), o corpus (M6.2) dá
registro, e o modelo reescreve o primeiro no tom do segundo. O que ele não faz,
em nenhum caminho, é decidir o que aconteceu.

## A ordem das operações é a garantia

    piso  →  passagens  →  prompt  →  geração  →  VERIFICAÇÃO  →  aluno
                                         │                          ↑
                                         └──── falhou ──→ piso ─────┘

A verificação fica ENTRE a geração e o aluno, não depois da entrega. Não há
caminho em que texto não verificado chegue lá: `execute` só devolve prosa do
modelo se o veredito passou, e devolve o piso em todos os outros casos.

## Arbitragem por categoria (correção 3 do M6.3)

O ADR 0027 mediu que a similaridade NÃO distingue uma regra de vocabulário da
correção validada que diz a mesma coisa — as duas voltam para a mesma consulta,
com notas próximas, em ordem que varia com o modelo de embedding. Deixar o prompt
à mercê dessa ordem faria o conteúdo do prompt mudar ao trocar de embedder, sem
que nada de factual tivesse mudado.

A arbitragem é por CATEGORIA, como o próprio ADR 0027 recomendou: entre irmãs do
mesmo tópico, a regra de vocabulário entra primeiro. Ela é a formulação curta e
citável, escrita para ser seguida; a correção validada é o registro de por que a
regra existe. As duas continuam podendo entrar — o que deixa de variar é a ORDEM,
e com ela o prompt.
"""

from __future__ import annotations

from collections.abc import Sequence

from ecosfera_ai.application.generation.language_model import LanguageModelPort
from ecosfera_ai.application.generation.rejection_log import AttemptRecorder, GenerationAttempt
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import FactualContext
from ecosfera_ai.domain.generation.anchoring import (
    GeneratedExplanation,
    GroundingVerdict,
    RegisterSource,
)
from ecosfera_ai.domain.generation.grounding import describe_failure, verify_grounding
from ecosfera_ai.domain.generation.prompt import PromptSpec
from ecosfera_ai.domain.rag.corpus import CorpusCategory
from ecosfera_ai.domain.rag.passage import RetrievedPassage


def render_register_guidance(passages: Sequence[RetrievedPassage]) -> str:
    """As passagens viram linhas de orientação, com a origem junto.

    A origem entra no prompt porque ela é o que distingue "regra do projeto" de
    "coisa que o modelo lembra".

    Vive AQUI, e não junto da especificação do prompt, por causa do contrato de
    import: se o módulo da especificação conhecesse `RetrievedPassage`, o
    verificador de fundamentação passaria a alcançar o texto do corpus por
    transitividade — e a garantia de que ele confere a saída contra o piso, e
    nunca contra a passagem, voltaria a ser disciplina em vez de barreira.
    """
    if not passages:
        return ""
    return "\n".join(f"- {passage.text.strip()} (origem: {passage.source})" for passage in passages)


# A ordem de desempate entre irmãs. Menor entra primeiro.
_CATEGORY_PRIORITY: dict[CorpusCategory, int] = {
    CorpusCategory.VOCABULARY_RULE: 0,
    CorpusCategory.VALIDATED_CORRECTION: 1,
    CorpusCategory.CURRICULUM_OBJECTIVE: 2,
    CorpusCategory.EXTERNAL_REFERENCE: 3,
}


def arbitrate_by_category(passages: Sequence[RetrievedPassage]) -> tuple[RetrievedPassage, ...]:
    """Ordena as passagens de forma estável, categoria primeiro.

    Dentro da mesma categoria a similaridade continua mandando — é ela que diz o
    que veio ao caso. Entre categorias, a prioridade é fixa, e é isso que torna o
    prompt independente de qual irmã o embedder preferiu naquele dia.

    `entry_id` fecha o desempate para que a ordem seja TOTAL: duas entradas de
    mesma categoria e mesma nota produziriam ordem arbitrária, e um prompt que
    muda entre execuções idênticas é irreprodutível justamente onde se está
    tentando medir um componente não-determinístico.
    """
    return tuple(
        sorted(
            passages,
            key=lambda passage: (
                _CATEGORY_PRIORITY.get(passage.category, len(_CATEGORY_PRIORITY)),
                -passage.similarity,
                passage.entry_id,
            ),
        )
    )


class GenerateAnchoredExplanationUseCase:
    """Piso + registro → prosa reescrita, ou o piso de volta."""

    def __init__(
        self,
        model: LanguageModelPort,
        spec: PromptSpec,
        *,
        recorder: AttemptRecorder | None = None,
        scenario: str = "",
    ) -> None:
        self._model = model
        self._spec = spec
        # O registro é OPCIONAL na produção e obrigatório na avaliação. Sem ele,
        # o M6.4 mediria falhas imaginadas em vez das que o sistema produziu — a
        # lacuna que o ADR 0028 deixou ao prometer "motivos utilizáveis" sem
        # guardar nenhum.
        self._recorder = recorder
        self._scenario = scenario

    async def execute(
        self,
        *,
        floor: Explanation,
        context: FactualContext,
        passages: Sequence[RetrievedPassage] = (),
        scenario: str = "",
    ) -> GeneratedExplanation:
        """Gera com ancoragem, verifica, e recua ao piso em qualquer falha."""
        return self._recorded(
            await self._generate(floor=floor, context=context, passages=passages),
            scenario=scenario or self._scenario,
        )

    def _recorded(self, result: GeneratedExplanation, *, scenario: str) -> GeneratedExplanation:
        """Registra a tentativa — aprovada, reprovada ou sem geração.

        As três entram, e é a aprovação que torna a medição possível: um arquivo
        só de falhas não tem denominador, e a tentação seguinte seria estimá-lo.
        """
        if self._recorder is not None:
            self._recorder.record(GenerationAttempt.of(result, scenario=scenario))
        return result

    async def _generate(
        self,
        *,
        floor: Explanation,
        context: FactualContext,
        passages: Sequence[RetrievedPassage] = (),
    ) -> GeneratedExplanation:
        ordered = arbitrate_by_category(passages)
        sources = tuple(
            RegisterSource(
                entry_id=passage.entry_id,
                category=passage.category,
                source=passage.source,
                similarity=passage.similarity,
            )
            for passage in ordered
        )

        if floor.is_empty or not floor.summary.strip():
            return self._fallback(
                floor, sources, reason="o piso do M6.1 está vazio: não há o que reescrever"
            )

        prompt = self._spec.build(
            floor_text=floor.summary,
            register_guidance=render_register_guidance(ordered),
        )
        try:
            generated = await self._model.generate(prompt)
        except Exception as escaped:
            # A porta PROMETE `None` em vez de exceção, e o adaptador Ollama
            # cumpre. Mas a promessa é do adaptador, e o M6.4 vai injetar aqui um
            # harness adversarial que ninguém escreveu ainda. Confiar na promessa
            # neste ponto faria o aluno pagar por uma implementação de terceiro
            # mal-comportada, existindo o piso do M6.1 pronto para entregar.
            #
            # `except Exception` é amplo de propósito: a única falha que NÃO se
            # quer capturar aqui é a que também não é `Exception` (cancelamento
            # de tarefa, interrupção), e essas continuam subindo.
            return self._fallback(floor, sources, reason=f"o modelo levantou exceção: {escaped!r}")
        if generated is None:
            return self._fallback(
                floor, sources, reason=self._failure_reason(), verdict_known=False
            )

        verdict = verify_grounding(generated, floor=floor, context=context, spec=self._spec)
        if not verdict.passed:
            return self._fallback(
                floor,
                sources,
                reason=describe_failure(generated, verdict),
                verdict=verdict,
                verdict_known=True,
            )

        return GeneratedExplanation(
            planet_id=floor.planet_id,
            register=floor.register,
            text=generated,
            floor_text=floor.summary,
            verdict=verdict,
            fell_back=False,
            model_name=self._model.model_name,
            register_sources=sources,
        )

    def _failure_reason(self) -> str:
        """O motivo que o adaptador registrou, quando ele registra algum."""
        reported = getattr(self._model, "last_failure", "")
        return str(reported) if reported else "o modelo não devolveu texto utilizável"

    def _fallback(
        self,
        floor: Explanation,
        sources: tuple[RegisterSource, ...],
        *,
        reason: str,
        verdict: GroundingVerdict | None = None,
        verdict_known: bool = False,
    ) -> GeneratedExplanation:
        """O piso do M6.1, íntegro, com o motivo do recuo preservado.

        `verdict_known` separa "reprovou na fundamentação" de "não houve geração
        para verificar". Contar os dois juntos daria ao M6.4 uma taxa de
        alucinação inflada por indisponibilidade de rede.
        """
        return GeneratedExplanation(
            planet_id=floor.planet_id,
            register=floor.register if floor.register else Register.STANDARD,
            text=floor.summary,
            floor_text=floor.summary,
            verdict=(
                verdict
                if verdict_known and verdict is not None
                else GroundingVerdict.not_evaluated()
            ),
            fell_back=True,
            model_name=self._model.model_name,
            register_sources=sources,
            fallback_reason=reason,
        )


__all__ = ["GenerateAnchoredExplanationUseCase", "arbitrate_by_category"]
