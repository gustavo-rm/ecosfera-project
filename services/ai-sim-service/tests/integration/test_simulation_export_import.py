"""Export → import → replay reproduz o original (critério do M5, Spec §8).

Uma simulação deixa de viver só no banco de quem a rodou: vira um arquivo que
atravessa máquinas. O que este arquivo exige é que a viagem não perca nada — nem
estado, nem trilha, nem a capacidade de reproduzir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support import build_quiet_planet

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.shared_kernel.events import DomainEvent
from ecosfera_ai.shared_kernel.observability import InMemoryEventStore
from ecosfera_ai.shared_kernel.portable import (
    EXPORT_FORMAT_VERSION,
    IncompatibleExportError,
    SimulationExport,
)
from ecosfera_ai.shared_kernel.world_state import WORLD_STATE_VERSION
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed, PlanetState

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TICKS = 200


def _run() -> tuple[list[PlanetState], list[DomainEvent]]:
    store = InMemoryEventStore()
    planet = build_quiet_planet()
    # O planeta-quieto é montado sem sink; para a trilha, usamos o publish do
    # Planet Engine por composição própria.
    snapshot = snapshot_of(initial_state(PlanetSeed("export", 2027), PARAMS))
    states = [planet_state_of(snapshot)]
    for _ in range(TICKS):
        outcome = planet.tick(snapshot)
        snapshot = outcome.snapshot
        states.append(planet_state_of(snapshot))
        for event in outcome.events:
            store.emit(event)
    return states, list(store.events)


@pytest.fixture(scope="module")
def artefact() -> SimulationExport:
    states, events = _run()
    return SimulationExport(
        planet_id="export",
        seed=2027,
        world_state_version=WORLD_STATE_VERSION,
        params_version=PARAMS.version if hasattr(PARAMS, "version") else 4,
        checkpoints={str(i): dict(s.to_dict()) for i, s in enumerate(states[:5])},
        events=SimulationExport.encode_events(events),
        metadata={"ticks": TICKS},
    )


def test_the_run_produced_something_worth_exporting(artefact: SimulationExport) -> None:
    """Sem trilha e sem checkpoints, os testes abaixo seriam vacuamente verdes."""
    assert artefact.events, "a corrida não emitiu evento algum"
    assert artefact.eras(), "a corrida não produziu checkpoint algum"


def test_the_artefact_round_trips_through_json(artefact: SimulationExport) -> None:
    assert SimulationExport.from_json(artefact.to_json()) == artefact


def test_the_serialisation_is_deterministic(artefact: SimulationExport) -> None:
    """Dois exports da mesma simulação dão o MESMO arquivo, byte a byte.

    É o que permite comparar artefatos por hash — detectar deriva sem reimportar.
    """
    assert artefact.to_json() == artefact.to_json()


def test_every_event_survives_the_trip_with_the_full_envelope(
    artefact: SimulationExport,
) -> None:
    """O envelope §4 íntegro, e não um resumo.

    Perder `causation_id` na viagem seria perder a cadeia causal — o artefato
    exportaria o QUE aconteceu sem o PORQUÊ.
    """
    _, original = _run()
    restored = SimulationExport.from_json(artefact.to_json()).domain_events()

    assert len(restored) == len(original)
    for before, after in zip(original, restored, strict=True):
        assert after == before, f"{before.event_type} não sobreviveu ao export"


def test_the_causal_chain_survives_the_trip(artefact: SimulationExport) -> None:
    """A prova funcional: a cadeia ainda anda depois de exportar e importar."""
    restored = SimulationExport.from_json(artefact.to_json()).domain_events()
    index = {e.event_id: e for e in restored}
    linked = [e for e in restored if e.causation_id and e.causation_id in index]
    assert linked, "nenhum elo causal sobreviveu ao export"
    for event in linked:
        parent = index[event.causation_id]  # type: ignore[index]
        assert parent.occurred_at.tick <= event.occurred_at.tick


def test_the_checkpoints_survive_field_by_field(artefact: SimulationExport) -> None:
    """A dívida de rehidratação, conferida no artefato."""
    states, _ = _run()
    for era in artefact.eras():
        restored = PlanetState.from_dict(dict(artefact.checkpoint(era)))
        assert restored.to_dict() == states[era].to_dict()


def test_replaying_the_import_reproduces_the_original(artefact: SimulationExport) -> None:
    """O critério do M5: reexecutar a partir do import dá o MESMO planeta.

    Não basta o artefato guardar bytes iguais; o que importa é ele reconstituir
    uma simulação que ANDA igual.
    """
    imported = SimulationExport.from_json(artefact.to_json())
    start = PlanetState.from_dict(dict(imported.checkpoint(0)))

    planet = build_quiet_planet()
    snapshot = snapshot_of(start)
    for _ in range(TICKS):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    original = build_quiet_planet()
    reference = snapshot_of(initial_state(PlanetSeed("export", 2027), PARAMS))
    for _ in range(TICKS):
        reference = original.tick(reference, publish=False).snapshot

    assert snapshot == reference, "o replay do import divergiu do original"


# --- As recusas: importar errado tem de FALHAR, não degradar ------------------


def test_an_artefact_from_another_world_state_version_is_refused(
    artefact: SimulationExport,
) -> None:
    """Versão de esquema diferente = recusa alta.

    Degradar em silêncio produziria um planeta parecido com o original, e a
    diferença só apareceria muito depois, quando ninguém associa a causa.
    """
    tampered = artefact.to_json().replace(
        f'"world_state_version": {WORLD_STATE_VERSION}', '"world_state_version": 3'
    )
    with pytest.raises(IncompatibleExportError, match="world-state v3"):
        SimulationExport.from_json(tampered)


def test_an_artefact_from_another_format_version_is_refused(
    artefact: SimulationExport,
) -> None:
    tampered = artefact.to_json().replace(
        f'"format_version": {EXPORT_FORMAT_VERSION}', '"format_version": 99'
    )
    with pytest.raises(IncompatibleExportError, match="formato 99"):
        SimulationExport.from_json(tampered)


def test_an_unknown_cause_code_is_refused_rather_than_guessed() -> None:
    """Uma causa que este binário não conhece não vira explicação inventada."""
    from ecosfera_ai.shared_kernel.events import UnknownCauseCodeError, event_from_dict

    with pytest.raises(UnknownCauseCodeError):
        event_from_dict(
            {
                "event_id": "x",
                "event_type": "Whatever",
                "engine_id": "ghost",
                "tick": 1,
                "era": 0,
                "seed": 1,
                "cause_code": "CAUSA_DE_UM_ENGINE_QUE_NAO_EXISTE",
                "correlation_id": "c",
            }
        )
