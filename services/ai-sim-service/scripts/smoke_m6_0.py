"""Roteiro de fumaça do M6.0 — o dossiê factual de uma corrida REAL, sem LLM.

    uv run python scripts/smoke_m6_0.py            # com o extra `sim`
    uv run --no-extra sim python scripts/smoke_m6_0.py   # sem ele

Roda um planeta com meteoro declarado, monta o `FactualContext` da era e imprime
o JSON para inspeção humana. O que se confere a olho, e o que o script afirma:

  1. a cadeia meteoro → (resfriamento, extinção) está INTACTA e navegável nas
     duas direções;
  2. a distinção catastrófica × ecológica sobreviveu à travessia (ADR 0019);
  3. não há UMA LINHA de prosa no dossiê — só código, número e identificador;
  4. o dossiê é determinístico: a mesma corrida o reproduz idêntico.

**Horizonte:** 400 ticks, dentro do horizonte quase-estacionário do ADR 0020.

**Sem LLM.** O M6.0 é a fundação factual, e ela é anterior ao gerador de
propósito: primeiro o fato verificável, depois quem o reescreve (M6.3).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "tests")

from ecosfera_ai.application.consumers.assemble_context import ContextAssembler
from ecosfera_ai.application.platform.event_query import InMemoryEventQuery
from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    ExtinctionNature,
    FactualContext,
)
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.engines.event.events import METEOR_IMPACT
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from support import build_scripted_planet

HORIZON = 400
PLANET = "planet-smoke-m6"
PARAMS = load_params(Path("configs/simulation_params.yaml"))

# Prosa NÃO pode aparecer no dossiê. A varredura é mecânica de propósito: toda
# string que sai dali é identificador, código ou chave de campo.
PROSE_MARKERS = ("porque", "espécie ", "aluno", "aconteceu", "ancestral comum")


def run() -> list[DomainEvent]:
    """Uma corrida com meteoro LETAL declarado, sobre um planeta com vida."""
    store = InMemoryEventStore()
    planet = build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("meteor", 2027), PARAMS))
    for _ in range(HORIZON):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.scientific_view())


async def assemble(trail: list[DomainEvent], era: int) -> FactualContext:
    assembler = ContextAssembler(InMemoryEventQuery.of(PLANET, trail))
    return await assembler.execute(PLANET, ContextSlice.of_era(era))


def main() -> int:
    trail = run()
    era = trail[-1].occurred_at.era
    context = asyncio.run(assemble(trail, era))

    payload = json.dumps(context.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)

    print(f"\n--- dossiê da era {era} do planeta {PLANET} ---")
    print(f"eventos: {len(context.events)}")
    print(f"raízes causais: {len(context.causal_roots)}")
    print(f"marcadores: {len(context.markers)}")
    print(f"especiações: {len(context.speciations)}  (raras até a Fase 2 — deferred.md)")
    print(f"extinções: {len(context.extinctions)}")

    # 1. a cadeia está intacta e navegável
    meteors = [e for e in context.events if e.event_type == METEOR_IMPACT]
    assert meteors, "a corrida não produziu meteoro — o cenário deixou de valer"
    downstream = context.consequences_of(meteors[0].event_id)
    assert downstream, "o meteoro não tem consequência alguma: a cadeia se perdeu"
    print(f"consequências do meteoro: {len(downstream)} evento(s)")

    for extinction in context.extinctions:
        assert context.event(extinction.event_id) is not None
        print(f"  extinção {extinction.cause_code} -> {extinction.nature.value}")

    # 2. a distinção do ADR 0019 sobreviveu
    natures = {f.nature for f in context.extinctions}
    assert natures <= {ExtinctionNature.CATASTROPHIC, ExtinctionNature.ECOLOGICAL}

    # 3. nem uma linha de prosa
    for marker in PROSE_MARKERS:
        assert marker not in payload, f"o dossiê contém prosa: {marker!r}"

    # 4. determinismo
    again = asyncio.run(assemble(run(), era))
    assert again.to_dict() == context.to_dict(), "o dossiê não é determinístico"

    print("\nOK — dossiê factual íntegro, navegável, sem prosa e determinístico.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
