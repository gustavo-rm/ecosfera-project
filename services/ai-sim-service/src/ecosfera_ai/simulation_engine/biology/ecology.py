"""Modelo ecológico com Mesa: dinâmica trófica EMERGENTE (TASK-0050/0051, RF-032).

Cada agente é uma **população de espécie** (não um indivíduo): a agregação é o que
torna o custo tratável — o teto de agentes é o número de espécies vivas, não o de
organismos (mitigação do RSK de custo computacional do Inc 3).

As oscilações predador-presa **emergem** das regras locais de cada agente; não há
equação de Lotka-Volterra escrita em lugar nenhum. Cada população só sabe:

  - produtores crescem logisticamente até a capacidade de suporte que a camada
    determinística (`life.py`) oferece;
  - consumidores crescem proporcionalmente ao que conseguem predar no nível
    trófico abaixo, e morrem por manutenção;
  - toda predação retira biomassa da presa.

Da soma dessas regras nascem os ciclos clássicos — que é exatamente o fenômeno
que o aluno deve observar e explicar.

Reprodutibilidade (RF-023): `mesa.Model` é semeado por `seed=`, derivado da
semente do planeta e da era. O modelo NÃO escreve no `PlanetState` (ADR 0006).
"""

from __future__ import annotations

from dataclasses import dataclass

import mesa

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.genome import (
    TROPHIC_PRODUCER,
)

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class EcologyParams:
    """Parâmetros da dinâmica ecológica (dados versionados).

    `max_agents` e `max_steps` são tetos de custo, não de ciência: contêm o pior
    caso de tempo por era (RSK Inc 3).
    """

    steps: int
    growth_rate: float  # crescimento intrínseco dos produtores
    predation_rate: float  # eficiência de captura por unidade de predador
    conversion_efficiency: float  # fração da presa convertida em predador
    mortality_rate: float  # mortalidade natural dos consumidores
    demographic_noise: float  # ruído demográfico (semeado)
    min_viable_population: float  # abaixo disto a população colapsa a zero
    max_agents: int  # teto de populações simuladas
    max_steps: int  # teto absoluto de passos por era


@dataclass(frozen=True, slots=True)
class PopulationSnapshot:
    """Fotografia populacional de uma espécie ao fim da era."""

    species_id: str
    population: float
    trophic_level: int


@dataclass(frozen=True, slots=True)
class EcologyOutcome:
    """Resultado da simulação ecológica de uma era."""

    populations: list[PopulationSnapshot]
    history: list[dict[str, float]]  # população por espécie a cada passo

    def population_of(self, species_id: str) -> float:
        for snapshot in self.populations:
            if snapshot.species_id == species_id:
                return snapshot.population
        return 0.0


class PopulationAgent(mesa.Agent):  # type: ignore[misc]
    """Agente = população de uma espécie. Sabe apenas comer, crescer e morrer."""

    def __init__(
        self,
        model: EcologyModel,
        species_id: str,
        trophic_level: int,
        population: float,
        metabolism: float,
    ) -> None:
        super().__init__(model)
        self.species_id = species_id
        self.trophic_level = trophic_level
        self.population = population
        self.metabolism = metabolism
        self.consumed = 0.0  # biomassa capturada no passo corrente

    def step(self) -> None:
        """Regra local do agente; a dinâmica global emerge da soma delas."""
        params = self.model.params
        if self.trophic_level <= TROPHIC_PRODUCER:
            self._grow_as_producer(params)
        else:
            self._grow_as_consumer(params)

        # Ruído demográfico proporcional à população (semeado pelo modelo).
        if params.demographic_noise > 0.0:
            self.population += (
                self.model.random.gauss(0.0, params.demographic_noise) * self.population
            )

        if self.population < params.min_viable_population:
            self.population = 0.0
        self.population = max(0.0, self.population)

    def _grow_as_producer(self, params: EcologyParams) -> None:
        """Crescimento logístico dentro da capacidade que o ambiente oferece."""
        capacity = self.model.producer_capacity
        if capacity <= 0.0:
            self.population -= params.mortality_rate * self.population
            return
        occupied = self.model.total_producer_population()
        self.population += (
            params.growth_rate * self.population * (1.0 - occupied / max(capacity, _EPS))
        )
        self.population -= self.consumed  # o que foi predado neste passo

    def _grow_as_consumer(self, params: EcologyParams) -> None:
        """Cresce com o que predou no nível abaixo e paga a manutenção."""
        prey = self.model.prey_available(self.trophic_level)
        captured = params.predation_rate * self.population * prey
        captured = min(captured, prey)  # não se come mais presa do que existe
        self.model.register_predation(self.trophic_level, captured)

        self.population += params.conversion_efficiency * captured
        self.population -= params.mortality_rate * self.metabolism * self.population
        self.population -= self.consumed  # predado pelo nível acima


