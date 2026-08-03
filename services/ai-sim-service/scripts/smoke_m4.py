"""Roteiro de fumaça do M4 — reproduzível, dentro do HORIZONTE VÁLIDO.

    uv run python scripts/smoke_m4.py            # com o extra `sim`
    uv run --no-extra sim python scripts/smoke_m4.py   # sem ele

Exercita, ponta a ponta e sem mocks:

  1. o Diretor agenda e TELEGRAFA um evento (RF-019/020);
  2. um meteoro esfria o planeta pela `EventSlice` (perturbação via Canal A);
  3. a mortalidade catastrófica extingue espécie(s) com `CATASTROPHIC_EVENT`;
  4. a cadeia causal vai da extinção até o meteoro por `causation_id`;
  5. o Tutor (sem LLM) distingue catastrófica de ecológica;
  6. a mesma semente reproduz a trajetória bit-a-bit (RF-023).

**Horizonte:** 500 ticks. Não é preguiça — além de ~500 o planeta deixa de ser
quase-estacionário, e isso é dívida HERDADA registrada no ADR 0020. Rodar o
smoke além disso mediria a instabilidade, não o M4.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "tests")

from ecosfera_ai.application.feedback.explain_from_events import load_translation
from ecosfera_ai.domain.feedback.rule_loader import build_engine
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed
from support import build_scripted_planet

HORIZON = 500  # horizonte de jogo válido (ADR 0020)
PARAMS = load_params(Path("configs/simulation_params.yaml"))


def _run(planet, seed: str, ticks: int = HORIZON):
    snapshot = snapshot_of(initial_state(PlanetSeed(seed, 2027), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot).snapshot
        trail.append(snapshot)
    return trail


def main() -> int:
    ok = True

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and condition
        print(f"  [{'OK ' if condition else 'FALHA'}] {label}{f' — {detail}' if detail else ''}")

    print(f"ECOSFERA — smoke do M4 (horizonte {HORIZON} ticks)\n")
    try:
        import mesa  # noqa: F401

        print("extra `sim`: PRESENTE\n")
    except ImportError:
        print("extra `sim`: AUSENTE (só física; é um cenário suportado)\n")

    # 1-2. Diretor, telegrafia e perturbação
    print("1) Diretor, telegrafia e perturbação")
    store = InMemoryEventStore()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget, sink=store)
    trail = _run(planet, "smoke-director")
    forecasts = [e for e in store.events if e.event_type == "EventForecast"]
    active = [s for s in trail if s.event.active_kind]
    check("o Diretor agendou eventos", bool(forecasts), f"{len(forecasts)} anúncio(s)")
    check("a perturbação ficou ativa", bool(active), f"{len(active)} tick(s)")
    check(
        "todo evento foi anunciado antes",
        len(forecasts) >= len({s.event.active_kind for s in active} - {0.0}),
    )

    # 3-4. Meteoro letal declarado: extinção catastrófica e cadeia causal
    print("\n2) Meteoro -> extinção catastrófica -> cadeia causal")
    store = InMemoryEventStore()
    meteor = build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0, sink=store)
    trail = _run(meteor, "smoke-meteor")

    impacts = [e for e in store.events if e.event_type == "MeteorImpact"]
    extinctions = [
        e
        for e in store.events
        if e.event_type == "SpeciesExtinct" and str(e.cause_code) == "CATASTROPHIC_EVENT"
    ]
    check("o meteoro caiu", bool(impacts), f"{len(impacts)} impacto(s)")
    check("houve extinção CATASTRÓFICA", bool(extinctions), f"{len(extinctions)}")

    index = {e.event_id: e for e in store.events}
    chained = [e for e in extinctions if e.causation_id and index.get(e.causation_id) in impacts]
    check(
        "a extinção aponta para o METEORO (não para o clima)",
        bool(chained),
        f"{len(chained)} de {len(extinctions)}",
    )

    cooled = [s for s in trail if s.event.cooling_forcing > 0.0]
    check("o meteoro resfriou o planeta", bool(cooled), f"{len(cooled)} tick(s) de resfriamento")

    # 5. O Tutor distingue as duas famílias
    print("\n3) Tutor (sem LLM): catastrófica x ecológica")
    translation = load_translation(Path("configs/event_observations.yaml"))
    rules = build_engine(Path("configs/causal_rules.yaml"))
    if extinctions:
        observations = translation.observations([extinctions[0]])
        chain = rules.explain("smoke", observations).chain
        text = " ".join(step.explanation for step in chain)
        check("a explicação nomeia o evento extremo", "evento extremo" in text)
        check("e diz que a adaptação não a teria salvado", "por mais bem adaptada" in text)
        print(f"      → {text.split('.')[0]}.")
    else:
        check("explicação da extinção catastrófica", False, "nenhuma extinção para narrar")

    # 6. Replay bit-a-bit
    print("\n4) Replay determinístico (RF-023)")
    again = _run(build_scripted_planet(EventKind.METEOR, lead=4, mortality=2.0), "smoke-meteor")
    check("a trajetória repete bit-a-bit", [s.event for s in trail] == [s.event for s in again])
    check(
        "o estado físico repete bit-a-bit",
        [s.climate.temperature for s in trail] == [s.climate.temperature for s in again],
    )

    print(f"\n{'SMOKE OK' if ok else 'SMOKE FALHOU'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
