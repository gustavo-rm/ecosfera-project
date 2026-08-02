"""Modelo ecológico com Mesa: dinâmica trófica EMERGENTE (TASK-0050/0051, RF-032).

Cada agente é uma **população de espécie** (não um indivíduo): a agregação é o que
torna o custo tratável — o teto de agentes é o número de espécies vivas, não o de
organismos (mitigação do RSK de custo computacional do Inc 3).

As oscilações predador-presa **emergem** das regras locais de cada agente; não há
equação de Lotka-Volterra escrita em lugar nenhum. Cada população só sabe:

  - produtores crescem logisticamente até a capacidade de suporte que a camada
    determinística oferece;
  - consumidores crescem proporcionalmente ao que conseguem predar no nível
    trófico abaixo, e morrem por manutenção;
  - toda predação retira biomassa da presa.

Da soma dessas regras nascem os ciclos clássicos — que é exatamente o fenômeno
que o aluno deve observar e explicar.

## Atualização SÍNCRONA em duas fases (corrigido no M3)

O passo é calculado em duas fases: primeiro todos leem a MESMA fotografia das
populações e declaram suas variações; só depois as variações são aplicadas. Três
defeitos medidos na versão anterior desaparecem com isso:

1. **Predação "grátis" no último passo.** A captura era debitada da presa no
   INÍCIO do passo seguinte, então a predação do último passo da era nunca era
   paga — o predador crescia com biomassa que a presa nunca perdeu. Medido:
   **7,76% de biomassa fantasma por era**.
2. **Sobrepredação.** Cada predador limitava a própria captura ao estoque de
   presa, mas vários predadores somados podiam capturar mais do que existia. Há
   agora um **teto global por nível trófico**: se a demanda excede o estoque, as
   capturas são rateadas proporcionalmente.
3. **Dependência da ordem de iteração.** `shuffle_do` fazia cada agente ver o
   estado semi-atualizado dos anteriores. Lendo todos da mesma fotografia, a
   ordem deixa de importar — o resultado é função da semente, não do sorteio.

Por que isso deixou de ser tolerável: enquanto a ecologia era um beco sem saída
(o resultado ia para o códex e não realimentava a física), o vazamento era uma
imprecisão contida. No M3 a saída passa a alimentar `biota.biomass`, que alimenta
o sumidouro biótico de carbono — e o vazamento entraria no ciclo do carbono
fechado no M2, com a identidade contábil fechando sobre o número errado.

**Conservação.** A predação não cria biomassa: a presa perde `captura`, o
predador ganha `conversão × captura`, com `conversão < 1`. Sem produção primária,
o total só pode CAIR. É o que `test_ecology_conserves_biomass` verifica.

Reprodutibilidade (RF-023): o modelo é semeado por `seed=`, derivado da semente
do planeta e da era. O modelo NÃO escreve no `PlanetState` (ADR 0006).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.genome import TROPHIC_PRODUCER

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

    def total_biomass(self) -> float:
        """Soma das populações vivas — a grandeza cuja conservação se verifica."""
        return sum(snapshot.population for snapshot in self.populations)


@lru_cache(maxsize=1)
def _mesa_classes() -> tuple[type, type]:
    """Constrói as classes Mesa SOB DEMANDA (ADR 0017).

    `PopulationAgent` e `EcologyModel` herdam de `mesa.*`, então defini-las no
    topo do módulo obrigaria quem apenas IMPORTA este arquivo a ter o extra `sim`
    instalado. A cadeia chegava até `create_app()`: registrar um handler de 404
    exigia um framework de simulação por agente.

    Herança exige que a base exista no momento da definição, então a única forma
    de adiar o import é adiar a própria definição. A fábrica é cacheada para que
    as classes sejam criadas UMA vez — identidade estável, da qual `isinstance` e
    o próprio Mesa dependem.
    """
    import mesa

    class PopulationAgent(mesa.Agent):  # type: ignore[misc]
        """Agente = população de uma espécie. Sabe apenas comer, crescer e morrer."""

        def __init__(
            self,
            model: Any,
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

        def planned_change(
            self, observed: dict[int, float], captured: float, eaten: float
        ) -> float:
            """Variação declarada a partir da FOTOGRAFIA, sem tocar em ninguém.

            `observed` é a biomassa por nível trófico no início do passo — a mesma
            para todos, que é o que remove a dependência de ordem.
            """
            params = self.model.params
            if self.trophic_level <= TROPHIC_PRODUCER:
                capacity = self.model.producer_capacity
                if capacity <= 0.0:
                    growth = -params.mortality_rate * self.population
                else:
                    occupied = observed.get(TROPHIC_PRODUCER, 0.0)
                    growth = (
                        params.growth_rate
                        * self.population
                        * (1.0 - occupied / max(capacity, _EPS))
                    )
            else:
                growth = params.conversion_efficiency * captured
                growth -= params.mortality_rate * self.metabolism * self.population
            return float(growth) - eaten

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
            self.history: list[dict[str, float]] = []

            # Contenção de custo: só as espécies mais populosas entram no modelo.
            # O desempate por `species_id` torna o corte determinístico quando
            # duas espécies têm a mesma população.
            ranked = sorted(species, key=lambda r: (-r.population, r.species_id))
            for record in ranked[: params.max_agents]:
                PopulationAgent(
                    model=self,
                    species_id=record.species_id,
                    trophic_level=record.genome.trophic_class,
                    population=record.population,
                    metabolism=record.genome.metabolism,
                )

        def populations(self) -> list[Any]:
            """Agentes em ordem ESTÁVEL — o resultado não depende do sorteio."""
            agents: list[Any] = sorted(self.agents, key=lambda a: a.species_id)
            return agents

        def _observed(self) -> dict[int, float]:
            """Biomassa por nível trófico no início do passo (a fotografia)."""
            observed: dict[int, float] = {}
            for agent in self.populations():
                observed[agent.trophic_level] = (
                    observed.get(agent.trophic_level, 0.0) + agent.population
                )
            return observed

        def _captures(
            self, observed: dict[int, float]
        ) -> tuple[dict[str, float], dict[str, float]]:
            """Capturas por predador e perdas por presa, com TETO GLOBAL por nível.

            Cada predador declara a captura desejada; se a soma dos desejos sobre
            um nível excede o estoque, todos são rateados na mesma proporção. Sem
            esse teto, dois predadores famintos comeriam, somados, mais presa do
            que existe — e a diferença viraria biomassa do nada.
            """
            params = self.params
            desired: dict[str, float] = {}
            demand_by_prey: dict[int, float] = {}
            for agent in self.populations():
                if agent.trophic_level <= TROPHIC_PRODUCER:
                    continue
                prey_level = max(TROPHIC_PRODUCER, agent.trophic_level - 1)
                available = observed.get(prey_level, 0.0)
                want = params.predation_rate * agent.population * available
                desired[agent.species_id] = want
                demand_by_prey[prey_level] = demand_by_prey.get(prey_level, 0.0) + want

            scale: dict[int, float] = {}
            for prey_level, demand in demand_by_prey.items():
                available = observed.get(prey_level, 0.0)
                scale[prey_level] = min(1.0, available / demand) if demand > _EPS else 0.0

            captured: dict[str, float] = {}
            taken_by_level: dict[int, float] = {}
            for agent in self.populations():
                if agent.trophic_level <= TROPHIC_PRODUCER:
                    continue
                prey_level = max(TROPHIC_PRODUCER, agent.trophic_level - 1)
                amount = desired[agent.species_id] * scale.get(prey_level, 0.0)
                captured[agent.species_id] = amount
                taken_by_level[prey_level] = taken_by_level.get(prey_level, 0.0) + amount

            # Rateia a perda entre as presas do nível, proporcional à população.
            eaten: dict[str, float] = {}
            for agent in self.populations():
                total_level = observed.get(agent.trophic_level, 0.0)
                taken = taken_by_level.get(agent.trophic_level, 0.0)
                share = (agent.population / total_level) if total_level > _EPS else 0.0
                eaten[agent.species_id] = taken * share
            return captured, eaten

        def step(self) -> None:
            """Um passo SÍNCRONO: todos leem a mesma fotografia, depois aplicam."""
            observed = self._observed()
            captured, eaten = self._captures(observed)

            planned = {
                agent.species_id: agent.planned_change(
                    observed,
                    captured.get(agent.species_id, 0.0),
                    eaten.get(agent.species_id, 0.0),
                )
                for agent in self.populations()
            }

            params = self.params
            for agent in self.populations():
                agent.population += planned[agent.species_id]
                if params.demographic_noise > 0.0:
                    agent.population += (
                        self.random.gauss(0.0, params.demographic_noise) * agent.population
                    )
                if agent.population < params.min_viable_population:
                    agent.population = 0.0
                agent.population = max(0.0, agent.population)

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

    return PopulationAgent, EcologyModel


def simulate_ecology(
    species: list[SpeciesRecord],
    capacity: float,
    params: EcologyParams,
    seed: int,
) -> EcologyOutcome:
    """Fachada: roda uma era de ecologia e devolve o snapshot populacional."""
    if not species:
        return EcologyOutcome(populations=[], history=[])
    _, model_cls = _mesa_classes()
    outcome: EcologyOutcome = model_cls(species, capacity, params, seed).run()
    return outcome
