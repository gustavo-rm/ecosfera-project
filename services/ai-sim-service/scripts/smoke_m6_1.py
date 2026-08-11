"""Roteiro de fumaça do M6.1 — o piso de qualidade, numa corrida REAL, sem LLM.

    uv run python scripts/smoke_m6_1.py            # com o extra `sim`
    uv run --no-extra sim python scripts/smoke_m6_1.py   # sem ele

Roda um planeta com meteoro declarado, monta o dossiê factual do M6.0 e o narra
com os templates do M6.1. O que se confere a olho, e o que o script afirma:

  1. a extinção CATASTRÓFICA nunca culpa a adaptação, e NOMEIA o evento extremo
     que a causou — vindo do `causation_id` real, não de plausibilidade;
  2. a extinção ECOLÓGICA fala de ambiente e adaptação, com aptidão CONTEXTUAL;
  3. se a corrida produzir especiação, ela lê como ancestral comum + duas
     linhagens irmãs, jamais como "A deu origem a B";
  4. toda afirmação é rastreável a um campo do dossiê;
  5. a mesma corrida produz a mesma prosa, palavra por palavra.

É esta saída que o LLM do M6.3 vai ter de superar. Se ele não superar, não entra.

**Horizonte:** 400 ticks, dentro do horizonte quase-estacionário do ADR 0020.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, "tests")

from ecosfera_ai.application.consumers.render_explanation import ExplanationRenderer
from ecosfera_ai.domain.consumers.explanation import Explanation, Register
from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    ExtinctionNature,
    FactualContext,
)
from ecosfera_ai.domain.consumers.templates import load_templates
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from support import build_scripted_planet

HORIZON = 400
PLANET = "planet-smoke-m61"
PARAMS = load_params(Path("configs/simulation_params.yaml"))
NUMBER = re.compile(r"\d+")

# Formulações que culpariam a comunidade pela própria morte.
BLAMING = ("não conseguiu se adaptar", "não se adaptou", "era inferior", "não tolerou")


def run() -> list[DomainEvent]:
    """Uma corrida com meteoro LETAL declarado, sobre um planeta com vida."""
    store = InMemoryEventStore()
    planet = build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0, sink=store)
    snapshot = snapshot_of(initial_state(PlanetSeed("meteor", 2027), PARAMS))
    for _ in range(HORIZON):
        snapshot = planet.tick(snapshot).snapshot
    return list(store.scientific_view())


def explain(trail: list[DomainEvent], era: int) -> tuple[FactualContext, Explanation]:
    context = FactualContext.of(PLANET, ContextSlice.of_era(era), tuple(trail))
    renderer = ExplanationRenderer(load_templates(Path("configs/explanation_templates.yaml")))
    return context, renderer.render(context, Register.STANDARD)


def main() -> int:
    trail = run()
    era = trail[-1].occurred_at.era
    context, explanation = explain(trail, era)

    print(f"--- explicação da era {era} do planeta {PLANET} ---\n")
    for fact in explanation.facts:
        print(f"[{fact.template_id}] {fact.text}\n")

    print(f"eventos no dossiê: {len(context.events)}")
    print(f"frases narradas:   {len(explanation.facts)}")
    print(f"extinções:         {len(context.extinctions)}")
    print(f"especiações:       {len(context.speciations)} (raras até a Fase 2)\n")

    # 1. a catastrófica nunca culpa a adaptação, e nomeia o gatilho
    catastrophic = [f for f in context.extinctions if f.nature is ExtinctionNature.CATASTROPHIC]
    assert catastrophic, "a corrida não produziu extinção catastrófica — o cenário não vale"
    for fact in catastrophic:
        sentence = next(f for f in explanation.facts if f.grounding.event_id == fact.event_id)
        lowered = sentence.text.lower()
        for phrase in BLAMING:
            assert phrase not in lowered, f"a catástrofe culpou a comunidade: {sentence.text!r}"
        assert "por mais bem adaptada" in lowered or "não foi culpa dela" in lowered
    print(f"OK — {len(catastrophic)} extinção(ões) catastrófica(s), nenhuma culpa a adaptação.")

    # 2. a ecológica fala de ambiente, e é diferente da catastrófica
    ecological = [f for f in context.extinctions if f.nature is ExtinctionNature.ECOLOGICAL]
    for fact in ecological:
        sentence = next(f for f in explanation.facts if f.grounding.event_id == fact.event_id)
        lowered = sentence.text.lower()
        assert "em outro ambiente" in lowered, f"a ecológica perdeu o contexto: {sentence.text!r}"
        assert "evento extremo" not in lowered
    print(f"OK — {len(ecological)} extinção(ões) ecológica(s), todas contextuais.")

    # 3. especiação, se houver, é ancestral comum
    for fact in context.speciations:
        sentence = next(f for f in explanation.facts if f.grounding.event_id == fact.event_id)
        lowered = sentence.text.lower()
        assert "ancestral comum" in lowered and "irmãs" in lowered
        assert "deu origem" not in lowered
    if context.speciations:
        print(f"OK — {len(context.speciations)} especiação(ões), todas por ancestral comum.")
    else:
        print("OK — nenhuma especiação nesta corrida (o caso comum até a Fase 2).")

    # 4. tudo o que a prosa afirma vem do dossiê
    known = {event.event_id for event in context.events}
    for fact in explanation.facts:
        if fact.grounding.event_id is not None:
            assert fact.grounding.event_id in known, "frase ancorada em evento fora do dossiê"
        for number in NUMBER.findall(fact.text):
            assert number in set(fact.slots.values()), (
                f"o número {number!r} apareceu sem vir do dossiê: {fact.text!r}"
            )
    assert explanation.summary == " ".join(f.text for f in explanation.facts)
    print("OK — toda afirmação é rastreável a um campo do dossiê.")

    # 5. determinismo
    _, again = explain(run(), era)
    assert again.to_dict() == explanation.to_dict(), "a explicação não é determinística"
    print("OK — a mesma corrida produz a mesma prosa, palavra por palavra.")

    print("\nPISO DE QUALIDADE estabelecido. O LLM do M6.3 terá de superá-lo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
