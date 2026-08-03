"""Catálogo de eventos extraordinários e seus perfis de perturbação.

Puro: sem I/O, sem RNG próprio, sem framework. A intensidade de um evento em
funcao do tempo decorrido é uma FUNÇÃO — é isso que permite ao Event Engine ser
função pura do snapshot e ao replay reproduzir a perturbação bit-a-bit.

## Perturbação é estoque que decai, não pulso

Um meteoro não esfria o planeta no tick do impacto e pronto: ele injeta poeira
que permanece meses na estratosfera e decai. Modelar o evento como um pulso
instantâneo produziria um degrau na temperatura e nenhum "inverno de impacto" —
que é justamente o fenômeno a ensinar.

Por isso cada evento declara uma DURAÇÃO e um perfil de decaimento, e o que os
Engines afetados leem é a intensidade CORRENTE. Eles não sabem qual evento a
produziu, nem há quanto tempo — o que os mantém ignorantes deste catálogo.

> Toon et al. (1997), *Environmental perturbations caused by the impacts of
> asteroids and comets* — poeira estratosférica e resfriamento pós-impacto.
> Robock (2000), *Volcanic eruptions and climate* — forçamento por aerossol.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum


class EventKind(IntEnum):
    """Catálogo. É `IntEnum` porque o índice viaja na `EventSlice` (Canal A).

    O Canal A é de floats: anunciar QUAL evento vem pela telegrafia exige um
    número. O nome viaja pelo Canal B, onde há espaço para estrutura.
    """

    NONE = 0
    METEOR = 1
    DROUGHT = 2
    WILDFIRE = 3
    ICE_AGE = 4
    STORM = 5
    SUPERVOLCANO = 6


@dataclass(frozen=True, slots=True)
class EventProfile:
    """Como UM evento perturba o mundo, em dados versionados (`params.yaml`).

    Cada coeficiente é a perturbação NO PICO; a intensidade corrente é o pico
    multiplicado pelo decaimento. Um evento com `duration = 0` não existe.
    """

    kind: EventKind
    duration: int  # ticks de perturbação ativa
    decay: float  # constante de decaimento exponencial (0 = degrau)
    dust: float
    cooling: float
    drought: float
    impact: float
    mortality: float
    supervolcanic: float
    forecast_lead: int  # ticks de antecedência do aviso (RF-019/020)
    weight: float  # peso relativo no sorteio do Diretor


def decay_at(profile: EventProfile, elapsed: int) -> float:
    """Fração da intensidade de pico ainda ativa após `elapsed` ticks.

    Fora da janela do evento a perturbação é exatamente zero — e não um resíduo
    numérico. Um resíduo que nunca zera manteria o planeta permanentemente
    perturbado e faria a linha de base derivar sem causa, que é o defeito que o
    teste de quase-estacionariedade existe para pegar.
    """
    if elapsed < 0 or elapsed >= profile.duration:
        return 0.0
    if profile.decay <= 0.0:
        return 1.0
    return math.exp(-profile.decay * elapsed)


def perturbation_at(profile: EventProfile, elapsed: int) -> dict[str, float]:
    """Perturbação corrente do evento, campo a campo da `EventSlice`.

    `impact` e `mortality` são PICOS, não estoques: valem só no tick em que o
    evento ocorre. Uma mortalidade catastrófica que decaísse por vinte ticks não
    seria uma catástrofe — seria uma pressão ecológica, que é precisamente a
    distinção que o ADR 0019 preserva.
    """
    fraction = decay_at(profile, elapsed)
    instantaneous = 1.0 if elapsed == 0 else 0.0
    return {
        "dust_load": profile.dust * fraction,
        "cooling_forcing": profile.cooling * fraction,
        "drought_intensity": profile.drought * fraction,
        "supervolcanic_intensity": profile.supervolcanic * fraction,
        "impact_energy": profile.impact * instantaneous,
        "catastrophic_mortality": profile.mortality * instantaneous,
    }


def is_catastrophic(profile: EventProfile) -> bool:
    """O evento mata INDEPENDENTEMENTE de adaptação?

    É o predicado que separa as duas taxonomias de extinção do ADR 0019. Uma
    seca reduz o recurso e mata quem não o tolera — isso é ecológico. Um meteoro
    mata quem estava embaixo — isso é catastrófico.
    """
    return profile.mortality > 0.0
