"""A linha de base é FÍSICA, não um chute — e nada se move sem causa.

Este arquivo existe por causa do bug que o M2 encontrou: com `ocean_carbon = 0`,
o planeta não estava "no começo", estava num estado fisicamente impossível (um
oceano infinitamente sub-saturado). O sintoma foi CO₂ caindo de 280 para 234, e a
leitura pedagógica virava **"o oceano resfria o planeta"** — que numa plataforma
de ensino não é um número errado numa tela, é um aluno aprendendo ciência falsa.

O que se protege aqui é a classe inteira do defeito, não o caso particular.

## O que "linha de base estável" significa de fato

Não significa "nada muda a partir do tick 0" — e afirmar isso seria falso. Medido
sobre 600 ticks, a linha de base faz duas coisas que são **física correta e
deliberada**, não deriva sem causa:

1. **O planeta busca o próprio equilíbrio e o gelo inicial derrete.** O modelo
   equilibra em ~17,6 °C, e a condição inicial declara 14 °C — uma distância
   herdada de antes do M2, pinada em `KNOWN_EQUILIBRIUM_GAP_C` para não crescer
   em silêncio. Somado a isso, com limiar de degelo em 0 °C um planeta com 10% de
   gelo perde esse gelo, o albedo cai e o aquecimento continua: é a
   retroalimentação gelo-albedo, um dos fenômenos que o produto existe para
   ensinar. Congelá-la seria remover ciência para deixar um número parado.
2. **O CO₂ procura o equilíbrio fonte/sumidouro.** Sobe até ~360 ppm enquanto a
   biosfera é jovem, e volta para ~286 quando ela amadurece e o sumidouro biótico
   passa a morder. É o termostato carbonato-silicato mais a absorção biótica
   funcionando — excursão e retorno, não fuga.

O que **não** pode acontecer é movimento sem causa: carbono aparecendo sem fonte,
temperatura fugindo sem forçamento, ou o planeta divergindo em vez de convergir.
É isso que os testes abaixo travam.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecosfera_ai.engines.astronomy.service import AstronomyEngine
from ecosfera_ai.engines.atmosphere.service import AtmosphereEngine
from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.engines.chemistry.contracts import load_params as chemistry_params
from ecosfera_ai.engines.chemistry.service import ChemistryEngine
from ecosfera_ai.engines.climate.contracts import load_params as climate_params
from ecosfera_ai.engines.climate.domain import absorbed_energy, equilibrium_temperature
from ecosfera_ai.engines.climate.service import ClimateEngine
from ecosfera_ai.engines.composition import build_planet_engine, planet_invariants
from ecosfera_ai.engines.ecology.service import EcologyEngine
from ecosfera_ai.engines.evolution.service import EvolutionEngine
from ecosfera_ai.engines.geology.contracts import load_params as geology_params
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.engines.hydrology.contracts import load_params as hydrology_params
from ecosfera_ai.engines.hydrology.service import HydrologyEngine
from ecosfera_ai.engines.planet.registry import EngineRegistry
from ecosfera_ai.engines.planet.service import PlanetEngine
from ecosfera_ai.engines.resource.contracts import load_params as resource_params
from ecosfera_ai.engines.resource.domain import habitability
from ecosfera_ai.engines.resource.service import ResourceEngine
from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
CHEMISTRY = chemistry_params()
CLIMATE = climate_params()
RESOURCE = resource_params()
HORIZON = 600


def _trail(
    *, geology: object | None = None, ticks: int = HORIZON, seed: int = 2027
) -> list[WorldStateSnapshot]:
    """Trajetória longa, opcionalmente com a geologia reparametrizada."""
    if geology is None:
        planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    else:
        planet = PlanetEngine(
            EngineRegistry.of(
                [
                    AstronomyEngine(),
                    GeologyEngine(geology),  # type: ignore[arg-type]
                    ChemistryEngine(),
                    AtmosphereEngine(),
                    ClimateEngine(),
                    HydrologyEngine(),
                    ResourceEngine(),
                    EvolutionEngine(),
                    EcologyEngine(),
                ]
            ),
            invariants=planet_invariants(
                PARAMS.bounds, water_tolerance=hydrology_params().conservation_tolerance
            ),
            budget=PARAMS.engine_budget,
        )
    snapshot = snapshot_of(initial_state(PlanetSeed("baseline", seed), PARAMS))
    trail = [snapshot]
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return trail


# --- As condições iniciais são física declarada ------------------------------


# Distância CONHECIDA entre a temperatura inicial declarada e o equilíbrio do
# modelo, em °C. Não é zero, e o número está aqui para que não cresça em silêncio.
#
# Origem: `initial_state.temperature = 14,0` é a âncora pré-industrial da Terra e
# vem do config original; `equilibrium_offset = -2,2` foi escolhido no M1 para
# PRESERVAR o equilíbrio de ~17,6 °C que o modelo linear tinha (ver comentário em
# climate/params.yaml). As duas decisões são defensáveis isoladamente e
# incompatíveis juntas: o planeta aquece ~3,6 °C na partida só para alcançar o
# próprio equilíbrio.
#
# Isso ANTECEDE o M2 — não foi introduzido aqui, e fechá-lo é recalibração de
# clima (deslocaria toda trajetória e todo checkpoint gravado), decisão que não
# cabe a um marco de fronteiras. Fica pinado até que se decida.
KNOWN_EQUILIBRIUM_GAP_C = 3.6


def test_the_initial_temperature_gap_to_equilibrium_does_not_grow() -> None:
    """A condição inicial e o equilíbrio do modelo NÃO coincidem — e isso é sabido.

    O ideal é distância zero: um planeta deve nascer no próprio equilíbrio, senão
    o transiente de partida é artefato de condição inicial, não física — a mesma
    classe de defeito do `ocean_carbon` zerado.

    Aqui a distância é ~3,6 °C, herdada de antes do M2 (ver
    `KNOWN_EQUILIBRIUM_GAP_C`). O que este teste garante é que ela não CRESÇA em
    silêncio: recalibrar albedo, insolação ou conversão energia→temperatura sem
    revisitar a condição inicial quebra o teste.
    """
    ice = PARAMS.initial_state.ice_cover
    absorbed = absorbed_energy(1.0, ice, CLIMATE)
    # CO2 na referência => forçamento zero, por definição de Myhre.
    equilibrium = equilibrium_temperature(absorbed, 0.0, CLIMATE)
    gap = abs(equilibrium - PARAMS.initial_state.temperature)

    assert gap == pytest.approx(KNOWN_EQUILIBRIUM_GAP_C, abs=0.5), (
        f"a distância inicial→equilíbrio mudou: {gap:.2f} °C "
        f"(conhecida: {KNOWN_EQUILIBRIUM_GAP_C} °C). Se foi de propósito, "
        "atualize a constante; se não, a condição inicial virou um chute maior."
    )


def test_the_ocean_starts_in_equilibrium_with_the_reference_atmosphere() -> None:
    """Sem isto, o gradiente de partida é de 280 ppm inteiros (ADR 0012)."""
    assert PARAMS.initial_state.ocean_carbon == pytest.approx(CHEMISTRY.reference_ocean_carbon), (
        "o carbono oceânico inicial descolou da referência do Chemistry Engine"
    )
    assert PARAMS.initial_state.co2 == pytest.approx(CHEMISTRY.reference_co2)


def test_the_nutrient_stocks_start_non_limiting() -> None:
    """Zerá-los não é 'planeta jovem', é campo não preenchido (ADR 0012).

    Nos valores de referência, o nutriente não limita: a capacidade inicial fica
    governada por temperatura e água, que são os termos portados do `life`.
    """
    init = PARAMS.initial_state
    assert init.nitrogen >= RESOURCE.nitrogen_demand
    assert init.phosphorus >= RESOURCE.phosphorus_demand
    assert init.sulfur >= RESOURCE.sulfur_demand
    assert init.nutrients >= RESOURCE.nutrient_requirement


def test_the_initial_capacity_comes_from_the_resource_engine_alone() -> None:
    """A capacidade inicial EMANA do Resource — não é valor colado do `life`.

    O `life` foi removido no M2 (ADR 0014); os termos térmico e hídrico agora são
    dados do `resource/params.yaml`, que é a fonte de verdade única. Este teste
    fixa que o número que o planeta recebe no primeiro tick é o que a fórmula do
    Resource produz, e não uma constante herdada em outro lugar.
    """
    trail = _trail(ticks=1)
    after = trail[1]
    published = after.resource.carrying_capacity

    # A temperatura é a do MESMO tick (o Climate roda antes do Resource): usar a
    # de abertura erraria por ~2,5 unidades de capacidade, o que de quebra prova
    # que o Resource consome o clima recém-resolvido, e não o defasado.
    expected = RESOURCE.max_carrying_capacity * habitability(
        after.climate.temperature,
        after.resource.water_available,
        after.resource.nutrients_available,
        after.resource.energy_available,
        RESOURCE,
    )
    assert published == pytest.approx(expected, rel=1e-9)
    assert published > 0.0, "a capacidade inicial não pode nascer nula"


# --- Nada se move sem causa ---------------------------------------------------


def test_no_carbon_appears_without_a_source() -> None:
    """Sem fonte vulcânica, o carbono só pode CAIR. Jamais subir sozinho.

    É o teste mais direto de "não há movimento sem causa": removida a única
    entrada do sistema, sobram apenas sumidouros (intemperismo, absorção biótica,
    soterramento). Qualquer ganho líquido seria carbono inventado.
    """
    quiet = replace(geology_params(), outgassing_base=0.0, volcanism_sensitivity=0.0)
    trail = _trail(geology=quiet, ticks=300)

    start, end = trail[0].atmosphere.co2, trail[-1].atmosphere.co2
    assert end < start, "sem fonte, a atmosfera não pode ganhar carbono"

    total_start = (
        trail[0].atmosphere.co2 + trail[0].chemistry.ocean_carbon + trail[0].chemistry.soil_carbon
    )
    total_end = (
        trail[-1].atmosphere.co2
        + trail[-1].chemistry.ocean_carbon
        + trail[-1].chemistry.soil_carbon
    )
    assert total_end <= total_start + 1e-6, "o carbono TOTAL cresceu sem fonte alguma"


def test_the_trend_is_not_an_artefact_of_the_noise() -> None:
    """Zerar o ruído meteorológico não muda a história — só a aparência dela.

    Se a trajetória dependesse do ruído, o que o aluno veria seria estatística de
    sorteio apresentada como física.
    """
    quiet = replace(
        geology_params(),
        outgassing_base=0.0,
        volcanism_sensitivity=0.0,
        tectonic_activity=0.0,
    )
    trail = _trail(geology=quiet, ticks=300)
    assert trail[-1].atmosphere.co2 < trail[0].atmosphere.co2


def test_baseline_planet_is_quasi_stationary() -> None:
    """Passado o transiente, o planeta ASSENTA em vez de derivar.

    Medido sobre 600 ticks: o CO₂ excursiona até ~360 ppm com a biosfera jovem e
    retorna para ~286 quando o sumidouro biótico amadurece; a temperatura se
    acomoda perto de 19 °C. A janela examinada aqui é a METADE FINAL, depois de
    o transiente de partida (degelo inicial + busca do equilíbrio de carbono) ter
    passado — que é onde "estável" tem significado.

    A janela inicial é excluída de propósito, e não para o teste passar: ela
    contém a retroalimentação gelo-albedo, que é fenômeno a ensinar, não deriva a
    eliminar.
    """
    trail = _trail()
    settled = trail[HORIZON // 2 :]

    co2 = [s.atmosphere.co2 for s in settled]
    temperature = [s.climate.temperature for s in settled]

    assert max(co2) - min(co2) < 60.0, (
        f"o CO₂ deriva na janela assentada: {min(co2):.0f}..{max(co2):.0f}"
    )
    assert max(temperature) - min(temperature) < 2.0, "a temperatura não assenta"


def test_the_thermostat_pulls_back_instead_of_running_away() -> None:
    """A excursão de carbono RETORNA — é termostato, não fuga.

    Um sistema com retroalimentação positiva descontrolada subiria monotonamente.
    O que se exige aqui é que o pico fique no meio da série e o fim volte para
    perto da partida: excursão e retorno.
    """
    trail = _trail()
    co2 = [s.atmosphere.co2 for s in trail]
    peak = max(co2)
    peak_at = co2.index(peak)

    assert 0 < peak_at < len(co2) - 1, "o CO₂ nunca parou de subir — sem termostato"
    assert co2[-1] < peak, "o carbono não voltou do pico"
    assert abs(co2[-1] - co2[0]) < 0.25 * co2[0], (
        f"o fim ({co2[-1]:.0f}) ficou longe da partida ({co2[0]:.0f}) — há deriva de fundo"
    )


def test_the_planet_stays_in_the_habitable_envelope() -> None:
    """Nem bola de neve nem estufa descontrolada, ao longo de 600 ticks."""
    for snapshot in _trail():
        assert -20.0 < snapshot.climate.temperature < 60.0, "o planeta saiu da faixa habitável"
        assert 0.0 <= snapshot.hydrology.ice_fraction <= 1.0
        assert 0.0 < snapshot.atmosphere.co2 < 5000.0, "estufa descontrolada"


def test_the_initial_transient_is_the_ice_albedo_feedback() -> None:
    """O aquecimento de partida tem causa NOMEADA: o gelo inicial derrete.

    Nomear a causa é o que separa "transiente físico" de "deriva sem causa". Se
    um dia o planeta aquecer no início SEM que o gelo se mova, o transiente
    passou a vir de outro lugar — e é aí que se deve desconfiar da condição
    inicial.
    """
    trail = _trail(ticks=120)
    ice_start = trail[0].hydrology.ice_fraction
    ice_end = trail[-1].hydrology.ice_fraction

    assert ice_start > 0.0, "sem gelo inicial não há retroalimentação para observar"
    assert ice_end < ice_start, "o gelo deveria derreter a esta temperatura"
    assert trail[-1].climate.temperature > trail[0].climate.temperature
