"""Subsistema de geologia: tectônica, vulcanismo e erosão -> relevo.

O relevo é um estoque disputado por dois fluxos opostos: o **soerguimento**
tectônico/vulcânico o constrói e a **erosão** (proporcional à água disponível e
ao próprio relevo) o desgasta. O vulcanismo é um processo pulsante — decai para
uma linha de base e recebe pulsos tectônicos de um ruído procedural **semeado
pelo RNG do tick**, portanto reprodutível (RF-023), nunca aleatório de verdade.

Acoplamento com a química: o vulcanismo é a fonte de CO2 do planeta. A química
lê `state.volcanism` para escalar a desgaseificação — como a geologia roda depois
da química na ordem do tick, o efeito no CO2 aparece no tick seguinte (defasagem
de um passo, documentada no orquestrador e no ADR 0004).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.simulation_engine.state import PlanetState, StateDelta


@dataclass(frozen=True, slots=True)
class GeologyParams:
    """Parâmetros de tectônica, vulcanismo e erosão (dados versionados)."""

    tectonic_activity: float  # intensidade dos pulsos tectônicos
    volcanism_baseline: float  # nível de vulcanismo de repouso
    volcanism_decay: float  # relaxação do vulcanismo para a linha de base
    uplift_coeff: float  # soerguimento do relevo por unidade de vulcanismo
    erosion_coeff: float  # desgaste do relevo por unidade de água


class GeologySubsystem:
    """Estratégia de geologia parametrizada por dados (`GeologyParams`)."""

    name = "geology"

    def __init__(self, params: GeologyParams) -> None:
        self._p = params

    def step(self, state: PlanetState, rng: np.random.Generator) -> StateDelta:
        # Vulcanismo: relaxa para a linha de base e recebe pulsos tectônicos.
        # abs() mantém o pulso como fonte (não existe vulcanismo negativo).
        pulse = abs(float(rng.normal(0.0, self._p.tectonic_activity)))
        relaxation = self._p.volcanism_decay * (self._p.volcanism_baseline - state.volcanism)
        d_volcanism = relaxation + pulse

        # Relevo: soerguimento vulcânico menos erosão (∝ água disponível e relevo).
        uplift = self._p.uplift_coeff * state.volcanism
        erosion = self._p.erosion_coeff * state.water * state.relief
        return StateDelta(d_relief=uplift - erosion, d_volcanism=d_volcanism)
