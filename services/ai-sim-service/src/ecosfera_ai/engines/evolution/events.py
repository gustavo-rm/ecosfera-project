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

# Mortandade em massa SEM extinção total. É o caso comum e faltava: a extinção
# só dispara quando a comunidade inteira cai abaixo do piso de viabilidade, o que
# quase nunca acontece. Um choque térmico que custa um quarto da biomassa não
# produzia evento algum — o diagnóstico de causa existia e era inalcançável.
#
# Para uma plataforma cujo produto é explicar POR QUÊ, "a comunidade perdeu 23%
# da biomassa porque o calor passou do que ela tolera" é justamente o evento que
# precisa existir (ADR 0016).
MASS_MORTALITY = "MassMortality"


class EvolutionCauseCode(CauseCodeEnum):
    """Causas estruturadas da evolução — código, nunca prosa."""

    HABITABILITY_THRESHOLD = "HABITABILITY_THRESHOLD"
    THERMAL_INTOLERANCE = "THERMAL_INTOLERANCE"
    RESOURCE_SCARCITY = "RESOURCE_SCARCITY"
    PREDATION_PRESSURE = "PREDATION_PRESSURE"
    GENETIC_DIVERGENCE = "GENETIC_DIVERGENCE"
    DIRECTIONAL_SELECTION = "DIRECTIONAL_SELECTION"