class EcologyModel(mesa.Model):  # type: ignore[misc]
    """Modelo Mesa que compõe as populações e resolve a cadeia trófica."""

    def __init__(
        self,
        species: list[SpeciesRecord],
        capacity: float,
        params: EcologyParams,
        seed: int,
    ) -> None:
        super().__init__(seed=seed)
        self.params = params
        self.producer_capacity = max(0.0, capacity)
        self._predation_by_level: dict[int, float] = {}
        self.history: list[dict[str, float]] = []

        # Contenção de custo: só as espécies mais populosas entram no modelo.
        ranked = sorted(species, key=lambda r: r.population, reverse=True)
        for record in ranked[: params.max_agents]:
            PopulationAgent(
                model=self,
                species_id=record.species_id,
                trophic_level=record.genome.trophic_class,
                population=record.population,
                metabolism=record.genome.metabolism,
            )

    # --- Consultas usadas pelos agentes ---------------------------------------
    def populations(self) -> list[PopulationAgent]:
        agents: list[PopulationAgent] = list(self.agents)
        return agents

    def total_producer_population(self) -> float:
        return sum(a.population for a in self.populations() if a.trophic_level <= TROPHIC_PRODUCER)

    def prey_available(self, trophic_level: int) -> float:
        """Biomassa disponível no nível imediatamente abaixo do predador."""
        prey_level = max(TROPHIC_PRODUCER, trophic_level - 1)
        return sum(a.population for a in self.populations() if a.trophic_level == prey_level)

    def register_predation(self, predator_level: int, captured: float) -> None:
        """Contabiliza a captura para debitar da presa no fecho do passo."""
        prey_level = max(TROPHIC_PRODUCER, predator_level - 1)
        self._predation_by_level[prey_level] = (
            self._predation_by_level.get(prey_level, 0.0) + captured
        )

    # --- Ciclo -----------------------------------------------------------------
    def step(self) -> None:
        # Distribui a predação do passo anterior proporcionalmente entre as presas.
        for level, captured in self._predation_by_level.items():
            prey = [a for a in self.populations() if a.trophic_level == level]
            total = sum(a.population for a in prey)
            for agent in prey:
                share = (agent.population / total) if total > 0.0 else 0.0
                agent.consumed = captured * share
        self._predation_by_level.clear()

        # `shuffle_do` embaralha com o RNG semeado do modelo: a ordem varia, mas
        # de forma reprodutível para a mesma semente.
        self.agents.shuffle_do("step")

        for agent in self.populations():
            agent.consumed = 0.0
        self.history.append({a.species_id: a.population for a in self.populations()})

    def run(self) -> EcologyOutcome:
        steps = min(self.params.steps, self.params.max_steps)
        for _ in range(steps):
            self.step()
        return EcologyOutcome(
            populations=[
                PopulationSnapshot(
                    species_id=a.species_id,
                    population=a.population,
                    trophic_level=a.trophic_level,
                )
                for a in self.populations()
            ],
            history=self.history,
        )


def simulate_ecology(
    species: list[SpeciesRecord],
    capacity: float,
    params: EcologyParams,
    seed: int,
) -> EcologyOutcome:
    """Fachada: roda uma era de ecologia e devolve o snapshot populacional."""
    if not species:
        return EcologyOutcome(populations=[], history=[])
    return EcologyModel(species, capacity, params, seed).run()
