"""O registro de gerações — a matéria-prima do conjunto de avaliação.

## A lacuna que este módulo fecha

O ADR 0028 prometeu ao M6.4 "os motivos de reprovação em forma utilizável". A
forma existia — `describe_failure` monta a linha, `fallback_reason` a carrega —
mas **nada guardava nada**. O objeto vivia uma chamada e era descartado, sem log,
sem banco, sem arquivo. Utilizável em FORMATO, e inexistente como dado.

Sem isto, "montar o conjunto de avaliação a partir de falhas reais" seria
impossível de cumprir: só haveria casos sintéticos, que são exatamente os que o
Task A do M6.4 diz serem de menor sinal — porque descrevem as falhas que alguém
IMAGINOU, e não as que o sistema de fato produziu.

## Por que registrar TAMBÉM as aprovações

Uma medição de taxa de aprovação precisa do denominador. Registrar só reprovações
daria um arquivo cheio de falhas e nenhuma noção de quantas gerações houve — e a
tentação seguinte seria estimar o denominador, que é como uma métrica passa a
medir a própria expectativa de quem a lê.

## Por que JSONL, e não uma tabela

O consumidor é humano e é análise: alguém abre o arquivo, lê os casos e monta um
conjunto. Uma tabela exigiria migration, adaptador e Postgres vivo para uma coisa
que o M6.4 lê uma vez por rodada de avaliação. Se um dia isto virar telemetria
contínua, o caminho é o Event Store — e aí a decisão é outra, com LGPD junto,
porque prosa gerada para um aluno é dado de aluno.

## O que NÃO entra aqui

Nada que identifique quem estudou. O registro guarda `planet_id`, o texto gerado,
o veredito e a proveniência do registro — o mesmo material que o M5 já classificou
como dado de SIMULAÇÃO e não de aluno (ADR 0021/0022).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from ecosfera_ai.domain.generation.anchoring import GeneratedExplanation

DEFAULT_LOG_PATH = Path("var/generation_attempts.jsonl")


@dataclass(frozen=True, slots=True)
class GenerationAttempt:
    """Uma tentativa de geração, com tudo o que a avaliação precisa reler.

    `scenario` é o rótulo do caso que a produziu. Ele existe porque o ADR 0028
    registrou um confundidor: o piso da cascata é um parágrafo repetitivo, e
    misturá-lo com os demais numa taxa única esconderia se a queda de qualidade
    vem do modelo ou da forma do piso.
    """

    recorded_at: str
    planet_id: str
    scenario: str
    model_name: str
    generated: str
    floor_text: str
    fell_back: bool
    fallback_reason: str
    verdict: dict[str, Any]

    @classmethod
    def of(
        cls, explanation: GeneratedExplanation, *, scenario: str, now: datetime | None = None
    ) -> GenerationAttempt:
        moment = now or datetime.now(UTC)
        return cls(
            recorded_at=moment.isoformat(),
            planet_id=explanation.planet_id,
            scenario=scenario,
            model_name=explanation.model_name,
            # Quando houve recuo, `text` é o piso; o que interessa à avaliação é o
            # que o MODELO escreveu, e ele está preservado no motivo do recuo.
            generated="" if explanation.fell_back else explanation.text,
            floor_text=explanation.floor_text,
            fell_back=explanation.fell_back,
            fallback_reason=explanation.fallback_reason,
            verdict=explanation.verdict.to_dict(),
        )

    @property
    def was_evaluated(self) -> bool:
        """Houve texto para verificar? Distingue reprovação de indisponibilidade."""
        return bool(self.verdict.get("evaluated"))

    @property
    def passed(self) -> bool:
        return bool(self.verdict.get("passed"))

    @property
    def coverage_complete(self) -> bool:
        coverage = self.verdict.get("coverage") or {}
        return bool(coverage.get("complete"))

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(str(reason) for reason in self.verdict.get("reasons") or ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_at": self.recorded_at,
            "planet_id": self.planet_id,
            "scenario": self.scenario,
            "model_name": self.model_name,
            "generated": self.generated,
            "floor_text": self.floor_text,
            "fell_back": self.fell_back,
            "fallback_reason": self.fallback_reason,
            "verdict": self.verdict,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GenerationAttempt:
        return cls(
            recorded_at=str(payload["recorded_at"]),
            planet_id=str(payload["planet_id"]),
            scenario=str(payload.get("scenario", "")),
            model_name=str(payload.get("model_name", "")),
            generated=str(payload.get("generated", "")),
            floor_text=str(payload.get("floor_text", "")),
            fell_back=bool(payload.get("fell_back")),
            fallback_reason=str(payload.get("fallback_reason", "")),
            verdict=dict(payload.get("verdict") or {}),
        )


class AttemptRecorder(Protocol):
    """A porta do registro — para que a avaliação não dependa de disco."""

    def record(self, attempt: GenerationAttempt) -> None: ...

    def read_all(self) -> Sequence[GenerationAttempt]: ...


class InMemoryAttemptRecorder:
    """Implementação de referência: roda em qualquer lugar, sem arquivo."""

    def __init__(self) -> None:
        self._attempts: list[GenerationAttempt] = []

    def record(self, attempt: GenerationAttempt) -> None:
        self._attempts.append(attempt)

    def read_all(self) -> Sequence[GenerationAttempt]:
        return tuple(self._attempts)


class JsonlAttemptRecorder:
    """Uma linha por tentativa, em append — legível por humano e por script.

    Append, e não reescrita: uma rodada de avaliação acrescenta ao que já existe,
    e o conjunto CRESCE entre marcos. Reescrever daria sempre a fotografia da
    última execução, que é a menos interessante das disponíveis.
    """

    def __init__(self, path: Path = DEFAULT_LOG_PATH) -> None:
        self._path = path

    def record(self, attempt: GenerationAttempt) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(attempt.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def read_all(self) -> Sequence[GenerationAttempt]:
        return tuple(self._iter_attempts())

    def _iter_attempts(self) -> Iterator[GenerationAttempt]:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield GenerationAttempt.from_dict(json.loads(line))


def _port_conformance() -> tuple[AttemptRecorder, AttemptRecorder]:
    """Prova, em tempo de checagem de tipo, que as duas satisfazem a porta."""
    return InMemoryAttemptRecorder(), JsonlAttemptRecorder()


__all__ = [
    "DEFAULT_LOG_PATH",
    "AttemptRecorder",
    "GenerationAttempt",
    "InMemoryAttemptRecorder",
    "JsonlAttemptRecorder",
]
