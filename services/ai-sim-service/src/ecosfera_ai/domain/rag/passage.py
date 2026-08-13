"""`RetrievedPassage` — material de REGISTRO, e estruturalmente NÃO um fato.

Este é o tipo que carrega a decisão arquitetural central do M6.2, e a razão de
ele existir separado é o modo de falha que o M6 inteiro existe para impedir.

## O risco concreto

No M6.3 um LLM vai receber, no mesmo prompt, duas coisas: o dossiê factual do
planeta daquele aluno (M6.0/M6.1) e algumas passagens deste corpus. Se as duas
chegarem com a mesma cara, nada impede que uma passagem que diz *"extinções
catastróficas são independentes de aptidão"* seja lida como *"houve uma extinção
catastrófica neste planeta"*. A frase resultante seria fluente, pedagogicamente
correta em tese, e FALSA sobre o planeta da criança — ancorada num corpus real e
não no event log dela. É a alucinação mais difícil de detectar que este desenho
admite, e ela não precisa de um modelo mal-comportado para acontecer: basta um
tipo permissivo demais.

## A garantia, e por que ela é de FORMA e não de disciplina

`RetrievedPassage` não compartilha campo algum com `DomainEvent` nem com
`FactualContext`. Não tem `event_id`, nem `occurred_at`, nem `cause_code`, nem
`causation_id`, nem `participants`. Não há herança comum, não há protocolo
comum, e o `mypy --strict` recusa passar um no lugar do outro.

O efeito prático: nenhuma função que espera um fato aceita uma passagem, e
qualquer tentativa de tratá-la como fato quebra na primeira leitura de atributo —
em vez de produzir silenciosamente uma narrativa errada.
`test_retrieved_passage_is_not_a_fact_type` afirma as duas direções, inclusive
rodando o verificador de tipos sobre a atribuição proibida.

## `relevant_cause_codes` é chave de ROTEAMENTO

O campo diz "esta regra de linguagem serve quando se narra tal mecanismo". Não
afirma que o mecanismo ocorreu. É por isso que ele se chama assim e não
`cause_code`: o nome no singular é o do envelope §4, e reusá-lo aqui convidaria
exatamente a confusão que este módulo previne.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ecosfera_ai.domain.rag.corpus import CorpusCategory

# Os campos que caracterizam um FATO derivado do Event Store. Nenhum deles pode
# aparecer numa passagem — `test_retrieved_passage_is_not_a_fact_type` varre.
FACT_BEARING_FIELDS: frozenset[str] = frozenset(
    {
        "event_id",
        "occurred_at",
        "cause_code",
        "cause_detail",
        "causation_id",
        "correlation_id",
        "participants",
        "consequences",
        "planet_id",
        "events",
        "speciations",
        "extinctions",
    }
)


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    """Uma passagem do corpus recuperada por similaridade, com a origem junto.

    `similarity` viaja porque o M6.3 e o M6.4 vão precisar dela: uma recuperação
    de baixa similaridade é material fraco, e um guardrail futuro pode recusá-la
    em vez de deixar o modelo se apoiar no que quase não veio ao caso.

    `source` viaja porque a auditoria é o produto: qualquer frase que o Tutor
    disser em determinado registro tem de poder ser rastreada até o documento do
    projeto que estabeleceu aquele registro.
    """

    entry_id: str
    category: CorpusCategory
    source: str
    text: str
    similarity: float
    topic: str = ""
    relevant_cause_codes: tuple[str, ...] = ()
    bncc_codes: tuple[str, ...] = ()
    grade_band: str = ""
    code_verified: bool | None = None
    license: str = ""
    # Com QUAL modelo esta passagem foi recuperada. Similaridade entre vetores de
    # modelos diferentes não significa nada, e o retriever recusa a mistura.
    embedding_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "category": self.category.value,
            "source": self.source,
            "text": self.text,
            "similarity": self.similarity,
            "topic": self.topic,
            "relevant_cause_codes": list(self.relevant_cause_codes),
            "bncc_codes": list(self.bncc_codes),
            "grade_band": self.grade_band,
            "code_verified": self.code_verified,
            "license": self.license,
            "embedding_model": self.embedding_model,
        }


__all__ = ["FACT_BEARING_FIELDS", "RetrievedPassage"]
