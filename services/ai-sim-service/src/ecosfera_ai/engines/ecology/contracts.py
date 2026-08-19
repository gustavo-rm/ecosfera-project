"""Fatias e parâmetros do Ecology Engine (Spec §5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from ecosfera_ai.shared_kernel.world_state import SliceRef

ENGINE_ID = "ecology"

# Lê a comunidade que a Evolution acabou de resolver (mesmo tick) e o orçamento
# que o Resource publicou. Fecha a ordem do tick, então não precisa de defasagem.
WRITES = SliceRef.ECOLOGY
READS: frozenset[SliceRef] = frozenset({SliceRef.BIOTA, SliceRef.RESOURCE})
# A mortalidade catastrófica chega pela `EventSlice`, lida DEFASADA (o Event
# roda por último). É por ela que uma espécie BEM ADAPTADA pode morrer — a
# correção de concepção equivocada do M4 (ADR 0019).
LAGGED_READS: frozenset[SliceRef] = frozenset({SliceRef.EVENT})

PARAMS_PATH = Path(__file__).parent / "params.yaml"


@dataclass(frozen=True, slots=True)
class EcologyEngineParams:
    """Ciência do Engine como DADO versionado (Spec §5.1)."""

    version: int
    steps_per_tick: int
    growth_rate: float
    predation_rate: float
    conversion_efficiency: float
    mortality_rate: float
    demographic_noise: float
    min_viable_population: float
    herbivore_share: float
    predator_share: float
    max_consumer_share: float
    consumer_capacity_share: float
    collapse_threshold: float
    decline_threshold: float
    max_agents: int
    max_steps: int
    max_duration_s: float
    max_events: int
    # ECO-001 (Fase 1): dieta generalista do predador, destravada por era.
    # `unlock_era`/`full_era` delimitam a rampa da onivoria (força 0 → 1); os
    # pesos da dieta na força plena somam 1. Ausentes (params v1), o carregador
    # assume `producer=0`, e a dieta é (herbívoro=1, produtor=0) em toda era —
    # cadeia estrita, idêntica ao M4.
    generalist_unlock_era: int
    generalist_full_era: int
    predator_diet_herbivore: float
    predator_diet_producer: float


def load_params(path: Path = PARAMS_PATH) -> EcologyEngineParams:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    budget = raw.get("budget", {})
    generalist = _load_generalist(raw.get("generalist"))
    ints = {"steps_per_tick", "max_agents", "max_steps"}
    # `generalist` é um bloco aninhado, não um escalar: fica fora da conversão
    # para float, e entra pelos campos tipados de `_load_generalist`.
    reserved = ints | {"version", "budget", "generalist"}
    fields = {k: float(v) for k, v in raw.items() if k not in reserved}
    return EcologyEngineParams(
        version=int(raw["version"]),
        steps_per_tick=int(raw["steps_per_tick"]),
        max_agents=int(raw["max_agents"]),
        max_steps=int(raw["max_steps"]),
        max_duration_s=float(budget.get("max_duration_s", 0.25)),
        max_events=int(budget.get("max_events", 100)),
        generalist_unlock_era=generalist.unlock_era,
        generalist_full_era=generalist.full_era,
        predator_diet_herbivore=generalist.diet_herbivore,
        predator_diet_producer=generalist.diet_producer,
        **fields,
    )


class _Generalist(NamedTuple):
    """Bloco `generalist` do YAML, achatado e tipado para o construtor."""

    unlock_era: int
    full_era: int
    diet_herbivore: float
    diet_producer: float


def _load_generalist(raw: dict[str, Any] | None) -> _Generalist:
    """Lê o bloco `generalist` do YAML nos campos tipados do dataclass.

    Ausente (params v1), assume cadeia estrita: `producer=0` faz a dieta valer
    (herbívoro=1, produtor=0) em qualquer era. Presente, exige que os pesos somem
    1 — um dado versionado incoerente é erro de configuração, não deriva a
    absorver em silêncio.
    """
    if not raw:
        return _Generalist(unlock_era=0, full_era=0, diet_herbivore=1.0, diet_producer=0.0)
    diet = raw.get("predator_diet", {})
    herbivore = float(diet.get("herbivore", 1.0))
    producer = float(diet.get("producer", 0.0))
    if abs((herbivore + producer) - 1.0) > 1e-9:
        raise ValueError(
            f"os pesos da dieta do predador devem somar 1, não {herbivore + producer:.6f} "
            f"(herbívoro={herbivore}, produtor={producer})"
        )
    unlock = int(raw.get("unlock_era", 0))
    full = int(raw.get("full_era", unlock))
    if full < unlock:
        raise ValueError(
            f"generalist.full_era ({full}) não pode ser antes de unlock_era ({unlock})"
        )
    return _Generalist(
        unlock_era=unlock, full_era=full, diet_herbivore=herbivore, diet_producer=producer
    )
