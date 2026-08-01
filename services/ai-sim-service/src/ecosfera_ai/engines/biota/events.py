# M2: determinístico; substituído pela evolução emergente no M3 (ADR-ARCH-0001)
"""Vocabulário de evento do Biota Engine provisório (Canal B, envelope §4).

`Abiogenesis` e `BiomassCollapse` descrevem a biomassa AGREGADA. Especiação,
extinção de espécie e dinâmica trófica NÃO estão aqui — são vocabulário da
camada emergente do M3 (ADR 0013).
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

ABIOGENESIS = "Abiogenesis"
BIOMASS_COLLAPSE = "BiomassCollapse"


class BiotaCauseCode(CauseCodeEnum):
    """Causas estruturadas da biota — código, nunca prosa pedagógica."""

    HABITABILITY_THRESHOLD = "HABITABILITY_THRESHOLD"
    CAPACITY_COLLAPSE = "CAPACITY_COLLAPSE"
