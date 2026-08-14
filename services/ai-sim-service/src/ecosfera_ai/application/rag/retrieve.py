"""O retriever — devolve REGISTRO, nunca fato.

A superfície que o M6.3 vai consumir. Ela entrega `RetrievedPassage`, que é
estruturalmente incapaz de ocupar o lugar de um fato do Event Store (ver
`domain/rag/passage.py`): sem `event_id`, sem `occurred_at`, sem `cause_code`, e
recusada pelo verificador de tipos onde um `DomainEvent` é esperado.

## Consciente de categoria, de propósito

Pedir "regras de vocabulário relevantes a este `cause_code`" é uma pergunta
diferente de "objetivos de currículo desta faixa de ensino". Um retriever que
devolvesse os dois misturados obrigaria o M6.3 a filtrar depois — e a filtrar
depois é como se perde o controle sobre o que entra no prompt. O filtro é aqui.

## A similaridade viaja junto

O M6.4 vai precisar dela para raciocinar sobre confiança, e um guardrail futuro
pode recusar recuperação fraca em vez de deixar o modelo se apoiar no que quase
não veio ao caso. Esconder o número obrigaria a subetapa seguinte a recalculá-lo
por fora — ou, pior, a confiar sem medir.

## Nenhuma prosa sai daqui

O retriever devolve passagens; ele não as compõe, não as resume e não as
reescreve. Compor é o M6.3, e fazer isso aqui apagaria a fronteira entre
"material recuperado" e "texto gerado" justamente na camada em que ela ainda é
fácil de auditar.
"""

from __future__ import annotations

from collections.abc import Sequence

from ecosfera_ai.application.rag.corpus_index import CorpusIndex, ScoredEntry
from ecosfera_ai.domain.rag.corpus import CorpusCategory, CorpusEntry
from ecosfera_ai.domain.rag.embedding import EmbeddingModel
from ecosfera_ai.domain.rag.passage import RetrievedPassage

DEFAULT_LIMIT = 5


class RetrievePassagesUseCase:
    """Consulta em texto livre (ou um `cause_code`) → passagens ranqueadas."""

    def __init__(self, embedder: EmbeddingModel, index: CorpusIndex) -> None:
        self._embedder = embedder
        self._index = index

    async def execute(
        self,
        query: str,
        *,
        limit: int = DEFAULT_LIMIT,
        categories: frozenset[CorpusCategory] | None = None,
        cause_code: str | None = None,
        min_similarity: float = 0.0,
    ) -> tuple[RetrievedPassage, ...]:
        """Recupera as `limit` passagens mais próximas da consulta.

        `min_similarity` existe para quem já sabe o que fazer com recuperação
        fraca. O padrão é 0.0 — descartar por padrão esconderia do M6.4 o material
        que ele precisa examinar para calibrar o próprio corte.
        """
        if limit <= 0:
            return ()
        vector = self._embedder.embed([query])[0]
        found = await self._index.search(
            self._embedder.name,
            vector,
            limit=limit,
            categories=categories,
            cause_code=cause_code,
        )
        return tuple(
            _as_passage(scored, self._embedder.name)
            for scored in found
            if scored.similarity >= min_similarity
        )

    async def for_cause_code(
        self, cause_code: str, *, limit: int = DEFAULT_LIMIT
    ) -> tuple[RetrievedPassage, ...]:
        """As regras de LINGUAGEM que valem ao narrar um mecanismo.

        O atalho que o M6.3 vai usar mais: dado o `cause_code` de um evento REAL
        do planeta (que veio do Event Store, não daqui), quais regras de
        vocabulário e correções validadas governam a forma de contá-lo.

        Note o que o método NÃO faz: ele não afirma que o mecanismo ocorreu. Quem
        afirma isso é o dossiê factual; aqui o código é apenas a chave de busca.
        """
        return await self.execute(
            cause_code,
            limit=limit,
            categories=frozenset(
                {CorpusCategory.VOCABULARY_RULE, CorpusCategory.VALIDATED_CORRECTION}
            ),
            cause_code=cause_code,
        )


def _as_passage(scored: ScoredEntry, model_name: str) -> RetrievedPassage:
    entry: CorpusEntry = scored.entry
    return RetrievedPassage(
        entry_id=entry.entry_id,
        category=entry.category,
        source=entry.source,
        text=entry.text,
        similarity=scored.similarity,
        topic=entry.topic,
        relevant_cause_codes=entry.cause_codes,
        bncc_codes=entry.bncc_codes,
        grade_band=entry.grade_band,
        code_verified=entry.code_verified,
        license=entry.license,
        embedding_model=model_name,
    )


def passages_to_dicts(passages: Sequence[RetrievedPassage]) -> list[dict[str, object]]:
    """Forma portável — para inspeção humana e para a rota de auditoria."""
    return [passage.to_dict() for passage in passages]


__all__ = ["DEFAULT_LIMIT", "RetrievePassagesUseCase", "passages_to_dicts"]
