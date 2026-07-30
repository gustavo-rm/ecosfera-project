"""Canal A: composição de deltas e invariantes do world-state (Spec §3)."""

from __future__ import annotations

import pytest

from ecosfera_ai.shared_kernel.world_state import (
    BoundedFraction,
    ClimateSlice,
    NonNegativeStocks,
    SliceRef,
    StateDelta,
    WorldStateSnapshot,
    apply_delta,
    compose,
    difference,
)


def _snapshot(**climate: float) -> WorldStateSnapshot:
    return WorldStateSnapshot(planet_id="p", seed=1, tick=0, era=0, climate=ClimateSlice(**climate))


def _delta(engine: str, **values: float) -> StateDelta:
    return StateDelta(engine_id=engine, tick=0, writes=SliceRef.CLIMATE, values=values)


def test_merge_is_associative() -> None:
    """(a+b)+c == a+(b+c) — pré-requisito para compor deltas sem ambiguidade.

    Os valores são frações binárias exatas (0.5, 0.25, 0.125) de propósito: a
    associatividade que se afirma aqui é a da ESTRUTURA (união de chaves + soma),
    não a da aritmética de ponto flutuante, que não é associativa em geral.
    """
    a = _delta("a", temperature=0.5, energy=0.25)
    b = _delta("b", temperature=0.25, ice_cover=0.125)
    c = _delta("c", energy=0.5)

    left = a.merge(b).merge(c)
    right = a.merge(b.merge(c))

    assert dict(left.values) == dict(right.values)
    assert dict(left.values) == {"temperature": 0.75, "energy": 0.75, "ice_cover": 0.125}


def test_merge_refuses_deltas_from_different_slices() -> None:
    climate = _delta("a", temperature=1.0)
    biota = StateDelta(engine_id="b", tick=0, writes=SliceRef.BIOTA, values={"biomass": 1.0})
    with pytest.raises(ValueError, match="fatias distintas"):
        climate.merge(biota)


def test_compose_is_deterministic_and_order_sensitive() -> None:
    """A mesma sequência sempre dá o mesmo resultado; a ordem é significativa.

    Sequencial (não simultâneo) é a decisão do ADR 0008: só assim a ordem de
    acoplamento da Spec §5.3 tem efeito físico.
    """
    base = _snapshot(temperature=10.0)
    deltas = [_delta("chemistry", temperature=2.0), _delta("ocean", temperature=-0.5)]

    first = compose(base, deltas)
    second = compose(base, deltas)

    assert first.snapshot == second.snapshot
    assert first.snapshot.climate.temperature == 11.5


def test_delta_only_touches_the_slice_it_declares() -> None:
    base = WorldStateSnapshot(planet_id="p", seed=1, tick=0, era=0)
    after = apply_delta(base, _delta("climate", temperature=3.0))

    assert after.climate.temperature == 3.0
    assert after.biota == base.biota
    assert after.chemistry == base.chemistry
    assert after.geology == base.geology


def test_delta_with_unknown_field_is_rejected() -> None:
    """Erro de fronteira aparece na hora, não como campo silenciosamente perdido."""
    base = _snapshot()
    bogus = StateDelta(
        engine_id="climate", tick=0, writes=SliceRef.CLIMATE, values={"biomass": 1.0}
    )
    with pytest.raises(ValueError, match="campos inexistentes"):
        apply_delta(base, bogus)


def test_non_negative_stocks_clamps_and_reports() -> None:
    """O recorte é determinístico; o REGISTRO é que segue para a observabilidade."""
    base = _snapshot(energy=1.0)
    invariant = NonNegativeStocks({SliceRef.CLIMATE: ("energy",)})

    outcome = compose(base, [_delta("climate", energy=-5.0)], [invariant])

    assert outcome.snapshot.climate.energy == 0.0
    assert len(outcome.breaches) == 1
    breach = outcome.breaches[0]
    assert (breach.invariant, breach.field, breach.value) == ("non_negative_stocks", "energy", -4.0)


def test_bounded_fraction_keeps_ice_cover_physical() -> None:
    base = _snapshot(ice_cover=0.9)
    invariant = BoundedFraction({SliceRef.CLIMATE: ("ice_cover",)})

    outcome = compose(base, [_delta("climate", ice_cover=0.5)], [invariant])

    assert outcome.snapshot.climate.ice_cover == 1.0
    assert outcome.breaches[0].limit == 1.0


def test_invariants_do_not_fire_inside_the_valid_range() -> None:
    base = _snapshot(ice_cover=0.4, energy=2.0)
    invariants = [
        NonNegativeStocks({SliceRef.CLIMATE: ("energy",)}),
        BoundedFraction({SliceRef.CLIMATE: ("ice_cover",)}),
    ]

    outcome = compose(base, [_delta("climate", ice_cover=0.1, energy=1.0)], invariants)

    assert outcome.breaches == ()
    assert outcome.snapshot.climate.ice_cover == pytest.approx(0.5)


def test_difference_round_trips_through_a_delta() -> None:
    """Ler a variação e reaplicá-la reproduz a fatia — base do adaptador legado."""
    before = ClimateSlice(temperature=5.0, ice_cover=0.2, energy=1.0)
    after = ClimateSlice(temperature=7.5, ice_cover=0.1, energy=1.0)

    base = _snapshot(temperature=5.0, ice_cover=0.2, energy=1.0)
    rebuilt = apply_delta(
        base,
        StateDelta(
            engine_id="x", tick=0, writes=SliceRef.CLIMATE, values=difference(before, after)
        ),
    )

    assert rebuilt.climate == after


def test_snapshot_is_immutable() -> None:
    snapshot = _snapshot(temperature=1.0)
    with pytest.raises(AttributeError):
        snapshot.tick = 5  # type: ignore[misc]
    assert snapshot.advanced().tick == 1
    assert snapshot.tick == 0
