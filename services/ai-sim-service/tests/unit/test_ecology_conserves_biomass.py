"""GUARDA DO VAZAMENTO: a predação não pode criar biomassa.

Este arquivo existe porque a suíte anterior **não tinha como detectar** o defeito
que ele protege. `test_carbon_is_not_double_counted` fecha a identidade contábil
do carbono — e fecharia igualmente bem sobre um número errado, porque ela verifica
a coerência entre os livros, não a origem do valor. Uma biomassa inflada entra na
conta e sai da conta; a identidade não se abala.

O defeito medido na versão anterior do `ecology.py` era de **7,76% de biomassa
fantasma por era**, vindo de três lugares: a captura debitada da presa só no passo
seguinte (a predação do último passo nunca era paga), a ausência de teto global
por nível trófico (vários predadores somados capturavam mais presa do que existia)
e a dependência da ordem de iteração.

A partir do M3 a saída da ecologia alimenta `biota.biomass`, que alimenta o
sumidouro biótico de carbono. Sem este teste, alguém pode regredir a atualização
síncrona no futuro e TODOS os testes de carbono continuariam verdes — de novo.

## A propriedade

A predação **move** biomassa com perda: a presa perde `captura`, o predador ganha
`conversão × captura`, e `conversão < 1`. O restante é energia dissipada no
metabolismo. Logo, **sem produção primária, o total só pode cair**.

É uma desigualdade, não uma igualdade — e é essa a forma certa: exigir soma
constante seria exigir que a segunda lei da termodinâmica não valesse.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.simulation_engine.biology.codex import SpeciesRecord
from ecosfera_ai.simulation_engine.biology.ecology import EcologyParams, simulate_ecology
from ecosfera_ai.simulation_engine.biology.genome import (
    TROPHIC_HERBIVORE,
    TROPHIC_PREDATOR,
    TROPHIC_PRODUCER,
    Genome,
)
from ecosfera_ai.simulation_engine.params import load_params

PARAMS: EcologyParams = load_params(Path("configs/simulation_params.yaml")).ecology

# Tolerância declarada: só ruído de ponto flutuante cabe aqui. O vazamento que
# este teste existe para pegar era de 7,76% — quatro ordens de grandeza acima.
TOLERANCE = 1e-9


def _genome(trophic: float, metabolism: float = 1.0) -> Genome:
    return Genome(
        temp_optimum=20.0,
        temp_tolerance=15.0,
        water_need=0.2,
        size=1.0,
        metabolism=metabolism,
        trophic_level=trophic,
    )


def _species(species_id: str, trophic: float, population: float) -> SpeciesRecord:
    return SpeciesRecord(
        species_id=species_id,
        planet_id="p",
        genome=_genome(trophic),
        emerged_era=0,
        extinct_era=None,
        ancestor_id=None,
        population=population,
        fitness=0.5,
    )


def _food_chain() -> list[SpeciesRecord]:
    """Produtor → herbívoro → predador, para exercitar a cadeia inteira."""
    return [
        _species("prod", TROPHIC_PRODUCER, 100.0),
        _species("herb", TROPHIC_HERBIVORE, 30.0),
        _species("pred", TROPHIC_PREDATOR, 10.0),
    ]


def _no_primary_production() -> EcologyParams:
    """Fecha a única ENTRADA de biomassa do sistema.

    Sem crescimento de produtor e sem ruído demográfico, nada pode acrescentar
    biomassa. Qualquer aumento no total é, por definição, matéria criada do nada.
    """
    return replace(PARAMS, growth_rate=0.0, demographic_noise=0.0, min_viable_population=0.0)


def test_ecology_conserves_biomass() -> None:
    """Sem produção primária, o total de biomassa NUNCA cresce.

    É o teste que, na versão antiga, acusaria os 7,76% por era.
    """
    params = _no_primary_production()
    start = sum(record.population for record in _food_chain())
    outcome = simulate_ecology(_food_chain(), capacity=0.0, params=params, seed=7)

    assert outcome.total_biomass() <= start + TOLERANCE, (
        f"a ecologia criou biomassa do nada: {start:.6f} -> "
        f"{outcome.total_biomass():.6f} (+{outcome.total_biomass() - start:.6f})"
    )


def test_no_step_of_the_history_creates_biomass() -> None:
    """A conservação vale PASSO A PASSO, não só no total da era.

    Verificar apenas as pontas deixaria passar um vazamento compensado por uma
    perda em outro passo — e o defeito antigo era exatamente localizado no ÚLTIMO
    passo, que uma comparação ponta-a-ponta poderia diluir.
    """
    params = _no_primary_production()
    start = sum(record.population for record in _food_chain())
    outcome = simulate_ecology(_food_chain(), capacity=0.0, params=params, seed=11)

    previous = start
    for index, step in enumerate(outcome.history):
        total = sum(step.values())
        assert total <= previous + TOLERANCE, (
            f"o passo {index} criou biomassa: {previous:.6f} -> {total:.6f}"
        )
        previous = total


def test_predation_actually_happens_so_the_test_is_not_vacuous() -> None:
    """Uma cadeia parada conservaria trivialmente — o teste precisa de predação."""
    params = _no_primary_production()
    outcome = simulate_ecology(_food_chain(), capacity=0.0, params=params, seed=7)

    assert outcome.population_of("prod") < 100.0, "o produtor não foi predado"
    assert outcome.total_biomass() > 0.0, "colapso total tornaria a asserção vazia"


def test_predators_never_eat_more_prey_than_exists() -> None:
    """Teto global por nível: muitos predadores famintos não inventam presa.

    Com vários predadores sobre uma presa escassa, a versão anterior permitia que
    a soma das capturas excedesse o estoque — e o excedente virava biomassa nova.
    """
    params = replace(
        _no_primary_production(),
        predation_rate=5.0,  # fome absurda: a demanda excede o estoque com folga
        conversion_efficiency=1.0,  # pior caso: nada se dissipa na conversão
        mortality_rate=0.0,
    )
    crowd = [
        _species("prod", TROPHIC_PRODUCER, 1.0),
        *(_species(f"herb{i}", TROPHIC_HERBIVORE, 20.0) for i in range(5)),
    ]
    start = sum(record.population for record in crowd)
    outcome = simulate_ecology(crowd, capacity=0.0, params=params, seed=3)

    assert outcome.population_of("prod") >= -TOLERANCE, "a presa ficou negativa"
    assert outcome.total_biomass() <= start + TOLERANCE, (
        "a soma das capturas excedeu a presa disponível e virou biomassa nova"
    )


def test_the_result_does_not_depend_on_iteration_order() -> None:
    """Ordem de iteração não é ciência: a mesma semente dá o mesmo resultado.

    A versão anterior usava `shuffle_do`, então cada agente via o estado
    semi-atualizado dos anteriores. Aqui a ordem de ENTRADA das espécies também
    não pode alterar o resultado — todos leem a mesma fotografia.
    """
    params = _no_primary_production()
    forward = simulate_ecology(_food_chain(), capacity=0.0, params=params, seed=5)
    reversed_input = simulate_ecology(
        list(reversed(_food_chain())), capacity=0.0, params=params, seed=5
    )

    for species_id in ("prod", "herb", "pred"):
        assert forward.population_of(species_id) == pytest.approx(
            reversed_input.population_of(species_id), rel=1e-12
        ), f"{species_id} depende da ordem em que as espécies foram passadas"


def test_the_same_seed_reproduces_the_era() -> None:
    """RF-023 continua valendo com a atualização síncrona."""
    first = simulate_ecology(_food_chain(), capacity=50.0, params=PARAMS, seed=99)
    second = simulate_ecology(_food_chain(), capacity=50.0, params=PARAMS, seed=99)
    assert [s.population for s in first.populations] == [s.population for s in second.populations]
