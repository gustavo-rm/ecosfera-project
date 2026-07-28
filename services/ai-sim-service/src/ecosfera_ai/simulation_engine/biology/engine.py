"""Fachada da biologia emergente: uma era de evolução + ecologia (ADR 0006).

Reúne o AG (`evolution`) e o ABM (`ecology`) num único passo por era e — o mais
importante — centraliza a **derivação da semente**. Tanto o avanço de era quanto
o replay usam esta mesma fachada, o que é o que garante que reconstruir o passado
produza o MESMO códex e as MESMAS populações (RF-016/023).

Regra de fronteira (Dossiê §8): este módulo LÊ o `PlanetState` e a capacidade de
suporte publicada pelo `life.py` determinístico, e NUNCA os escreve. Todo o
resultado é biológico (espécies e populações), persistido em tabelas próprias.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord, living
from ecosfera_ai.simulation_engine.biology.ecology import (
    EcologyParams,
    PopulationSnapshot,
    simulate_ecology,
)
from ecosfera_ai.simulation_engine.biology.evolution import EvolutionEngine
from ecosfera_ai.simulation_engine.state import PlanetState

# Sal que separa o fluxo da biologia do fluxo determinístico dentro da mesma
# semente de planeta: sem ele, biologia e clima consumiriam a mesma sequência.
_BIOLOGY_SALT = 0xB10


def biology_seed(planet_seed: int, era: int) -> int:
    """Deriva a semente da biologia a partir de (semente do planeta, era).

    Usa `SeedSequence` — o mesmo mecanismo do orquestrador determinístico — para
    obter independência estatística entre eras mantendo reprodutibilidade total.
    """
    sequence = np.random.SeedSequence([planet_seed, era, _BIOLOGY_SALT])
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


@dataclass(frozen=True, slots=True)
class BiologyOutcome:
    """Resultado biológico de uma era."""

    catalog: list[SpeciesRecord] = field(default_factory=list)
    speciated: list[SpeciesRecord] = field(default_factory=list)
    extinct: list[SpeciesRecord] = field(default_factory=list)
    populations: list[PopulationSnapshot] = field(default_factory=list)
    generations: int = 0

    @property
    def living_species(self) -> list[SpeciesRecord]:
        return living(self.catalog)


class BiologyEngine:
    """Compõe evolução e ecologia numa era, de forma reprodutível por semente."""

    def __init__(self, evolution: EvolutionEngine, ecology: EcologyParams) -> None:
        self._evolution = evolution
        self._ecology = ecology

    def advance_era(
        self,
        catalog: list[SpeciesRecord],
        state: PlanetState,
        capacity: float,
        *,
        planet_id: str,
        era: int,
    ) -> BiologyOutcome:
        """Roda uma era: seleção/especiação/extinção e depois a dinâmica trófica."""
        seed = biology_seed(state.seed, era)

        evolved = self._evolution.evolve(
            catalog, state, capacity, planet_id=planet_id, era=era, seed=seed
        )
        ecology = simulate_ecology(living(evolved.catalog), capacity, self._ecology, seed=seed)

        # As populações apuradas pelo ABM voltam ao códex (a evolução decide QUEM
        # existe; a ecologia decide QUANTOS).
        updated = [
            record.with_population(ecology.population_of(record.species_id), record.fitness)
            if not record.is_extinct
            else record
            for record in evolved.catalog
        ]

        # Uma espécie cuja população colapsou na era também se extingue: sem isso
        # o códex acumularia espécies vivas com zero indivíduos.
        collapsed = [
            record.extinguished(era) for record in living(updated) if record.population <= 0.0
        ]
        collapsed_ids = {record.species_id for record in collapsed}
        catalog_out = [
            next(c for c in collapsed if c.species_id == record.species_id)
            if record.species_id in collapsed_ids
            else record
            for record in updated
        ]

        return BiologyOutcome(
            catalog=catalog_out,
            speciated=evolved.speciated,
            extinct=[*evolved.extinct, *collapsed],
            populations=ecology.populations,
            generations=evolved.generations,
        )
