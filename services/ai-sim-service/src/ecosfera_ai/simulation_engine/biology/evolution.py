"""Motor evolutivo com DEAP: seleção, cruzamento, mutação, especiação e extinção.

TASK-0048 / RF-031. Este é o primeiro módulo do serviço que cruza a fronteira
determinístico × IA (Dossiê §8): o resultado é **emergente** — ninguém roteiriza
quais espécies surgem —, mas é **reproduzível por semente** (RF-023), o que o
replay do Inc 2 exige para reconstruir o passado com exatidão.

## Como o determinismo é garantido

O DEAP usa o módulo `random` GLOBAL do Python em todos os seus operadores
(`cxBlend`, `mutGaussian`, `selTournament`). Para conciliar isso com
reprodutibilidade sem poluir o processo, cada execução:

  1. salva o estado global do `random`,
  2. semeia com a semente derivada de (semente do planeta, era),
  3. roda a evolução,
  4. **restaura** o estado anterior no `finally`.

Assim a mesma (semente, era) produz sempre a mesma sequência de espécies, e
nenhuma outra parte do processo tem seu RNG afetado.

O motor NÃO escreve no `PlanetState`: lê o ambiente e a capacidade de suporte e
devolve só o que é biológico (ADR 0006).

## Por que o DEAP é importado preguiçosamente (ADR 0017)

`EvolutionParams` vive aqui, e `simulation_engine/params.py` o importa para
montar o `SimulationParams` — que por sua vez é importado por
`engines/composition.py`. Com `from deap import ...` no topo, essa cadeia tornava
o `deap` requisito de importação de **toda a física**, apesar de o extra `sim`
ser declarado opcional: o serviço não subia sem ele.

A fábrica `_deap()` desfaz isso. O `deap` passa a ser tocado só quando este motor
roda de fato, e os nove Engines — inclusive o Ecology, que é aritmética pura —
importam e rodam sem o extra instalado.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from ecosfera_ai.simulation_engine.biology.codex import (
    SpeciesRecord,
    living,
    species_id_for,
)
from ecosfera_ai.simulation_engine.biology.fitness import FitnessParams, environmental_fitness
from ecosfera_ai.simulation_engine.biology.genome import TROPHIC_PRODUCER, Genome
from ecosfera_ai.simulation_engine.state import PlanetState


@lru_cache(maxsize=1)
def _deap() -> tuple[Any, Any, Any]:
    """Importa o DEAP e registra as classes do `creator` — só quando usado.

    O DEAP exige classes registradas no módulo `creator`. Criá-las UMA vez (e não
    a cada execução) evita o warning de redefinição e o vazamento de memória; o
    `lru_cache` é o que garante essa única vez agora que o registro deixou de
    acontecer na importação do módulo.
    """
    from deap import base, creator, tools

    if not hasattr(creator, "EcosferaFitnessMax"):
        creator.create("EcosferaFitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "EcosferaIndividual"):
        creator.create("EcosferaIndividual", list, fitness=creator.EcosferaFitnessMax)
    return base, creator, tools


@dataclass(frozen=True, slots=True)
class EvolutionParams:
    """Parâmetros do AG (dados versionados). Os tetos contêm o custo (RSK Inc 3)."""

    population_size: int
    generations: int
    mutation_rate: float
    mutation_sigma: float
    crossover_rate: float
    tournament_size: int
    speciation_threshold: float  # distância genética que caracteriza espécie nova
    extinction_fitness: float  # abaixo disto a espécie não se sustenta
    extinction_population: float  # população mínima viável
    max_species: int  # teto de espécies vivas simultâneas
    founder_population: float  # população inicial de uma espécie nova


@dataclass(frozen=True, slots=True)
class EvolutionOutcome:
    """Resultado de uma rodada evolutiva sobre uma era."""

    catalog: list[SpeciesRecord] = field(default_factory=list)
    speciated: list[SpeciesRecord] = field(default_factory=list)
    extinct: list[SpeciesRecord] = field(default_factory=list)
    generations: int = 0


@contextmanager
def _seeded_random(seed: int) -> Iterator[None]:
    """Semeia o `random` global do DEAP e restaura o estado anterior ao sair."""
    previous = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(previous)


class EvolutionEngine:
    """Estratégia evolutiva plugável, parametrizada por dados."""

    name = "evolution"

    def __init__(self, params: EvolutionParams, fitness_params: FitnessParams) -> None:
        self._p = params
        self._f = fitness_params

    # --- Aptidão ---------------------------------------------------------------
    def _fitness_of(self, genome: Genome, state: PlanetState, occupancy: float) -> float:
        return environmental_fitness(genome, state, self._f, occupancy=occupancy)

    def _toolbox(self, state: PlanetState, occupancy: float) -> Any:
        """Monta o toolbox do DEAP com os operadores genéticos configurados."""
        base, _, tools = _deap()
        toolbox = base.Toolbox()

        def evaluate(individual: Any) -> tuple[float]:
            return (self._fitness_of(Genome.from_vector(individual), state, occupancy),)

        toolbox.register("evaluate", evaluate)
        toolbox.register("mate", tools.cxBlend, alpha=0.5)
        toolbox.register(
            "mutate",
            tools.mutGaussian,
            mu=0.0,
            sigma=self._p.mutation_sigma,
            indpb=self._p.mutation_rate,
        )
        toolbox.register("select", tools.selTournament, tournsize=self._p.tournament_size)
        return toolbox

    # --- Ciclo evolutivo -------------------------------------------------------
    def evolve(
        self,
        catalog: list[SpeciesRecord],
        state: PlanetState,
        capacity: float,
        *,
        planet_id: str,
        era: int,
        seed: int,
    ) -> EvolutionOutcome:
        """Roda o AG sobre as espécies vivas e devolve o códex atualizado.

        Sem espécies vivas e com capacidade positiva, a primeira espécie é semeada
        a partir do ambiente (abiogênese já validada pelo `life.py` determinístico).
        """
        alive = living(catalog)
        occupancy = (sum(r.population for r in alive) / capacity) if capacity > 0.0 else 1.0

        with _seeded_random(seed):
            if capacity <= 0.0:
                # Ambiente inviável: tudo que estava vivo se extingue.
                return self._extinguish_all(catalog, era)
            if not alive:
                return self._seed_first_species(catalog, state, planet_id, era)
            outcome = self._run_generations(
                catalog, alive, state, capacity, occupancy, planet_id, era
            )
            return self._refill_producer_niche(outcome, state, planet_id, era)

    def _refill_producer_niche(
        self, outcome: EvolutionOutcome, state: PlanetState, planet_id: str, era: int
    ) -> EvolutionOutcome:
        """Repovoa a base da cadeia trófica quando ela fica vazia.

        A mutação pode empurrar todos os produtores para níveis consumidores. Uma
        teia alimentar sem base é ecologicamente impossível — e o nicho de
        produtor vago é justamente o que a seleção natural preenche primeiro. Sem
        esta regra, o modelo sustentaria herbívoros sem nada para comer.
        """
        alive = living(outcome.catalog)
        if not alive or any(r.genome.trophic_class <= TROPHIC_PRODUCER for r in alive):
            return outcome

        colonizer = self._founder_genome(state)
        record = SpeciesRecord(
            species_id=species_id_for(planet_id, era, len(outcome.catalog)),
            planet_id=planet_id,
            genome=colonizer,
            emerged_era=era,
            population=self._p.founder_population,
            fitness=self._fitness_of(colonizer, state, 0.0),
        )
        return EvolutionOutcome(
            catalog=[*outcome.catalog, record],
            speciated=[*outcome.speciated, record],
            extinct=outcome.extinct,
            generations=outcome.generations,
        )

    def _founder_genome(self, state: PlanetState) -> Genome:
        """Genoma de um produtor colonizador, adaptado ao ambiente vigente."""
        return Genome(
            temp_optimum=state.temperature,
            temp_tolerance=random.uniform(5.0, 25.0),
            water_need=random.uniform(0.05, 0.4),
            size=random.uniform(0.05, 1.0),
            metabolism=random.uniform(0.1, 0.8),
            trophic_level=1.0,
        ).clamped()

    def _extinguish_all(self, catalog: list[SpeciesRecord], era: int) -> EvolutionOutcome:
        extinct = [record.extinguished(era) for record in living(catalog)]
        by_id = {record.species_id: record for record in extinct}
        updated = [by_id.get(record.species_id, record) for record in catalog]
        return EvolutionOutcome(catalog=updated, extinct=extinct)

    def _seed_first_species(
        self, catalog: list[SpeciesRecord], state: PlanetState, planet_id: str, era: int
    ) -> EvolutionOutcome:
        """Semeia o primeiro produtor, adaptado ao ambiente vigente."""
        founder = self._founder_genome(state)
        record = SpeciesRecord(
            species_id=species_id_for(planet_id, era, len(catalog)),
            planet_id=planet_id,
            genome=founder,
            emerged_era=era,
            population=self._p.founder_population,
            fitness=self._fitness_of(founder, state, 0.0),
        )
        return EvolutionOutcome(catalog=[*catalog, record], speciated=[record], generations=0)

    def _run_generations(
        self,
        catalog: list[SpeciesRecord],
        alive: list[SpeciesRecord],
        state: PlanetState,
        capacity: float,
        occupancy: float,
        planet_id: str,
        era: int,
    ) -> EvolutionOutcome:
        toolbox = self._toolbox(state, occupancy)
        population = self._initial_population(alive, toolbox)

        for individual in population:
            individual.fitness.values = toolbox.evaluate(individual)

        _, creator, _ = _deap()
        for _ in range(self._p.generations):
            offspring = [
                creator.EcosferaIndividual(ind)
                for ind in toolbox.select(population, len(population))
            ]
            for child in offspring:
                child.fitness = creator.EcosferaFitnessMax()

            for first, second in zip(offspring[::2], offspring[1::2], strict=False):
                if random.random() < self._p.crossover_rate:
                    toolbox.mate(first, second)
            for child in offspring:
                if random.random() < self._p.mutation_rate:
                    toolbox.mutate(child)
            for child in offspring:
                child.fitness.values = toolbox.evaluate(child)
            population = offspring

        return self._speciate_and_extinguish(
            catalog, alive, population, state, capacity, planet_id, era
        )

    def _initial_population(self, alive: list[SpeciesRecord], toolbox: Any) -> list[Any]:
        """População inicial: cópias mutadas dos genomas vivos (variação intraespecífica)."""
        _, creator, _ = _deap()
        seeds = [record.genome.to_vector() for record in alive]
        population: list[Any] = []
        while len(population) < self._p.population_size:
            base_vector = list(seeds[len(population) % len(seeds)])
            individual = creator.EcosferaIndividual(base_vector)
            if population:  # o primeiro clone preserva o genoma parental intacto
                toolbox.mutate(individual)
            population.append(individual)
        return population

    def _speciate_and_extinguish(
        self,
        catalog: list[SpeciesRecord],
        alive: list[SpeciesRecord],
        population: list[Any],
        state: PlanetState,
        capacity: float,
        planet_id: str,
        era: int,
    ) -> EvolutionOutcome:
        """Converte a população evoluída em eventos de especiação/extinção."""
        updated: dict[str, SpeciesRecord] = {r.species_id: r for r in catalog}
        speciated: list[SpeciesRecord] = []

        # 1. Cada espécie viva adota o melhor indivíduo próximo ao seu genoma.
        for record in alive:
            candidates = [
                genome
                for genome in (Genome.from_vector(ind) for ind in population)
                if record.genome.distance(genome) <= self._p.speciation_threshold
            ]
            if not candidates:
                continue
            best = max(candidates, key=lambda g: self._fitness_of(g, state, 0.0))
            fitness = self._fitness_of(best, state, 0.0)
            updated[record.species_id] = record.with_population(record.population, fitness)

        # 2. Divergentes acima do limiar viram espécies novas (especiação).
        living_genomes = [updated[r.species_id].genome for r in alive]
        slots = max(0, self._p.max_species - len(alive))
        for individual in population:
            if slots <= 0:
                break
            genome = Genome.from_vector(individual)
            diverged = all(
                genome.distance(existing) > self._p.speciation_threshold
                for existing in living_genomes
            )
            if diverged:
                fitness = self._fitness_of(genome, state, 0.0)
                if fitness < self._p.extinction_fitness:
                    continue  # inviável ao nascer: não vira espécie
                # ANCESTRALIDADE SUPERADA (BIO-001): o "ancestral" é escolhido
                # entre as espécies VIVAS, o que afirma que uma espécie atual
                # gerou outra espécie atual. O modelo correto — um ancestral
                # comum que se divide em duas linhagens irmãs — vive no Canal B
                # do Evolution Engine. Este caminho está dormente (ADR 0017) e
                # sai no tempo 3; não é reescrito aqui porque reescrevê-lo seria
                # implementar a camada de espécies, que é pós-M6 (ADR 0024).
                ancestor = min(alive, key=lambda r: r.genome.distance(genome))
                record = SpeciesRecord(
                    species_id=species_id_for(planet_id, era, len(updated)),
                    planet_id=planet_id,
                    genome=genome,
                    emerged_era=era,
                    population=self._p.founder_population,
                    fitness=fitness,
                    ancestor_id=ancestor.species_id,
                )
                updated[record.species_id] = record
                speciated.append(record)
                living_genomes.append(genome)
                slots -= 1

        # 3. Extinção: aptidão ou população abaixo do mínimo viável.
        extinct: list[SpeciesRecord] = []
        for record in living(list(updated.values())):
            if (
                record.fitness < self._p.extinction_fitness
                or record.population < self._p.extinction_population
            ):
                gone = record.extinguished(era)
                updated[record.species_id] = gone
                extinct.append(gone)

        return EvolutionOutcome(
            catalog=list(updated.values()),
            speciated=speciated,
            extinct=extinct,
            generations=self._p.generations,
        )
