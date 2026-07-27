"""Modelos de telemetria pedagógica (RF-071) e Evidência (Modelagem §8).

A telemetria é a fundação do Stealth Assessment (Inc 7): cada ação vira Evento;
o Analytics normaliza em Evidência; a rede bayesiana infere competência. Por isso
o esquema já nasce alinhado à Matriz de Evidências, mesmo antes do modelo bayesiano.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """Evento bruto emitido pelo jogo. Só entra no pipeline com consentimento (RF-008)."""

    student_id: str
    planet_id: str
    action: str  # ex.: 'intervene', 'advance_era', 'ask_tutor'
    payload: dict[str, float | str | bool]
    consent: bool
    occurred_at: datetime = field(default_factory=_now)

    def is_processable(self) -> bool:
        """LGPD: sem consentimento do responsável, o evento não é processado (RNF-009)."""
        return self.consent


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidência estruturada, pronta para mapear a competências/BNCC (RF-076)."""

    student_id: str
    competency_hint: str  # competência candidata (ex.: 'systems_thinking')
    strength: float  # [0,1] força da evidência
    source_action: str
    observed_at: datetime = field(default_factory=_now)
