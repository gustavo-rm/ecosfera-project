"""AUDITORIA ESTRUTURAL: a evolução do Engine não tem função de aptidão global.

A regra de ouro do M3 (ADR-ARCH-0001, ADR 0016) não é uma preferência de estilo —
é a diferença entre ensinar que a evolução RASTREIA o ambiente e ensinar que ela
MIRA um ótimo. A segunda é a concepção equivocada que a plataforma existe para
desfazer.

Uma regra só é regra se algo a barra. O contrato de import-linter barra o `deap`;
este arquivo barra o resto: o vocabulário e a FORMA do cálculo.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest

from ecosfera_ai.engines.evolution import domain, service
from ecosfera_ai.engines.evolution.contracts import load_params
from ecosfera_ai.engines.evolution.domain import LocalConditions, local_suitability
from ecosfera_ai.simulation_engine.biology.genome import Genome

PARAMS = load_params()
_PACKAGE = Path(service.__file__).parent

# Vocabulário de otimização populacional. Não é caça às palavras: cada um destes
# nomeia um mecanismo que só existe quando há um número global a maximizar.
FORBIDDEN_NAMES = (
    "selTournament",
    "tournament",
    "toolbox",
    "creator",
    "cxBlend",
    "mutGaussian",
    "hall_of_fame",
    "halloffame",
    "population_size",
    "generations",
)


def _sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(_PACKAGE.glob("*.py"))}


def test_the_evolution_package_imports_no_optimisation_framework() -> None:
    """Complementa o contrato de import-linter no nível do AST."""
    for path, source in _sources().items():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            assert "deap" not in names, f"{path.name} importa deap"
            assert "mesa" not in names, f"{path.name} importa mesa"


def test_no_optimisation_vocabulary_survives_in_the_engine() -> None:
    """Nem os identificadores do maquinário de otimização."""
    for path, source in _sources().items():
        lowered = source.lower()
        for name in FORBIDDEN_NAMES:
            assert name.lower() not in lowered, (
                f"{path.name} menciona {name!r}: o maquinário de otimização "
                "populacional voltou pela porta dos fundos"
            )


def test_there_is_no_function_named_fitness() -> None:
    """`local_suitability` não é `fitness` com outro nome — e o nome importa.

    Chamá-la de fitness convidaria o próximo leitor a maximizá-la.
    """
    for path, source in _sources().items():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert "fitness" not in node.name.lower(), f"{path.name}: {node.name}"


# --- A forma do cálculo, não só o vocabulário ---------------------------------


def _genome(**overrides: float) -> Genome:
    base = {
        "temp_optimum": 20.0,
        "temp_tolerance": 15.0,
        "water_need": 0.2,
        "size": 1.0,
        "metabolism": 1.0,
        "trophic_level": 1.0,
    }
    return Genome(**{**base, **overrides}).clamped()


def _conditions(**overrides: float) -> LocalConditions:
    base = {
        "temperature": 20.0,
        "water_available": 0.5,
        "energy_available": 0.05,
        "carrying_capacity": 100.0,
        "occupied": 20.0,
        "predation_pressure": 0.0,
    }
    return LocalConditions(**{**base, **overrides})  # type: ignore[arg-type]


def test_suitability_depends_only_on_the_cohort_and_its_environment() -> None:
    """A assinatura é a prova estrutural: não há por onde entrar uma população.

    Uma função de aptidão global precisa das CONCORRENTES para normalizar ou
    ranquear. Esta não tem como recebê-las — e é isso que a torna local.
    """
    signature = inspect.signature(local_suitability)
    assert list(signature.parameters) == ["genome", "conditions", "params"]

    fields = set(LocalConditions.__dataclass_fields__)
    assert "population" not in fields
    assert not any("species" in name or "others" in name for name in fields), (
        "a condição local passou a enxergar as concorrentes"
    )


def test_two_cohorts_do_not_compete_for_a_ranking_slot() -> None:
    """Ambas podem prosperar; ambas podem perecer. Não há soma constante.

    Num AG com fitness global, a seleção é relativa: melhorar uma piora as outras
    porque disputam os mesmos postos. Aqui não há postos.
    """
    hot = _genome(temp_optimum=30.0)
    cold = _genome(temp_optimum=10.0)

    both_thrive = _conditions(temperature=20.0, occupied=0.0)
    assert local_suitability(hot, both_thrive, PARAMS) > 0.3
    assert local_suitability(cold, both_thrive, PARAMS) > 0.3

    both_suffer = _conditions(temperature=75.0, occupied=0.0)
    assert local_suitability(hot, both_suffer, PARAMS) < 0.05
    assert local_suitability(cold, both_suffer, PARAMS) < 0.05


def test_a_cohort_score_does_not_move_when_another_cohort_changes() -> None:
    """Independência: a adequação de uma coorte ignora a existência da outra."""
    resident = _genome(temp_optimum=20.0)
    conditions = _conditions()
    alone = local_suitability(resident, conditions, PARAMS)

    # Uma segunda coorte, muito melhor adaptada, é avaliada no mesmo ambiente.
    newcomer = _genome(temp_optimum=20.0, metabolism=0.1, size=0.1)
    assert local_suitability(newcomer, conditions, PARAMS) >= alone
    # E a primeira NÃO se move por causa disso.
    assert local_suitability(resident, conditions, PARAMS) == alone


def test_the_environment_is_what_moves_the_score() -> None:
    """O que muda a adequação é o ambiente — a contraprova do teste anterior."""
    cohort = _genome(temp_optimum=20.0)
    warm = local_suitability(cohort, _conditions(temperature=20.0), PARAMS)
    hot = local_suitability(cohort, _conditions(temperature=45.0), PARAMS)
    assert hot < warm, "a temperatura deixou de importar"


def test_mutation_is_undirected() -> None:
    """O desvio não sabe se melhora ou piora: ~metade das vezes piora.

    Numa busca guiada por objetivo, a mutação seria aceita só quando melhora (ou
    com probabilidade dependente da melhora). Aqui ela é cega, e o ambiente decide
    DEPOIS.

    A coorte é posta FORA do ótimo de propósito. Exatamente no pico, toda
    perturbação desce — 100% de pioras seria o resultado correto de uma mutação
    cega, e o teste não distinguiria nada. É no flanco da gaussiana que "cego"
    e "direcionado" divergem: metade dos desvios aproxima do ótimo local, metade
    afasta.
    """
    cohort = _genome(temp_optimum=30.0)
    conditions = _conditions(temperature=20.0)
    baseline = local_suitability(cohort, conditions, PARAMS)

    rng = np.random.default_rng(20260801)
    worse = sum(
        1
        for _ in range(400)
        if local_suitability(domain.mutate(cohort, rng, PARAMS), conditions, PARAMS) < baseline
    )
    assert 120 < worse < 280, (
        f"{worse}/400 mutações pioraram — uma mutação cega fica perto da metade; "
        "muito longe disso indica desvio DIRECIONADO"
    )


def test_suitability_is_a_product_so_one_null_factor_is_fatal() -> None:
    """Lei do mínimo: nenhum excesso compensa a ausência de um recurso.

    Uma soma ponderada — a forma usual de uma função de aptidão — permitiria
    compensar. É a diferença entre "quão bom é este genoma" e "esta coorte
    consegue se sustentar aqui".
    """
    cohort = _genome(water_need=0.2)
    dry = _conditions(water_available=0.0)
    assert local_suitability(cohort, dry, PARAMS) == pytest.approx(0.0)

    # E nem uma temperatura perfeita com energia de sobra o resgata.
    perfect_but_dry = _conditions(
        temperature=cohort.temp_optimum, energy_available=10.0, water_available=0.0
    )
    assert local_suitability(cohort, perfect_but_dry, PARAMS) == pytest.approx(0.0)
