"""Seleção natural EMERGENTE: sobrevivência e reprodução por condição local.

## O que este módulo NÃO faz

Não existe função de aptidão global, nem número maximizado, nem torneio, nem
população otimizada geração a geração. Isso é deliberado e é a decisão central do
M3 (ADR-ARCH-0001, decisão adicional; ADR 0016).

A cadeia da decisão, para que ninguém a desfaça por engano:

    RF-031 (AG com fitness global)
      → ADR-ARCH-0001 supera o fitness global (é teleológico: ensina que a
        evolução "mira" um ótimo, que é exatamente a concepção equivocada que a
        plataforma existe para desfazer)
      → M3 conclui que, sem fitness global, o **DEAP não tem papel**: o que ele
        oferece é maquinário de otimização populacional, e otimização populacional
        é justamente o que foi proibido. Sobram ~50 linhas puras.

## O que este módulo faz

Cada coorte encontra as condições do SEU tick e responde a elas:

    excedente = adequação_local − custo_de_manutenção − pressão_de_predação
    Δpopulação = população × excedente

`adequação_local` é o produto dos fatores limitantes que a coorte de fato
enfrenta (temperatura vs. sua tolerância, água vs. sua necessidade, energia vs.
seu nível trófico, lotação vs. a capacidade publicada). É produto, e não soma,
pela lei do mínimo: um fator nulo inviabiliza a coorte por mais favoráveis que
sejam os outros.

A diferença entre isto e uma função de fitness não é cosmética. Aqui o número
não é comparado entre espécies nem usado para ordená-las: **cada coorte é
avaliada contra o ambiente, não contra as concorrentes.** Duas espécies podem
prosperar ao mesmo tempo, ou perecer ao mesmo tempo; não há competição por um
posto no ranking. A "aptidão" é o RESULTADO de sobreviver, não um alvo.

## Mutação e especiação

A reprodução copia o genoma com desvio gaussiano por traço (RNG semeado pelo
Planet). Quando a linhagem se distancia da ancestral além do limiar de
divergência, é **especiação** — uma espécie nova no códex, não um ponto melhor
no espaço de busca.

Puro: sem DEAP, sem Mesa, sem I/O. Testável sem framework algum.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ecosfera_ai.engines.evolution.contracts import EvolutionEngineParams
from ecosfera_ai.simulation_engine.biology.genome import TROPHIC_PRODUCER, Genome

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class LocalConditions:
    """O ambiente que UMA coorte encontra neste tick.

    É o único insumo da seleção. Note o que NÃO está aqui: nenhuma referência às
    outras espécies individualmente, nenhum ranking, nenhuma média da população.
    A lotação entra como grandeza AMBIENTAL (quanto do orçamento já está gasto),
    não como comparação com concorrentes.
    """

    temperature: float
    water_available: float
    energy_available: float
    carrying_capacity: float
    occupied: float  # biomassa total já instalada
    predation_pressure: float  # vinda da Ecology, leitura defasada

    @property
    def occupancy(self) -> float:
        """Fração do orçamento ambiental já ocupada.

        Sem orçamento algum a fração não é 1 — é INFINITA: qualquer biomassa
        instalada excede um teto de zero. Devolver 1,0 tratava um planeta
        inabitável como um planeta apenas cheio, e a diferença não era acadêmica:
        com `crowding(1) ≈ 0,45` contra um custo de manutenção de 0,45, a
        comunidade CRESCIA num mundo de capacidade zero.

        Com infinito, `crowding` vai a zero e a lei do mínimo faz o resto — o
        orçamento ambiental é mais um fator limitante, e um fator nulo é fatal.
        """
        if self.carrying_capacity <= _EPS:
            return math.inf
        return max(0.0, self.occupied) / self.carrying_capacity


def thermal_match(genome: Genome, temperature: float) -> float:
    """Quão bem ESTA coorte tolera a temperatura de agora — gaussiana no ótimo.

    A tolerância é traço do genoma: especialistas (janela estreita) despencam com
    pequenas variações, generalistas resistem. É o mecanismo pelo qual o
    aquecimento causa extinção, e o que dá sentido a `THERMAL_INTOLERANCE`.
    """
    offset = (temperature - genome.temp_optimum) / max(genome.temp_tolerance, _EPS)
    return math.exp(-(offset**2))


def water_match(genome: Genome, water_available: float) -> float:
    """Satura quando há água suficiente para a necessidade DESTA coorte."""
    if genome.water_need <= 0.0:
        return 1.0
    return min(1.0, max(0.0, water_available) / genome.water_need)


def energy_match(genome: Genome, energy_available: float, params: EvolutionEngineParams) -> float:
    """Só o produtor depende da irradiância; o consumidor come da cadeia trófica."""
    if genome.trophic_class > TROPHIC_PRODUCER:
        return 1.0
    if params.energy_reference <= 0.0:
        return 1.0
    return min(1.0, max(0.0, energy_available) / params.energy_reference)


def crowding(occupancy: float, params: EvolutionEngineParams) -> float:
    """Lotação: o orçamento cheio aperta a todos, sem eleger vencedor."""
    return 1.0 / (1.0 + params.crowding_weight * max(0.0, occupancy))


def local_suitability(
    genome: Genome, conditions: LocalConditions, params: EvolutionEngineParams
) -> float:
    """Adequação [0,1] desta coorte ao ambiente que ela encontra.

    Produto dos fatores limitantes (lei do mínimo, em versão suave). **Não é uma
    função de fitness**: não é comparada entre espécies nem maximizada. É a
    probabilidade local de a coorte se sustentar.
    """
    return (
        thermal_match(genome, conditions.temperature)
        * water_match(genome, conditions.water_available)
        * energy_match(genome, conditions.energy_available, params)
        * crowding(conditions.occupancy, params)
    )


def maintenance_cost(genome: Genome, params: EvolutionEngineParams) -> float:
    """O que a coorte gasta só para existir: corpo grande e metabolismo alto."""
    return params.metabolism_cost * genome.metabolism + params.size_cost * genome.size


def population_change(
    genome: Genome,
    population: float,
    conditions: LocalConditions,
    params: EvolutionEngineParams,
) -> float:
    """Variação da coorte: o excedente local aplicado à população existente.

    Excedente positivo → reprodução; negativo → morte. Nada aqui otimiza: a
    coorte apenas responde ao que encontra.
    """
    surplus = (
        local_suitability(genome, conditions, params)
        - maintenance_cost(genome, params)
        - params.predation_weight * max(0.0, conditions.predation_pressure)
    )
    return params.growth_rate * population * surplus


def mutate(genome: Genome, rng: np.random.Generator, params: EvolutionEngineParams) -> Genome:
    """Copia o genoma com desvio gaussiano por traço, recortando às faixas.

    A mutação é **não-direcionada**: o desvio não sabe se melhora ou piora a
    adequação. É o ambiente, depois, que decide quem se sustenta — que é a ordem
    correta e o oposto de uma busca guiada por objetivo.
    """
    traits = {
        name: float(getattr(genome, name)) + float(rng.normal(0.0, params.mutation_sigma * span))
        for name, span in _trait_spans().items()
    }
    return Genome(**traits).clamped()


def _trait_spans() -> dict[str, float]:
    """Amplitude de cada traço — a mutação é relativa à faixa, não absoluta.

    Sem isso, um mesmo sigma moveria `metabolism` (faixa 0,05–3) e `temp_optimum`
    (faixa −40–80) em escalas incomparáveis.
    """
    return {name: (high - low) for name, (low, high) in Genome.BOUNDS.items()}


def has_speciated(descendant: Genome, ancestor: Genome, params: EvolutionEngineParams) -> bool:
    """Divergiu o bastante da ancestral para ser outra espécie."""
    return descendant.distance(ancestor) >= params.speciation_threshold


def is_extinct(population: float, params: EvolutionEngineParams) -> bool:
    """Abaixo do mínimo viável, a coorte não se sustenta."""
    return population <= params.extinction_population
