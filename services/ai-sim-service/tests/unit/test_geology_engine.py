"""Geology Engine: vulcanismo determinístico, fluxo de CO2 e erupções (M1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ecosfera_ai.engines.geology.contracts import load_params
from ecosfera_ai.engines.geology.domain import (
    is_eruption,
    outgassing_flux,
    relief_change,
    volcanism_change,
)
from ecosfera_ai.engines.geology.events import VOLCANIC_ERUPTION, GeologyCauseCode
from ecosfera_ai.engines.geology.service import GeologyEngine
from ecosfera_ai.shared_kernel.engine import TickBudget, TickContext
from ecosfera_ai.shared_kernel.events import CauseCodeEnum, Granularity
from ecosfera_ai.shared_kernel.rng import rng_for
from ecosfera_ai.shared_kernel.world_state import (
    GeologySlice,
    LegacySlice,
    SliceRef,
    WorldStateSnapshot,
)

PARAMS = load_params()


def _snapshot(volcanism: float = 1.0, relief: float = 0.2, water: float = 1.0, tick: int = 0):
    return WorldStateSnapshot(
        planet_id="p",
        seed=2027,
        tick=tick,
        era=0,
        geology=GeologySlice(relief=relief, volcanism=volcanism),
        legacy=LegacySlice(water=water),
    )


def _context(snapshot: WorldStateSnapshot) -> TickContext:
    return TickContext(
        snapshot=snapshot,
        rng=rng_for(snapshot.seed, "geology", snapshot.tick),
        tick=snapshot.tick,
        era=snapshot.era,
        budget=TickBudget(),
    )


def test_declares_its_slice_and_the_lagged_read() -> None:
    engine = GeologyEngine()
    assert engine.writes is SliceRef.GEOLOGY
    # A água vem do legado, que roda DEPOIS — a defasagem é declarada, não presumida.
    assert engine.lagged_reads == frozenset({SliceRef.LEGACY})
    assert SliceRef.ATMOSPHERE not in engine.reads | engine.lagged_reads


def test_volcanism_is_reproducible_under_the_same_seed() -> None:
    first = GeologyEngine().tick(_context(_snapshot()))
    second = GeologyEngine().tick(_context(_snapshot()))
    assert dict(first.delta.values) == dict(second.delta.values)


def test_different_seeds_diverge() -> None:
    a = GeologyEngine().tick(_context(_snapshot()))
    b = GeologyEngine().tick(_context(replace(_snapshot(), seed=999)))
    assert dict(a.delta.values) != dict(b.delta.values)


def test_volcanism_relaxes_toward_the_baseline() -> None:
    """Sem pulso, um vulcanismo acima da linha de base tem de cair."""
    high = volcanism_change(PARAMS.volcanism_baseline + 1.0, pulse=0.0, params=PARAMS)
    low = volcanism_change(PARAMS.volcanism_baseline - 1.0, pulse=0.0, params=PARAMS)
    assert high < 0.0 < low


def test_the_tectonic_pulse_is_always_a_source() -> None:
    """Um pulso negativo do RNG não pode virar vulcanismo negativo."""
    assert volcanism_change(1.0, pulse=-0.5, params=PARAMS) > volcanism_change(
        1.0, pulse=0.0, params=PARAMS
    )


def test_relief_is_uplift_minus_erosion() -> None:
    dry = relief_change(volcanism=1.0, relief=0.5, water=0.0, params=PARAMS)
    wet = relief_change(volcanism=1.0, relief=0.5, water=2.0, params=PARAMS)
    assert dry > wet, "mais água disponível deveria erodir mais"


def test_outgassing_grows_with_volcanism() -> None:
    assert outgassing_flux(2.0, PARAMS) > outgassing_flux(1.0, PARAMS) > 0.0


def test_the_engine_publishes_the_flux_without_touching_the_atmosphere() -> None:
    """A seta vulcanismo→CO2 cruza a fronteira só pelo Canal A (Spec §2)."""
    result = GeologyEngine().tick(_context(_snapshot()))
    assert result.delta.writes is SliceRef.GEOLOGY
    assert "co2_flux" in result.delta.values
    assert "co2" not in result.delta.values


def test_eruption_threshold_gates_the_event() -> None:
    quiet = GeologyEngine().tick(_context(_snapshot(volcanism=0.5)))
    assert quiet.events == ()

    loud = GeologyEngine().tick(_context(_snapshot(volcanism=3.0)))
    assert [e.event_type for e in loud.events] == [VOLCANIC_ERUPTION]


def test_eruption_event_is_a_complete_envelope() -> None:
    event = GeologyEngine().tick(_context(_snapshot(volcanism=3.0))).events[0]

    assert isinstance(event.cause_code, CauseCodeEnum)
    assert event.cause_code is GeologyCauseCode.TECTONIC_PULSE
    assert event.engine_id == "geology"
    assert event.resources == ("co2",)
    assert event.location["region_id"] == "global"
    assert event.granularity is Granularity.AGGREGATE
    assert event.occurred_at.tick == 0
    assert set(event.cause_detail) == {"volcanism", "pulse", "co2_flux"}


def test_the_delta_carries_the_event_that_caused_it() -> None:
    """Proveniência do Canal A: é o que encadeia `causation_id` adiante."""
    result = GeologyEngine().tick(_context(_snapshot(volcanism=3.0)))
    assert result.delta.caused_by == (result.events[0].event_id,)


def test_is_eruption_uses_the_versioned_threshold() -> None:
    assert is_eruption(PARAMS.eruption_threshold, PARAMS) is True
    assert is_eruption(PARAMS.eruption_threshold - 1e-9, PARAMS) is False


def test_params_come_from_versioned_data() -> None:
    assert PARAMS.version >= 1
    assert PARAMS.outgassing_base > 0.0
    with pytest.raises(FileNotFoundError):
        load_params(__import__("pathlib").Path("nao-existe.yaml"))
