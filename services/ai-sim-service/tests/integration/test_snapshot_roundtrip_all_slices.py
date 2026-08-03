"""A `EventSlice` sobrevive ao round-trip COM UM EVENTO EM CURSO.

A guarda GERAL do round-trip já existe desde o M3
(`test_snapshot_roundtrip.py`), é parametrizada por `SliceRef` e traz a lista de
campos derivados justificada um a um — ela cobre a fatia nova automaticamente, e
duplicá-la aqui só criaria duas listas de exceção para manter em dia.

O que este arquivo acrescenta é o caso que a guarda geral NÃO garante: um evento
ATIVO no meio da janela. A `EventSlice` carrega bookkeeping (qual evento, há
quantos ticks, com que severidade) e é aí que a perda seria silenciosa e grave —
um meteoro em curso sumiria no meio do próprio inverno de impacto, sem erro
nenhum, e a trajetória divergiria do replay gravado.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_scripted_planet

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.world_state import EventSlice, WorldStateSnapshot
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))
EVENT_FIELDS = tuple(EventSlice.__dataclass_fields__)


@pytest.fixture(scope="module")
def mid_event() -> WorldStateSnapshot:
    """Snapshot tirado com um meteoro EM CURSO — perturbação e bookkeeping vivos."""
    planet = build_scripted_planet(EventKind.METEOR, lead=3)
    snapshot = snapshot_of(initial_state(PlanetSeed("roundtrip-m4", 2027), PARAMS))
    for _ in range(200):
        snapshot = planet.tick(snapshot, publish=False).snapshot
        if snapshot.event.active_kind and snapshot.event.dust_load > 0.0:
            return snapshot
    raise AssertionError("nenhum evento ativo apareceu na janela")


def test_the_fixture_really_has_an_event_in_flight(mid_event: WorldStateSnapshot) -> None:
    """Sem isto, o teste seguinte confirmaria que zeros sobrevivem a zeros."""
    assert mid_event.event.active_kind != 0.0
    assert mid_event.event.dust_load > 0.0
    assert mid_event.event.active_severity > 0.0


def test_every_event_field_survives_the_round_trip(mid_event: WorldStateSnapshot) -> None:
    rebuilt = snapshot_of(planet_state_of(mid_event))
    for field in EVENT_FIELDS:
        assert getattr(rebuilt.event, field) == pytest.approx(getattr(mid_event.event, field)), (
            f"event.{field} não sobreviveu — sem casa no PlanetState"
        )


def test_the_bookkeeping_survives_so_the_event_does_not_restart(
    mid_event: WorldStateSnapshot,
) -> None:
    """`active_elapsed` é o que impede o evento de recomeçar do zero.

    Perdê-lo não zeraria a perturbação — a reiniciaria, e o inverno de impacto
    duraria para sempre.
    """
    rebuilt = snapshot_of(planet_state_of(mid_event))
    assert rebuilt.event.active_elapsed == mid_event.event.active_elapsed
    assert rebuilt.event.active_kind == mid_event.event.active_kind


def test_the_planet_continues_identically_after_a_round_trip(
    mid_event: WorldStateSnapshot,
) -> None:
    """A prova FUNCIONAL: passar pela ponte não muda o futuro do planeta."""
    planet = build_scripted_planet(EventKind.METEOR, lead=3)
    direct = mid_event
    through_bridge = snapshot_of(planet_state_of(mid_event))
    for _ in range(30):
        direct = planet.tick(direct, publish=False).snapshot
        through_bridge = planet.tick(through_bridge, publish=False).snapshot

    assert direct.event == through_bridge.event
    assert direct.climate.temperature == pytest.approx(through_bridge.climate.temperature)
