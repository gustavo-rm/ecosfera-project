"""Orquestrador do tick determinístico (RF-013/014/023).

Roda os subsistemas (estratégias) aplicando cada delta ao estado de trabalho,
para que um subsistema enxergue os efeitos do anterior dentro do mesmo tick. O
RNG numpy é semeado por (seed, tick) via `SeedSequence`: a mesma semente
reproduz exatamente a trajetória (RF-023), enquanto cada tick recebe ruído
distinto porém determinístico.

## Ordem de acoplamento (canônica — ver ADR 0004)

    physics -> chemistry -> climate -> geology -> ocean -> life

Cada posição tem uma razão física:

1. **physics** abre o tick porque define a irradiância incidente (`solar_flux`)
   que todo o resto consome; não depende de ninguém.
2. **chemistry** atualiza os estoques de CO2/água ANTES do clima, para que o
   forçamento de estufa do tick já reflita o carbono novo.
3. **climate** converte energia + estufa em temperatura.
4. **geology** responde ao clima recém-calculado (erosão depende de água) e
   mantém o vulcanismo que a química lerá no PRÓXIMO tick — defasagem de um
   passo, deliberada: evita dependência circular dentro do mesmo tick.
5. **ocean** roda depois do clima para sequestrar calor da superfície
   (retroalimentação negativa) e diluir/concentrar a salinidade com a água já
   atualizada pela química.
6. **life** fecha o tick: a biomassa reage ao ambiente final da era.

A ordem é dado de configuração (`SUBSYSTEM_ORDER`), não convenção implícita.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecosfera_ai.domain.feedback.models import Observation
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.simulation_engine.state import PlanetState, StateBounds, StateDelta
from ecosfera_ai.simulation_engine.subsystems.base import Subsystem

# Ordem canônica de acoplamento dos subsistemas no tick (ver docstring do módulo
# e ADR 0004). A fábrica em `params.build_orchestrator` monta as estratégias
# seguindo exatamente esta sequência.
SUBSYSTEM_ORDER: tuple[str, ...] = (
    "physics",
    "chemistry",
    "climate",
    "geology",
    "ocean",
    "life",
)


@dataclass(frozen=True, slots=True)
class TickResult:
    """Resultado de um tick: novo estado, delta agregado e observações derivadas.

    `events` é o Canal B do tick, e sai VAZIO por aqui: o `TickOrchestrator`
    legado não emite domain events. Quem o preenche é o
    `FrameworkTickOrchestrator`, repassando o que os Engines emitiram. É por este
    campo que o feedback causal chega ao consumidor sem que ele precise vasculhar
    o Event Store por planeta — os eventos vêm da execução daquele planeta
    (ADR 0011).
    """

    state: PlanetState
    delta: StateDelta
    observations: list[Observation]
    events: tuple[DomainEvent, ...] = ()


class TickOrchestrator:
    """Compõe subsistemas plugáveis em um passo determinístico e reprodutível."""

    def __init__(self, subsystems: list[Subsystem], bounds: StateBounds) -> None:
        self._subsystems = subsystems
        self._bounds = bounds

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        """Nomes na ordem de execução — torna a ordem de acoplamento testável."""
        return tuple(s.name for s in self._subsystems)

    @property
    def bounds(self) -> StateBounds:
        """Faixas físicas usadas ao aplicar deltas (reusadas pelo replay)."""
        return self._bounds

    def tick(self, state: PlanetState) -> TickResult:
        rng = np.random.default_rng(np.random.SeedSequence([state.seed, state.tick]))
        working = state
        for subsystem in self._subsystems:
            delta = subsystem.step(working, rng)
            working = working.apply(delta, self._bounds)
        new_state = working.advanced()
        return TickResult(
            state=new_state,
            delta=new_state.delta_from(state),
            observations=new_state.observe(state),
        )
