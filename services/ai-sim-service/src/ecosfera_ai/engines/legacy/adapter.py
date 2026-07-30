"""Adaptador que faz o núcleo determinístico atual atravessar a moldura.

## Por que o adaptador embrulha o ORQUESTRADOR, e não cada subsistema

O enunciado do M0 pede embrulhar `climate/chemistry/geology/ocean` "como
Engines". Ao inspecionar o código, isso se mostrou impossível **sem alterar a
física** — o que o próprio M0 proíbe. Duas razões concretas:

1. **Fluxo de RNG compartilhado.** `TickOrchestrator.tick` cria UM
   `Generator` por tick (`SeedSequence([seed, tick])`) e o passa aos seis
   subsistemas em sequência. Cada subsistema consome sorteios de onde o anterior
   parou. A moldura, corretamente, dá a cada Engine um fluxo independente
   (`rng_for(seed, engine_id, tick)`). Dividir os seis em seis Engines trocaria
   todos os sorteios: mesma semente, trajetória diferente.

2. **Escrita através das fatias.** `chemistry` escreve `co2` (química),
   `ice_cover` (clima) e `water` (hidrologia); `ocean` escreve `temperature`,
   que é do clima. A regra "um Engine, uma fatia" (Spec §3) seria violada por
   dois dos quatro. Separar exige refatorar a física — que é exatamente o
   trabalho do M1/M2, não do M0.

Portanto: **um Engine, `legacy_planet`, dono da fatia transitória `LEGACY`**. O
comportamento é bit-a-bit o de hoje porque é literalmente o mesmo código. Cada
migração de M1/M2 tira campos da `LegacySlice` e os entrega ao Engine dono, até
a fatia desaparecer.

O adaptador **ignora `ctx.rng` de propósito** — usá-lo mudaria os números. É a
única exceção à regra "o Engine usa só o gerador recebido", ela é temporária, e
morre junto com a `LegacySlice`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.engines.legacy.bridge import legacy_slice_of, planet_state_of
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta, difference
from ecosfera_ai.simulation_engine.orchestrator import TickOrchestrator

LEGACY_ENGINE_ID = "legacy_planet"


@dataclass(slots=True)
class LegacySubsystemAdapter:
    """Expõe o `TickOrchestrator` existente como um Engine da moldura."""

    orchestrator: TickOrchestrator
    engine_id: str = LEGACY_ENGINE_ID
    reads: frozenset[SliceRef] = frozenset({SliceRef.LEGACY})
    lagged_reads: frozenset[SliceRef] = frozenset()
    writes: SliceRef = SliceRef.LEGACY

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        """Ordem de acoplamento herdada — as sementes dos Engines de M1/M2."""
        return self.orchestrator.subsystem_names

    def tick(self, ctx: TickContext) -> TickResult:
        state = planet_state_of(ctx.snapshot)
        result = self.orchestrator.tick(state)
        values = difference(legacy_slice_of(state), legacy_slice_of(result.state))
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values=values,
            ),
            # Sem eventos no M0: traduzir os marcos da timeline para o envelope
            # §4 exige `cause_code`s científicos, e cada Engine declara os seus ao
            # ser construído (M1/M2). Inventá-los aqui seria conhecimento de
            # domínio dentro de um adaptador.
            entities_processed=len(self.orchestrator.subsystem_names),
        )
