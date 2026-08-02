"""Vocabulário de evento do Geology Engine (Canal B, envelope §4)."""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

# Tipos de evento — vocabulário do domínio, não prosa.
VOLCANIC_ERUPTION = "VolcanicEruption"


class GeologyCauseCode(CauseCodeEnum):
    """Causas estruturadas da geologia.

    Herdam de `CauseCodeEnum` (base vazia e portanto herdável): cada Engine
    declara o próprio vocabulário sem que o envelope precise conhecer todos.
    A frase pedagógica correspondente é do Tutor, nunca daqui
    (ADR-ARCH-0002, Correção 1).
    """

    TECTONIC_PULSE = "TECTONIC_PULSE"
