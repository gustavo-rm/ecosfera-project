"""Física pura da geologia: vulcanismo, relevo e desgaseificação de carbono.

Sem framework, sem I/O, sem evento — só números. O `service.py` é quem traduz
isto para o Canal A e o Canal B.

## Fenômeno modelado

O vulcanismo é um processo **pulsante**: relaxa para uma linha de base e recebe
pulsos tectônicos. O relevo é um estoque disputado por dois fluxos opostos —
soerguimento (∝ vulcanismo) e erosão (∝ água disponível × relevo próprio).

A desgaseificação vulcânica é a fonte primária de CO2 atmosférico em escala
geológica; sem ela, o intemperismo de silicatos zeraria o carbono atmosférico em
poucos milhões de anos. É o braço "fonte" do ciclo carbonato-silicato
(Walker, Hays & Kasting, 1981), e é por isso que o fluxo emitido é **saída** da
geologia, não da química.
"""

from __future__ import annotations

from ecosfera_ai.engines.geology.contracts import GeologyEngineParams


def volcanism_change(volcanism: float, pulse: float, params: GeologyEngineParams) -> float:
    """Variação do vulcanismo: relaxação para a base mais o pulso tectônico.

    O pulso entra em módulo porque não existe vulcanismo negativo — um pulso é
    sempre uma FONTE de atividade, nunca um sumidouro.
    """
    relaxation = params.volcanism_decay * (params.volcanism_baseline - volcanism)
    return relaxation + abs(pulse)


def relief_change(
    volcanism: float, relief: float, water: float, params: GeologyEngineParams
) -> float:
    """Variação do relevo: soerguimento vulcânico menos erosão hídrica."""
    uplift = params.uplift_coeff * volcanism
    erosion = params.erosion_coeff * water * relief
    return uplift - erosion


def outgassing_flux(volcanism: float, params: GeologyEngineParams) -> float:
    """Fluxo de CO2 desgaseificado neste tick, em ppm.

    Escala linearmente com o vulcanismo sobre um fluxo de base — a mesma forma
    que o `chemistry` legado usava, agora com a autoria no Engine certo.
    """
    return params.outgassing_base * (1.0 + params.volcanism_sensitivity * volcanism)


def is_eruption(volcanism: float, params: GeologyEngineParams) -> bool:
    """Se o vulcanismo deste tick caracteriza uma erupção notável (Canal B)."""
    return volcanism >= params.eruption_threshold
