"""Vocabulário de evento do Evolution Engine (Canal B, envelope §4).

Os `cause_code` são enum e NUNCA prosa pedagógica: o Engine entrega o esqueleto
causal como dado, e a frase é do Tutor (ADR-ARCH-0002, Correção 1).

`THERMAL_INTOLERANCE` é o elo que fecha a cadeia ambiental→biológica: uma
`TemperatureShift` do Climate causa uma `SpeciesExtinct` com esta causa, e o
`causation_id` liga as duas sem que o Evolution conheça o Climate.
"""

from __future__ import annotations

from ecosfera_ai.shared_kernel.events import CauseCodeEnum

LIFE_EMERGED = "LifeEmerged"
SPECIATION_OCCURRED = "SpeciationOccurred"
SPECIES_EXTINCT = "SpeciesExtinct"
TRAIT_SHIFT = "TraitShift"


class EvolutionCauseCode(CauseCodeEnum):
    """Causas estruturadas da evolução — código, nunca prosa."""

    HABITABILITY_THRESHOLD = "HABITABILITY_THRESHOLD"
    THERMAL_INTOLERANCE = "THERMAL_INTOLERANCE"
    RESOURCE_SCARCITY = "RESOURCE_SCARCITY"
    PREDATION_PRESSURE = "PREDATION_PRESSURE"
    GENETIC_DIVERGENCE = "GENETIC_DIVERGENCE"
    DIRECTIONAL_SELECTION = "DIRECTIONAL_SELECTION"
