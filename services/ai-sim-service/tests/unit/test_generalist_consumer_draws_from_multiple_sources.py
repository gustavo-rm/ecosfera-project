"""ECO-001: um consumidor generalista come de MAIS DE UMA fonte trófica.

A lacuna que a Tássia apontou como a maior (Div. 3): a cadeia linear estrita faz
o predador comer só o nível imediatamente abaixo. Aqui o predador ganha uma
DIETA e, como generalista (onívoro), drena o produtor além do herbívoro. Estes
testes exigem que o segundo caminho seja REAL — que o predador de fato tire
biomassa do produtor —, não apenas declarado no parâmetro.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.ecology.contracts import load_params as ecology_params
from ecosfera_ai.engines.ecology.service import _trophic_step
from ecosfera_ai.shared_kernel.engine import TickContext
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

# Sem ruído demográfico: o que se afirma é a fonte da biomassa, não estatística
# de sorteio. `full_era = 0` liga a onivoria plena já na era 0 do próprio passo.
ECOLOGY = replace(ecology_params(), demographic_noise=0.0)
GENERALIST = replace(
    ECOLOGY,
    generalist_unlock_era=0,
    generalist_full_era=0,
    predator_diet_herbivore=0.70,
    predator_diet_producer=0.30,
)
PARAMS = load_params(Path("configs/simulation_params.yaml"))
CAPACITY = 200.0


def _ctx(era: int, *, tick: int = 5, seed: int = 2027) -> TickContext:
    snapshot = snapshot_of(initial_state(PlanetSeed("eco001", seed), PARAMS))
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "ecology", tick),
        tick=tick,
        era=era,
        budget=PARAMS.engine_budget,
    )


def test_a_predator_without_herbivores_still_feeds_as_a_generalist() -> None:
    """Sem herbívoro, o predador de cadeia estrita passa fome; o onívoro come planta.

    É a prova mais direta de "usa a segunda fonte": zerado o único elo da cadeia,
    só resta o produtor. Se o predador CRESCE, foi dele que comeu.
    """
    levels = (100.0, 0.0, 10.0)
    strict = _trophic_step(levels, CAPACITY, ECOLOGY, _ctx(era=0))
    generalist = _trophic_step(levels, CAPACITY, GENERALIST, _ctx(era=0))

    assert strict[2] < 10.0, "sem presa da cadeia, o predador estrito só pode declinar"
    assert generalist[2] > strict[2], "o generalista não aproveitou o produtor como fonte"
    assert generalist[0] < strict[0], "o produtor não perdeu biomassa para a onivoria"


def test_the_generalist_supplements_scarce_chain_prey_with_the_off_chain_source() -> None:
    """Com herbívoro escasso e produtor farto, o onívoro se sai melhor que o estrito.

    O generalista soma as duas fontes; o estrito depende só da presa escassa. A
    diferença é a captura fora-da-cadeia entrando na conta do predador.
    """
    levels = (120.0, 4.0, 10.0)
    strict = _trophic_step(levels, CAPACITY, ECOLOGY, _ctx(era=0))
    generalist = _trophic_step(levels, CAPACITY, GENERALIST, _ctx(era=0))

    assert generalist[2] > strict[2], "a dieta ampla não elevou o ganho do predador"
    assert generalist[0] < strict[0], "o produtor não sentiu a onivoria"


def test_both_prey_pools_lose_biomass_to_a_generalist_predator() -> None:
    """Com as duas presas presentes, o predador drena os DOIS poços no mesmo passo.

    A biomassa LÍQUIDA de um poço pode até crescer (a pastagem repõe o herbívoro);
    o que se afirma aqui é o FLUXO de captura. Isolamos cada fluxo contra o mesmo
    mundo SEM predador: se a presença do predador reduz o herbívoro E reduz o
    produtor além do que a pastagem já tira, ele comeu dos dois.
    """
    with_predator = _trophic_step((120.0, 30.0, 12.0), CAPACITY, GENERALIST, _ctx(era=0))
    no_predator = _trophic_step((120.0, 30.0, 0.0), CAPACITY, GENERALIST, _ctx(era=0))

    assert with_predator[1] < no_predator[1], "o predador não caçou o herbívoro (poço da cadeia)"
    assert with_predator[0] < no_predator[0], "o predador não drenou o produtor (poço da onivoria)"
