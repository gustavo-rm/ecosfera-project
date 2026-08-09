"""Códex de espécies (GDD §11): o catálogo que se preenche conforme a vida evolui.

Cada `SpeciesRecord` é o registro inspecionável de uma espécie: seu genoma, quando
surgiu, de quem descende e — se for o caso — quando se extinguiu. A linhagem
(`ancestor_id`) transforma o códex numa árvore filogenética navegável, que é o
artefato pedagógico central deste incremento (RF-031).

Puro: sem DEAP, sem Mesa, sem I/O. A persistência é responsabilidade da porta
`PlanetRepository` (ADR 0001).

## AVISO — `ancestor_id` aqui expressa o modelo SUPERADO (BIO-001)

Este códex pertence ao **caminho B**, o de biologia por era, DORMENTE desde o M3
(`biology_enabled=False`, ADR 0017 tempo 1) e destinado à remoção no tempo 3.
Quem o preenche é `simulation_engine/biology/evolution.py`, que escolhe o
`ancestor_id` entre as espécies **vivas** — ou seja, afirma que uma espécie atual
gerou outra espécie atual. Essa é exatamente a ancestralidade que o BIO-001
corrige: o correto é um ancestral comum que se dividiu em duas linhagens irmãs.

A Fase 0 **não reescreve este caminho** — reescrevê-lo seria implementar a camada
de espécies, que a decisão de coortes (BIO-003, ADR 0024) deixou para depois do
M6. O que a Fase 0 garante é que o modelo CORRETO é o do Canal B do Evolution
Engine (`SpeciationOccurred` com um ancestral e duas linhagens), e que este
caminho continua dormente — `test_path_b_is_dormant` e
`test_speciation_is_common_ancestor` guardam as duas pontas.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ecosfera_ai.simulation_engine.biology.genome import Genome

# Tipos de evento biológico anexados ao event log append-only (ADR 0004).
EVENT_SPECIATION = "speciation"
EVENT_EXTINCTION = "extinction"


@dataclass(frozen=True, slots=True)
class SpeciesRecord:
    """Uma espécie no códex. Imutável: mudanças produzem um novo registro."""

    species_id: str
    planet_id: str
    genome: Genome
    emerged_era: int
    population: float
    fitness: float
    ancestor_id: str | None = None
    extinct_era: int | None = None

    @property
    def is_extinct(self) -> bool:
        return self.extinct_era is not None

    def with_population(self, population: float, fitness: float) -> SpeciesRecord:
        """Atualiza população/aptidão preservando a identidade e a linhagem."""
        return replace(self, population=max(0.0, population), fitness=fitness)

    def extinguished(self, era: int) -> SpeciesRecord:
        """Marca a extinção na era informada (população vai a zero)."""
        return replace(self, extinct_era=era, population=0.0)

    def to_dict(self) -> dict[str, Any]:
        """Serializa para persistência/API (JSONB no Postgres — ADR 0005)."""
        return {
            "species_id": self.species_id,
            "planet_id": self.planet_id,
            "genome": self.genome.to_dict(),
            "emerged_era": self.emerged_era,
            "population": self.population,
            "fitness": self.fitness,
            "ancestor_id": self.ancestor_id,
            "extinct_era": self.extinct_era,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeciesRecord:
        """Reconstrói tolerando chaves desconhecidas (compatibilidade de schema)."""
        return cls(
            species_id=str(data["species_id"]),
            planet_id=str(data["planet_id"]),
            genome=Genome.from_dict(dict(data["genome"])),
            emerged_era=int(data["emerged_era"]),
            population=float(data["population"]),
            fitness=float(data["fitness"]),
            ancestor_id=data.get("ancestor_id"),
            extinct_era=(int(data["extinct_era"]) if data.get("extinct_era") is not None else None),
        )


def species_id_for(planet_id: str, era: int, index: int) -> str:
    """Identificador determinístico de espécie.

    Derivado de (planeta, era, índice) em vez de UUID aleatório: o replay tem de
    reconstruir o MESMO códex, com os mesmos ids, a partir da mesma semente
    (RF-016/023). Um UUID quebraria essa igualdade.
    """
    return f"{planet_id}-e{era}-s{index}"


def living(catalog: list[SpeciesRecord]) -> list[SpeciesRecord]:
    """Filtra as espécies vivas do códex."""
    return [record for record in catalog if not record.is_extinct]
