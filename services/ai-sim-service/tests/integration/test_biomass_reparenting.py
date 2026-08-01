"""GUARDA DO REPARENTING DA BIOMASSA (ADR 0016).

`biota.biomass` trocou de dono no M3: era escrita pelo Biota provisório do M2,
passou a ser escrita pelo Evolution Engine. Ela tem **dois leitores dentro do
ciclo do carbono**:

  - `atmosphere/service.py` — o sumidouro biótico (`carbon_uptake_coeff × biomassa`)
  - `resource/service.py`   — o consumo de recurso pela vida instalada

Remover o Biota sem dar novo dono à biomassa não seria "uma fatia fica vazia":
seria abrir um buraco no ciclo do carbono fechado no M2, no modo silencioso do
`solar_flux` — o sumidouro biótico iria a zero sem erro algum, o CO₂ passaria a
subir sem a absorção da vida, e `test_carbon_is_not_double_counted` continuaria
VERDE, porque a identidade contábil fecha igualmente bem com `absorbed = 0`.

Este arquivo é o análogo do `test_solar_flux_has_writer.py` do M2, e cobre as
duas travas: **quem escreve** e **com que defasagem se lê**.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from ecosfera_ai.engines.atmosphere.contracts import load_params as atmosphere_params
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
from ecosfera_ai.engines.evolution.contracts import ENGINE_ID as EVOLUTION_ID
from ecosfera_ai.shared_kernel.world_state import SliceRef, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
ATMOSPHERE = atmosphere_params()
TICKS = 200


def _trail(seed: int = 2027, ticks: int = TICKS) -> list[WorldStateSnapshot]:
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("reparent", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return trail


# --- Trava 1: a biomassa tem escritor -----------------------------------------


def test_biomass_has_writer_after_biota_removal() -> None:
    """A `BiotaSlice` mudou de dono, mas não ficou órfã."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert planet.registry.owned_slices[SliceRef.BIOTA] == EVOLUTION_ID
    assert "biota" not in ENGINE_ORDER, "o Biota provisório do M2 deveria ter saído"
    assert "evolution" in ENGINE_ORDER and "ecology" in ENGINE_ORDER


def test_the_biomass_is_alive_and_not_a_frozen_zero() -> None:
    """Um zero permanente é o sintoma exato do defeito que este arquivo previne."""
    trail = _trail()
    values = {round(s.biota.biomass, 9) for s in trail}
    assert len(values) > 10, "a biomassa não se moveu — a fatia ficou órfã?"
    assert max(s.biota.biomass for s in trail) > 1.0, "a vida nunca se estabeleceu"


def test_the_biotic_carbon_sink_reads_a_live_value() -> None:
    """O sumidouro biótico precisa MORDER, não recair num zero silencioso.

    Sem escritor, `carbon_uptake_coeff × 0 = 0` a cada tick: nenhum erro, nenhum
    teste vermelho, e o ciclo do carbono perde a absorção da vida.
    """
    trail = _trail()
    absorbed = [ATMOSPHERE.carbon_uptake_coeff * s.biota.biomass for s in trail]
    assert max(absorbed) > 0.0, "o sumidouro biótico está zerado"
    assert sum(1 for value in absorbed if value > 0.0) > TICKS // 2, (
        "a vida existiu em poucos ticks demais para o sumidouro significar algo"
    )


def test_the_resource_consumption_reads_a_live_value() -> None:
    """O segundo leitor: o consumo de recurso pela vida instalada."""
    trail = _trail()
    consumed = [s.resource.consumed for s in trail]
    assert max(consumed) > 0.0, "o Resource não está enxergando biomassa alguma"


# --- Trava 1b: o carbono continua fechando com o novo dono --------------------


def test_the_carbon_balance_still_closes_with_the_new_owner() -> None:
    """A identidade contábil do M2 vale com a biomassa vindo da Evolution.

    Este é o teste que o ADR 0012 fixou, reexecutado depois do reparenting: se o
    sumidouro biótico tivesse regredido a zero, a conta ainda fecharia — por isso
    ele vem ACOMPANHADO dos testes acima, que exigem um valor vivo. Os dois
    juntos é que cobrem o defeito; nenhum deles sozinho cobre.
    """
    trail = _trail()
    for before, after in pairwise(trail):
        injected = after.geology.co2_flux
        absorbed = ATMOSPHERE.carbon_uptake_coeff * before.biota.biomass
        weathered = ATMOSPHERE.weathering_coeff * before.atmosphere.co2
        total_before = (
            before.atmosphere.co2 + before.chemistry.ocean_carbon + before.chemistry.soil_carbon
        )
        total_after = (
            after.atmosphere.co2 + after.chemistry.ocean_carbon + after.chemistry.soil_carbon
        )
        assert total_after == pytest.approx(
            total_before + injected - absorbed - weathered, abs=1e-6
        ), f"o carbono deixou de fechar no tick {before.tick}"


# --- Trava 2: a defasagem de leitura sobreviveu à troca de dono ---------------


