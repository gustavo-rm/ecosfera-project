"""O Diretor: decide QUAIS eventos acontecem e QUANDO — deterministicamente.

É a "IA como Mestre" do GDD §10, e o nome engana: não há aprendizado aqui, e não
haverá no M4. O Diretor é uma função pura de `(world-state, RNG semeado)`.

## Por que puro, e o que isso proíbe

O Diretor **não lê logs, métricas nem o Event Store**. A tentação é evidente —
"agendar uma seca porque o aluno vem prosperando há muitas eras" pede o histórico
—, e é exatamente o que a moldura proíbe: a observabilidade é LATERAL e não
realimenta a simulação (ADR-ARCH-0002). Se o Diretor lesse a trilha, o replay
deixaria de ser reproduzível a partir de `(seed, checkpoint)`, porque a trilha é
efeito da execução, não entrada dela.

O que ele PODE ler é o world-state (Canal A), que é entrada legítima e replayável.
É o bastante para adequar o evento ao contexto: uma era glacial num planeta a 45 °C
não ensina nada — ensina que o simulador sorteia.

## Sem RL (adiado)

Aprendizado por reforço para ajustar tensão está FORA do M4 e registrado como tal.
Um Diretor treinado seria estatal e dependeria de histórico — as duas coisas que a
pureza acima recusa. Introduzi-lo exige antes decidir onde o estado do agente vive
e como o replay o reconstrói; não é uma extensão, é outro desenho.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.engines.event.contracts import EventEngineParams
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot


@dataclass(frozen=True, slots=True)
class Schedule:
    """O que o Diretor decidiu neste tick.

    `kind = NONE` significa "nada agendado agora" — o caso comum, e de longe.
    """

    kind: EventKind
    ticks_ahead: int
    severity: float


def _is_plausible(kind: EventKind, snapshot: WorldStateSnapshot, p: EventEngineParams) -> bool:
    """O evento faz sentido no mundo de AGORA?

    Não é roteiro — é recusa do absurdo. O Diretor não escolhe o evento "certo"
    para a lição; ele descarta o que seria fisicamente incoerente e sorteia entre
    o que resta.
    """
    if kind is EventKind.ICE_AGE:
        return snapshot.climate.temperature <= p.ice_age_max_temperature
    if kind is EventKind.DROUGHT:
        return snapshot.climate.temperature >= p.drought_min_temperature
    if kind is EventKind.WILDFIRE:
        # Não há incêndio sem o que queimar. A leitura da biota é do MESMO tick
        # (o Event roda por último), então é o combustível de agora.
        return snapshot.biota.biomass >= p.wildfire_min_biomass
    return True


def plausible_kinds(snapshot: WorldStateSnapshot, p: EventEngineParams) -> list[EventKind]:
    """Catálogo filtrado pelo contexto, em ordem ESTÁVEL.

    A ordem é o valor do enum, não a ordem do dicionário: a iteração precisa ser
    idêntica entre execuções para o sorteio ser reproduzível.
    """
    return sorted(
        (kind for kind in p.catalog if _is_plausible(kind, snapshot, p)),
        key=lambda kind: int(kind),
    )


def decide(
    snapshot: WorldStateSnapshot,
    rng: np.random.Generator,
    p: EventEngineParams,
    *,
    quiet: bool,
) -> Schedule:
    """Agenda (ou não) um evento, a partir do estado e do RNG semeado.

    O RNG vem do Planet Engine, derivado de `(seed, engine_id, tick)`. Duas
    execuções com a mesma semente sorteiam a mesma coisa nos mesmos ticks — é o
    que o `test_event_determinism` afirma e o que o replay exige (RF-023).
    """
    if quiet:
        return Schedule(EventKind.NONE, 0, 0.0)
    if float(rng.random()) >= p.scheduling_probability:
        return Schedule(EventKind.NONE, 0, 0.0)

    candidates = plausible_kinds(snapshot, p)
    if not candidates:
        return Schedule(EventKind.NONE, 0, 0.0)

    weights = np.array([p.profile(kind).weight for kind in candidates], dtype=float)
    total = float(weights.sum())
    if total <= 0.0:
        return Schedule(EventKind.NONE, 0, 0.0)

    chosen = candidates[int(rng.choice(len(candidates), p=weights / total))]
    profile = p.profile(chosen)
    # A severidade varia, para que dois meteoros não sejam o mesmo meteoro.
    severity = float(rng.uniform(0.6, 1.0))
    return Schedule(chosen, profile.forecast_lead, severity)
