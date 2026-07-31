"""Adaptador do que ainda NÃO virou Engine (hidrologia, astronomia, biomassa).

## Por que o adaptador embrulha o ORQUESTRADOR, e não cada subsistema

`TickOrchestrator.tick` cria UM `Generator` por tick e o passa aos subsistemas em
sequência: cada um consome sorteios de onde o anterior parou. A moldura,
corretamente, dá a cada Engine um fluxo independente. Dividir os restantes em um
Engine cada trocaria todos os sorteios sem nenhum ganho de fronteira — eles
seguem compartilhando a fatia `LEGACY` até migrarem de vez.

## O que mudou no M1

`geology` e `climate` saíram daqui: viraram Engines de verdade. Os dois
subsistemas que restaram e cuja ciência foi PARCIALMENTE migrada rodam com os
termos migrados **zerados nos parâmetros** (ver `orchestrator.reduced_params`),
não apenas com o resultado descartado. A diferença importa: zerando na origem, o
estado intermediário que `life` enxerga dentro do tick também fica correto, em
vez de carregar um carbono fantasma que seria descartado só no fim.
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
    """Expõe os subsistemas ainda não migrados como um Engine da moldura."""

    orchestrator: TickOrchestrator
    engine_id: str = LEGACY_ENGINE_ID
    # Lê tudo o que os subsistemas restantes precisam: a temperatura de verdade
    # (Climate) para o degelo, o CO2 (Atmosphere) e a geologia para a habitabilidade.
    reads: frozenset[SliceRef] = frozenset(
        {SliceRef.LEGACY, SliceRef.GEOLOGY, SliceRef.ATMOSPHERE, SliceRef.CLIMATE}
    )
    lagged_reads: frozenset[SliceRef] = frozenset()
    writes: SliceRef = SliceRef.LEGACY

    @property
    def subsystem_names(self) -> tuple[str, ...]:
        """Quem ainda roda por aqui — encolhe a cada marco."""
        return self.orchestrator.subsystem_names

    def tick(self, ctx: TickContext) -> TickResult:
        state = planet_state_of(ctx.snapshot)
        result = self.orchestrator.tick(state)
        # `difference` percorre apenas os campos da `LegacySlice`. Como
        # temperatura, CO2, energia, relevo e vulcanismo não existem mais nela,
        # é estruturalmente impossível este adaptador escrevê-los.
        values = difference(legacy_slice_of(state), legacy_slice_of(result.state))
        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values=values,
            ),
            entities_processed=len(self.orchestrator.subsystem_names),
        )