def test_biomass_read_is_lagged() -> None:
    """Atmosphere e Resource leem a biomassa do tick ANTERIOR — e isso é DECLARADO.

    A Evolution roda no FIM da ordem (…→resource→evolution→ecology), então quem
    corre antes dela naturalmente vê o valor do tick anterior. Mas "naturalmente"
    é acidente de ordenação: uma reordenação futura quebraria a defasagem em
    silêncio, e o acoplamento viraria síncrono sem que ninguém decidisse isso.

    Por isso a declaração é o que se afirma aqui, e não só o efeito.
    """
    from ecosfera_ai.engines.atmosphere.contracts import LAGGED_READS as ATMOSPHERE_LAGGED
    from ecosfera_ai.engines.atmosphere.contracts import READS as ATMOSPHERE_READS
    from ecosfera_ai.engines.resource.contracts import LAGGED_READS as RESOURCE_LAGGED
    from ecosfera_ai.engines.resource.contracts import READS as RESOURCE_READS

    assert SliceRef.BIOTA in ATMOSPHERE_LAGGED, "a atmosfera deixou de declarar a defasagem"
    assert SliceRef.BIOTA not in ATMOSPHERE_READS, "virou leitura do MESMO tick"
    assert SliceRef.BIOTA in RESOURCE_LAGGED, "o recurso deixou de declarar a defasagem"
    assert SliceRef.BIOTA not in RESOURCE_READS


def test_the_declared_lag_matches_the_actual_tick_order() -> None:
    """A declaração e a ordem têm de contar a mesma história.

    Declarar `lagged_reads` e depois rodar o escritor ANTES do leitor faria a
    leitura ser do mesmo tick, com a declaração mentindo. O `validate_graph`
    recusa o contrário (ler para a frente sem declarar); esta é a outra metade.

    A ordem é lida do REGISTRO CONSTRUÍDO, não da constante: comparar a
    declaração com outra declaração não afirmaria nada sobre o tick que roda.
    """
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    order = [engine.engine_id for engine in planet.registry.engines]
    assert order == list(ENGINE_ORDER), "a ordem construída divergiu da ordem declarada"

    writer = order.index("evolution")
    for reader in ("atmosphere", "resource"):
        assert order.index(reader) < writer, (
            f"{reader} declara ler a biota defasada, mas roda DEPOIS da evolution"
        )


def test_the_lag_is_observable_in_the_trajectory() -> None:
    """O efeito, e não só a declaração: o valor lido é o do tick anterior.

    Reproduz a conta do sumidouro biótico usando a biomassa DEFASADA e exige que
    ela case com o CO₂ que a atmosfera de fato produziu. Se a leitura passasse a
    ser do mesmo tick, a conta erraria pela variação de biomassa daquele passo.
    """
    trail = _trail(ticks=60)
    matches_lagged = 0
    for before, after in pairwise(trail):
        lagged = ATMOSPHERE.carbon_uptake_coeff * before.biota.biomass
        same_tick = ATMOSPHERE.carbon_uptake_coeff * after.biota.biomass
        if lagged == pytest.approx(same_tick, abs=1e-9):
            continue  # biomassa parada: o tick não distingue as hipóteses
        expected = (
            before.atmosphere.co2
            + after.geology.co2_flux
            - lagged
            - ATMOSPHERE.weathering_coeff * before.atmosphere.co2
            - after.chemistry.air_sea_flux
        )
        assert after.atmosphere.co2 == pytest.approx(max(0.0, expected), abs=1e-6)
        matches_lagged += 1
    assert matches_lagged > 10, "a biomassa mal se moveu — o teste não distinguiria nada"


# --- Trava 3: capacidade e biomassa não se confundem --------------------------


def test_capacity_is_the_limit_and_biomass_is_the_occupancy() -> None:
    """Resource não escreve biomassa; Evolution não redefine capacidade.

    É a fronteira onde um Engine futuro tende a se confundir (ADR 0016): um é o
    teto que o ambiente oferece, o outro é o quanto dele está preenchido.
    """
    from ecosfera_ai.engines.evolution.contracts import WRITES as EVOLUTION_WRITES
    from ecosfera_ai.engines.resource.contracts import WRITES as RESOURCE_WRITES

    assert RESOURCE_WRITES is SliceRef.RESOURCE
    assert EVOLUTION_WRITES is SliceRef.BIOTA

    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    for engine in planet.registry.engines:
        if engine.engine_id == "resource":
            assert engine.writes is not SliceRef.BIOTA
        if engine.engine_id == "evolution":
            assert engine.writes is not SliceRef.RESOURCE


def test_the_community_settles_inside_the_budget_it_was_given() -> None:
    """A ocupação acomoda NA capacidade, não acima dela.

    Uma biomassa que ultrapassasse a capacidade de forma sustentada seria dupla
    contagem por outro nome: a vida gastando um orçamento que o ambiente não
    publicou. Picos transitórios são legítimos (a densidade-dependência é
    contínua, não uma parede), o regime permanente não.
    """
    trail = _trail(ticks=400)
    settled = trail[200:]
    occupancy = [
        s.biota.biomass / s.resource.carrying_capacity
        for s in settled
        if s.resource.carrying_capacity > 0.0
    ]
    assert occupancy, "sem capacidade publicada, o teste não afirma nada"
    mean = sum(occupancy) / len(occupancy)
    assert mean < 1.25, f"a comunidade vive acima do orçamento (ocupação média {mean:.2f})"


def test_the_ecology_redistributes_without_creating_biomass() -> None:
    """A soma dos níveis tróficos é a biomassa da Evolution — nunca mais.

    A Ecology decide a FORMA da pirâmide; o tamanho é da Evolution. Se ela
    escrevesse um total próprio, haveria duas fontes de biomassa no world-state.
    """
    for snapshot in _trail(ticks=120):
        levels = (
            snapshot.ecology.producer_biomass
            + snapshot.ecology.herbivore_biomass
            + snapshot.ecology.predator_biomass
        )
        assert levels == pytest.approx(snapshot.biota.biomass, abs=1e-6), (
            "a soma trófica descolou da biomassa — a ecologia virou uma segunda fonte"
        )
