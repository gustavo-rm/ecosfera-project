"""A medição: taxa de aprovação, e as ressalvas que a tornam honesta.

Esta é a substituição do que os marcos físicos tinham. Lá, correção era "a mesma
entrada produz a mesma saída"; aqui é "o sistema se comporta bem sob tentativa
deliberada de quebrá-lo, e a taxa de falha é honestamente mensurável". A segunda
metade é o que este módulo faz, e ela é mais difícil que a primeira.

## Três coisas que uma taxa ingênua esconderia

**Indisponibilidade não é alucinação.** Um recuo por rede caída não diz nada sobre
o modelo. Contá-lo como reprovação mede a infraestrutura achando que mede a
geração — e a taxa PIORA quando o Ollama cai, que é a leitura exatamente errada.
`GroundingVerdict.evaluated` separa os dois desde o M6.3, e aqui essa separação
vira denominador.

**Aprovação com cobertura parcial não vale o mesmo que aprovação completa.** O
M6.4 fechou três tipos de evento, e cinco seguem sem checagem de invenção. Uma
saída pode passar sem que ninguém tenha conferido se ela inventou um
`TrophicCollapse`. Reportar as duas no mesmo número seria afirmar mais verificação
do que houve — o defeito que `DetectionCoverage` existe para impedir.

**A forma do piso confunde a comparação.** O ADR 0028 registrou que o piso da
cascata é um parágrafo repetitivo de cinco frases. Misturá-lo numa média única
esconderia se a qualidade cai por causa do modelo ou da forma do texto que ele
recebeu. Por isso o relatório quebra por cenário ANTES de agregar.

## O que esta medição NÃO é

Não é medida de qualidade pedagógica. Passar na fundamentação diz que a prosa não
inventou nada; não diz que ela ensina melhor que o piso do M6.1. Comparar as duas
exige leitor humano com critério pedagógico, e continua em aberto.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from ecosfera_ai.application.generation.rejection_log import GenerationAttempt


@dataclass(frozen=True, slots=True)
class ScenarioReport:
    """O resultado de um cenário, com o denominador explícito."""

    scenario: str
    attempts: int
    evaluated: int
    approved: int
    approved_with_full_coverage: int
    rejected: int
    infrastructure_failures: int

    @property
    def approval_rate(self) -> float | None:
        """Aprovadas sobre AVALIADAS — nunca sobre tentativas.

        `None` quando nada foi avaliado: uma taxa de 0% e "não houve o que medir"
        são coisas diferentes, e devolver 0.0 nos dois casos seria a mesma
        confusão que o terceiro estado do veredito já corrigiu uma vez.
        """
        return None if self.evaluated == 0 else self.approved / self.evaluated

    @property
    def full_coverage_rate(self) -> float | None:
        """Quanto da aprovação veio com verificação COMPLETA."""
        if self.approved == 0:
            return None
        return self.approved_with_full_coverage / self.approved


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """O relatório inteiro: por cenário, e só então agregado."""

    scenarios: tuple[ScenarioReport, ...] = ()
    reason_counts: tuple[tuple[str, int], ...] = ()
    models: frozenset[str] = field(default_factory=frozenset)

    @property
    def total_attempts(self) -> int:
        return sum(report.attempts for report in self.scenarios)

    @property
    def total_evaluated(self) -> int:
        return sum(report.evaluated for report in self.scenarios)

    @property
    def total_approved(self) -> int:
        return sum(report.approved for report in self.scenarios)

    @property
    def total_infrastructure_failures(self) -> int:
        return sum(report.infrastructure_failures for report in self.scenarios)

    @property
    def overall_approval_rate(self) -> float | None:
        """A agregada, que só deve ser lida DEPOIS das por cenário."""
        if self.total_evaluated == 0:
            return None
        return self.total_approved / self.total_evaluated


def _family_of(reason: str) -> str:
    """Agrupa motivos por família, para que a contagem diga algo.

    Sem isto, cada motivo seria único — eles citam o número, o termo ou o delta
    encontrado — e a contagem viraria uma lista de casos em vez de um padrão.
    """
    if "BIO-001" in reason:
        return "especiação/descendência (BIO-001)"
    if "BIO-005" in reason or "teleológica" in reason:
        return "teleologia (BIO-005)"
    if "Q5" in reason or "aptidão absoluta" in reason:
        return "aptidão absoluta (Q5)"
    if "contradiz" in reason:
        return "direção contrária ao log"
    if "não tem" in reason and "dossiê" in reason:
        return "acontecimento inventado"
    if "número" in reason:
        return "número sem origem no piso"
    if "vazio" in reason:
        return "saída vazia"
    return "outros"


def evaluate(attempts: Sequence[GenerationAttempt]) -> EvaluationReport:
    """Agrega as tentativas registradas num relatório com as ressalvas juntas."""
    by_scenario: dict[str, list[GenerationAttempt]] = {}
    for attempt in attempts:
        by_scenario.setdefault(attempt.scenario or "(sem cenário)", []).append(attempt)

    reports: list[ScenarioReport] = []
    for scenario in sorted(by_scenario):
        group = by_scenario[scenario]
        evaluated = [attempt for attempt in group if attempt.was_evaluated]
        approved = [attempt for attempt in evaluated if attempt.passed]
        reports.append(
            ScenarioReport(
                scenario=scenario,
                attempts=len(group),
                evaluated=len(evaluated),
                approved=len(approved),
                approved_with_full_coverage=sum(1 for a in approved if a.coverage_complete),
                rejected=len(evaluated) - len(approved),
                infrastructure_failures=len(group) - len(evaluated),
            )
        )

    families: Counter[str] = Counter()
    for attempt in attempts:
        for reason in attempt.reasons:
            families[_family_of(reason)] += 1

    return EvaluationReport(
        scenarios=tuple(reports),
        reason_counts=tuple(sorted(families.items(), key=lambda item: (-item[1], item[0]))),
        models=frozenset(attempt.model_name for attempt in attempts if attempt.model_name),
    )


__all__ = ["EvaluationReport", "ScenarioReport", "evaluate"]
