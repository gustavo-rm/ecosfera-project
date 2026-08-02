"""GUARDA DA DÍVIDA DE REHIDRATAÇÃO (ADR 0015).

A borda HTTP e a persistência guardam `PlanetState`, não `WorldStateSnapshot`.
`FrameworkTickOrchestrator.tick()` faz o ciclo `snapshot → Engines → PlanetState`
a CADA tick, então **um campo sem lugar no `PlanetState` volta a zero uma vez por
tick**. O Engine continua correto, o teste dele continua verde, e metade da
ciência simplesmente não realimenta nada.

É o mesmo padrão da falha do `solar_flux`: o sintoma é ausência, e ausência não
se denuncia sozinha.

O M2 fechou o buraco para as fatias que existiam. O risco é o PRÓXIMO Engine
(o Event Engine do M4 acrescenta estado) reabri-lo — e aí ninguém percebe.

## Como este arquivo protege

A regra é **inversão do padrão**: toda fatia, todo campo, DEVE sobreviver ao
round-trip. As exceções são declaradas uma a uma em `DERIVED_FIELDS`, com o
motivo. Quem acrescentar uma fatia nova e esquecer de mapeá-la na ponte não
precisa lembrar deste arquivo: o teste quebra sozinho, porque o default é
"tem de sobreviver".

Uma lista de campos a CONFERIR faria o oposto — protegeria só o que alguém
lembrou de listar, que é exatamente o esquecimento que se quer pegar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.composition import build_planet_engine
from ecosfera_ai.shared_kernel.world_state import (
    SliceRef,
    WorldStateSnapshot,
    slice_values,
)
from ecosfera_ai.simulation_engine.params import initial_state, load_params
from ecosfera_ai.simulation_engine.state import PlanetSeed

PARAMS = load_params(Path("configs/simulation_params.yaml"))

# As ÚNICAS perdas toleradas, cada uma com motivo. São grandezas DERIVADAS —
# funções puras de estoques que sobrevivem — e por isso o primeiro tick as
# recalcula idênticas (ADR 0011 §4b).
#
# Acrescentar campo aqui é decisão de projeto, não conveniência: significa
# afirmar que o valor é recuperável do que sobrou. Se não for, o campo pertence
# ao `PlanetState`.
DERIVED_FIELDS: dict[SliceRef, frozenset[str]] = {
    # Taxa do tick, função pura do vulcanismo.
    SliceRef.GEOLOGY: frozenset({"co2_flux"}),
    # Funções puras do estoque de CO2 (Myhre 1998 e a relação de pressão).
    SliceRef.ATMOSPHERE: frozenset({"greenhouse_forcing", "pressure"}),
}


def _evolved(ticks: int = 40, seed: int = 2027) -> WorldStateSnapshot:
    """Um snapshot com TODAS as fatias já em movimento — zeros não provam nada."""
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("roundtrip", seed), PARAMS))
    for _ in range(ticks):
        snapshot = planet.tick(snapshot, publish=False).snapshot
    return snapshot


def test_every_declared_slice_is_covered_by_this_test() -> None:
    """Se uma fatia nova aparecer, ela cai automaticamente sob a regra."""
    covered = set(SliceRef)
    assert covered, "SliceRef vazio — o world-state perdeu suas fatias"
    # `DERIVED_FIELDS` só pode citar fatias que existem.
    assert set(DERIVED_FIELDS) <= covered


@pytest.mark.parametrize("ref", list(SliceRef), ids=lambda r: r.value)
def test_snapshot_roundtrip_preserves_all_slices(ref: SliceRef) -> None:
    """`snapshot → PlanetState → snapshot` não pode perder campo algum.

    Parametrizado por fatia DECLARADA, e não por uma lista escrita à mão: um
    Engine novo entra aqui sozinho no dia em que sua fatia entrar no `SliceRef`.
    """
    rich = _evolved()
    survived = snapshot_of(planet_state_of(rich))

    before = slice_values(rich.slice_of(ref))
    after = slice_values(survived.slice_of(ref))
    derived = DERIVED_FIELDS.get(ref, frozenset())

    assert set(before) == set(after), f"a fatia {ref} mudou de forma no round-trip"

    lost = {
        name: (value, after[name])
        for name, value in before.items()
        if name not in derived and after[name] != value
    }
    assert not lost, (
        f"a ponte perdeu campos de {ref}: {sorted(lost)}. "
        "Ou o campo entra no `PlanetState` (engines/bridge.py), ou é declarado "
        "em DERIVED_FIELDS com o motivo pelo qual é recuperável."
    )


@pytest.mark.parametrize("ref", list(SliceRef), ids=lambda r: r.value)
def test_the_slices_are_not_trivially_zero(ref: SliceRef) -> None:
    """Um round-trip de zeros passaria mesmo com a ponte inteira quebrada."""
    rich = _evolved()
    values = slice_values(rich.slice_of(ref))
    assert any(value != 0.0 for value in values.values()), (
        f"a fatia {ref} está inteira em zero depois de 40 ticks — "
        "o teste de round-trip não estaria provando nada sobre ela"
    )


def test_the_declared_losses_really_are_recoverable() -> None:
    """As exceções não são desculpa: o primeiro tick as recalcula idênticas.

    É isso que separa "derivado" de "perdido". Se um campo listado em
    `DERIVED_FIELDS` não voltar ao mesmo valor, a exceção está errada e o campo
    precisa ser persistido.
    """
    rich = _evolved()
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)

    direct = planet.tick(rich, publish=False).snapshot
    through_bridge = planet.tick(snapshot_of(planet_state_of(rich)), publish=False).snapshot

    for ref, fields in DERIVED_FIELDS.items():
        straight = slice_values(direct.slice_of(ref))
        recovered = slice_values(through_bridge.slice_of(ref))
        for name in fields:
            assert recovered[name] == pytest.approx(straight[name], rel=1e-9), (
                f"{ref}.{name} foi declarado derivado mas NÃO se recupera — "
                "ele precisa entrar no `PlanetState`"
            )


def test_the_planet_state_carries_no_field_the_bridge_ignores() -> None:
    """A dívida é bidirecional: campo escrito e nunca lido também é armadilha."""
    rich = _evolved()
    state = planet_state_of(rich)
    rebuilt = planet_state_of(snapshot_of(state))

    from dataclasses import fields as dataclass_fields

    ignored = [
        f.name
        for f in dataclass_fields(state)
        if isinstance(getattr(state, f.name), float)
        and getattr(rebuilt, f.name) != getattr(state, f.name)
    ]
    assert not ignored, f"o `PlanetState` carrega campos que a ponte não reconstrói: {ignored}"
