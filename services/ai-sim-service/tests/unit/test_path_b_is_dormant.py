"""O CAMINHO B ESTÁ DORMENTE (ADR 0017, tempo 1).

A ciência inválida não roda sem ser pedida.

`biology_enabled` liga o caminho de biologia POR ERA — `simulation_engine/biology/`,
um AG do DEAP com `selTournament` sobre uma função de aptidão ESCALAR. A DEC-01 diz
que "não existe função de aptidão em nenhum ponto"; o ADR-ARCH-0001 superou o
fitness global por ser teleológico; e a auditoria de conformidade recomendou
explicitamente não subir com a flag ligada.

Enquanto esse caminho existir, o padrão tem de ser **desligado**. Um default é
exatamente o tipo de coisa que volta sozinha num merge distraído, e voltaria em
silêncio: nada estoura, o serviço sobe, e passa a emitir ciência que sabemos
estar errada.

Este arquivo some no tempo 3, junto com o caminho legado.
"""

from __future__ import annotations

from pathlib import Path

from ecosfera_ai.config.settings import Settings


def test_biology_enabled_is_off_by_default() -> None:
    """O padrão do código, sem ambiente nenhum interferindo."""
    assert Settings().biology_enabled is False, (
        "o caminho legado com fitness global voltou a rodar por padrão — "
        "ver ADR 0017 e a auditoria de conformidade (DEC-01)"
    )


def test_the_flag_still_works_when_asked_for() -> None:
    """Desligar por padrão não é remover: quem pedir explicitamente, recebe."""
    assert Settings(biology_enabled=True).biology_enabled is True


def test_the_emergent_biology_does_not_depend_on_the_flag() -> None:
    """A biologia do M3 roda no tick, sempre — a flag não a governa.

    É o que torna a contenção barata: desligar a flag não deixa o planeta sem
    vida, só sem o AG por era.
    """
    from ecosfera_ai.engines.composition import ENGINE_ORDER

    assert "evolution" in ENGINE_ORDER
    assert "ecology" in ENGINE_ORDER

    source = Path("src/ecosfera_ai/engines/composition.py").read_text(encoding="utf-8")
    assert "biology_enabled" not in source, (
        "a composição do tick passou a consultar a flag: a biologia emergente "
        "deixaria de ser o caminho único do world-state"
    )


def test_a_planet_still_grows_life_with_the_flag_off() -> None:
    """Contraprova viva: sem a flag, a vida do Engine continua acontecendo."""
    from ecosfera_ai.engines.bridge import snapshot_of
    from ecosfera_ai.engines.composition import build_planet_engine
    from ecosfera_ai.simulation_engine.params import initial_state, load_params
    from ecosfera_ai.simulation_engine.state import PlanetSeed

    assert Settings().biology_enabled is False

    params = load_params(Path("configs/simulation_params.yaml"))
    planet = build_planet_engine(params, budget=params.engine_budget)
    snapshot = snapshot_of(initial_state(PlanetSeed("flagoff", 2027), params))
    for _ in range(120):
        snapshot = planet.tick(snapshot, publish=False).snapshot

    assert snapshot.biota.biomass > 0.0, "desligar a flag apagou a vida do Engine"
    assert snapshot.ecology.producer_biomass > 0.0
