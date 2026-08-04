"""(F) A dívida de carbono fica OBSERVÁVEL e EXPORTÁVEL — não corrigida.

O M4 mediu que o CO₂ não tem equilíbrio de longo prazo (ADR 0020) e não tinha
como MOSTRAR isso: a suíte verificava correção por tick, e o colapso só aparece
na trajetória. Este arquivo instrumenta a dívida.

**O que ele NÃO afirma:** que o planeta é estável. Ele não é, e a instabilidade
segue como `xfail` anotado em `test_baseline_is_physics.py`. Afirmar estabilidade
aqui esconderia a dívida sob um teste verde — o oposto do propósito.

O que ele afirma é que a SÉRIE está íntegra: alinhada, completa, com os termos do
ciclo do carbono separados, e legível fora daqui.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import snapshot_of
from ecosfera_ai.shared_kernel.timeseries import CARBON_CHANNELS, TimeSeries, collect
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
# ALÉM do horizonte válido de ~500 ticks, de propósito: é justamente a região em
# que a dívida se manifesta, e a ferramenta existe para enxergá-la.
LONG_RUN = 900


@pytest.fixture(scope="module")
def series() -> TimeSeries:
    planet = build_quiet_planet()
    snapshot = snapshot_of(initial_state(PlanetSeed("carbon", 2027), PARAMS))
    trail = [snapshot]
    for _ in range(LONG_RUN):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        trail.append(snapshot)
    return collect(trail)


def test_the_series_covers_the_whole_long_run(series: TimeSeries) -> None:
    assert len(series.ticks) == LONG_RUN + 1
    assert series.ticks == tuple(range(LONG_RUN + 1))


def test_every_carbon_channel_is_present_and_aligned(series: TimeSeries) -> None:
    """Os termos SEPARADOS: ver o CO₂ subir diz QUE escapa, não ONDE."""
    assert set(series.channels) == set(CARBON_CHANNELS)
    for name, values in series.channels.items():
        assert len(values) == len(series.ticks), f"canal {name} desalinhado"
        assert all(isinstance(v, float) for v in values)


def test_the_source_and_the_reservoirs_are_separable(series: TimeSeries) -> None:
    """O diagnóstico futuro precisa somar entrada e saída — logo precisa dos dois."""
    assert any(v > 0.0 for v in series.channel("geology_outgassing")), "sem fonte registrada"
    assert any(v > 0.0 for v in series.channel("atmosphere_co2")), "sem estoque registrado"
    assert any(v > 0.0 for v in series.channel("ocean_carbon")), "sem reservatório oceânico"
    assert any(v > 0.0 for v in series.channel("biomass")), "sem sumidouro biótico"


def test_the_csv_opens_in_a_spreadsheet(series: TimeSeries) -> None:
    """Formato ABERTO: quem investiga a dívida é um humano com uma planilha."""
    rows = list(csv.reader(io.StringIO(series.to_csv())))
    header, *body = rows
    assert header[0] == "tick"
    assert set(header[1:]) == set(CARBON_CHANNELS)
    assert len(body) == len(series.ticks)
    assert [float(cell) for cell in body[0][1:]]  # tudo numérico


def test_the_json_export_is_complete(series: TimeSeries) -> None:
    data = json.loads(series.to_json())
    assert data["seed"] == 2027
    assert len(data["ticks"]) == LONG_RUN + 1
    assert set(data["channels"]) == set(CARBON_CHANNELS)


def test_a_misaligned_series_is_refused() -> None:
    """Uma série desalinhada mentiria sobre QUANDO cada valor ocorreu."""
    with pytest.raises(ValueError, match="desalinhada|pontos"):
        TimeSeries(planet_id="p", seed=1, ticks=(0, 1, 2), channels={"x": (0.0,)})


def test_the_export_does_not_claim_the_planet_is_stable(series: TimeSeries) -> None:
    """AFIRMAÇÃO EXPLÍCITA do que este arquivo não faz.

    A instabilidade é real e permanece dívida aberta (ADR 0020). Este teste
    existe para que ninguém leia o arquivo como se ele atestasse estabilidade —
    ele atesta que a série que a REVELA está íntegra e exportável.
    """
    co2 = series.channel("atmosphere_co2")
    amplitude = max(co2) - min(co2)
    assert amplitude > 0.0, "a série está constante — não mediria instabilidade alguma"
    # Sem asserção sobre a DIREÇÃO ou o limite do CO₂: isso é o `xfail` do M4.


def test_the_series_is_deterministic() -> None:
    """Mesma semente, mesma série — a instrumentação não introduz ruído."""

    def run() -> TimeSeries:
        planet = build_quiet_planet()
        snapshot = snapshot_of(initial_state(PlanetSeed("carbon-det", 99), PARAMS))
        trail = [snapshot]
        for _ in range(120):
            snapshot = planet.tick(snapshot, publish=False).snapshot
            trail.append(snapshot)
        return collect(trail)

    assert run().to_json() == run().to_json()
