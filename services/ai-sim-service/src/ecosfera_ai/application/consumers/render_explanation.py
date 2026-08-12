"""O caso de uso que transforma o dossiê factual em explicação — M6.1, sem LLM.

Fecha a Correção 1 do ADR-ARCH-0002 no ponto exato em que ela previa: a Visão
Educacional é RENDERIZADA pelo consumidor, a partir de eventos neutros. O Engine
entregou `cause_code` como dado, o M6.0 organizou o dossiê, e é aqui que a frase
finalmente existe.

## O piso de qualidade

O M6.3 vai colocar um LLM neste caminho. Quando isso acontecer, a pergunta
"o modelo está ajudando?" precisa ter resposta, e ela só existe se houver um
antes contra o qual comparar. Este renderizador é esse antes: determinístico,
auditável frase a frase, e correto por construção nos pontos em que errar custa
caro (extinção catastrófica, ancestral comum).

Um LLM que não superar isto não deve entrar.

## Sem LLM, e a fronteira é barrada por contrato

`import-linter` proíbe este pacote de alcançar Ollama, embeddings ou RAG. A
proibição vale enquanto a subetapa for esta — e ela é o que impede a fundação
factual de ganhar um gerador antes de ter um piso.
"""

from __future__ import annotations

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import EventStoreQuery
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext
from ecosfera_ai.domain.consumers.narration import narrate, summarize
from ecosfera_ai.domain.consumers.templates import TemplateSet


class ExplanationRenderer:
    """Dossiê factual entra, prosa auditável sai. Puro em cima do M6.0."""

    def __init__(self, templates: TemplateSet) -> None:
        self._templates = templates

    def render(
        self, context: FactualContext, register: Register = Register.STANDARD
    ) -> Explanation:
        """Renderiza a fatia inteira, em ordem cronológica.

        `summary` é a junção literal das frases de `facts` — nunca uma síntese
        por cima delas (ver `summarize`).
        """
        facts = narrate(context, self._templates, register)
        return Explanation(
            planet_id=context.planet_id,
            slice=context.slice,
            register=register,
            facts=facts,
            summary=summarize(facts),
        )


class ExplainSliceUseCase:
    """Do planeta e do recorte até a prosa, atravessando o Event Store.

    Junta as duas metades do M6: o `ContextAssembler` (M6.0) lê a trilha escopada
    no planeta, e o `ExplanationRenderer` (M6.1) a narra. Nenhuma das duas
    recalcula ciência nem toca no world-state.
    """

    def __init__(self, events: EventStoreQuery, renderer: ExplanationRenderer) -> None:
        self._assembler = ContextAssembler(events)
        self._renderer = renderer

    async def execute(
        self,
        planet_id: str,
        context_slice: ContextSlice,
        register: Register = Register.STANDARD,
    ) -> Explanation:
        context = await self._assembler.execute(planet_id, context_slice)
        return self._renderer.render(context, register)


__all__ = ["ExplainSliceUseCase", "ExplanationRenderer"]
