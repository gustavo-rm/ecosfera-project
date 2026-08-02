"""O legado saiu de vez — e é isto que impede que ele volte por descuido.

O M2 aposentou o `LegacySubsystemAdapter`, os seis subsistemas migrados e a flag
`ECOSFERA_ENGINES_FRAMEWORK` (ADR 0014). Sem um teste, "removido" é um estado que
dura até o primeiro merge distraído: bastaria alguém reintroduzir um módulo, ou
um import sobreviver num arquivo esquecido, para que o serviço voltasse a ter
dois caminhos de simulação — um deles com a ciência anterior ao M1.

**A remoção da flag custou o rollback, e isso foi deliberado** (ADR 0014). A rede
que permanece é o replay determinístico: reproduzir uma trajetória gravada
continua possível, e é essa a reversibilidade de que a auditoria depende.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from ecosfera_ai.config.settings import Settings
from ecosfera_ai.engines.composition import ENGINE_ORDER, build_planet_engine
from ecosfera_ai.interfaces.http.deps import get_orchestrator
from ecosfera_ai.shared_kernel.world_state import SliceRef
from ecosfera_ai.simulation_engine.params import load_params

PARAMS = load_params(Path("configs/simulation_params.yaml"))
SERVICE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = SERVICE_ROOT / "src" / "ecosfera_ai"

GONE_MODULES = (
    "ecosfera_ai.engines.legacy",
    "ecosfera_ai.engines.legacy.adapter",
    "ecosfera_ai.engines.legacy.bridge",
    "ecosfera_ai.engines.legacy.orchestrator",
    "ecosfera_ai.simulation_engine.subsystems",
    "ecosfera_ai.simulation_engine.subsystems.physics",
    "ecosfera_ai.simulation_engine.subsystems.chemistry",
    "ecosfera_ai.simulation_engine.subsystems.climate",
    "ecosfera_ai.simulation_engine.subsystems.geology",
    "ecosfera_ai.simulation_engine.subsystems.ocean",
    "ecosfera_ai.simulation_engine.subsystems.life",
)


@pytest.mark.parametrize("module", GONE_MODULES)
def test_the_legacy_modules_no_longer_exist(module: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_no_source_file_still_imports_the_legacy() -> None:
    """Um import sobrevivente reintroduziria o caminho antigo pela porta lateral."""
    offenders: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                if any(module == gone or module.startswith(f"{gone}.") for gone in GONE_MODULES):
                    offenders.append(f"{path.relative_to(SOURCE_ROOT)}: {module}")
    assert not offenders, f"o legado voltou por import: {offenders}"


def test_the_framework_flag_is_gone_from_settings() -> None:
    """A flag não existe mais: não há um segundo motor para ela escolher.

    Definir `ECOSFERA_ENGINES_FRAMEWORK` no ambiente hoje é inócuo — e é melhor
    assim do que uma flag que finge oferecer uma escolha já inexistente.
    """
    assert not hasattr(Settings(), "engines_framework")
    assert "engines_framework" not in Settings.model_fields


def test_the_composition_root_has_a_single_simulation_path() -> None:
    """Uma rota de tick, sem ramo condicional (ADR 0014)."""
    from ecosfera_ai.engines.composition import FrameworkTickOrchestrator

    get_orchestrator.cache_clear()
    ticker = get_orchestrator()
    assert isinstance(ticker, FrameworkTickOrchestrator)
    assert ticker.subsystem_names == ENGINE_ORDER
    get_orchestrator.cache_clear()


def test_every_slice_has_an_engine_owner() -> None:
    """Não sobrou fatia transitória: a `LegacySlice` deixou de existir."""
    assert not hasattr(SliceRef, "LEGACY")
    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    assert set(planet.registry.owned_slices) == set(SliceRef)
    assert len(ENGINE_ORDER) == len(SliceRef)


def test_replay_is_the_reversibility_that_survived() -> None:
    """O rollback foi embora; reproduzir o passado, não.

    Perder a flag significa que não há como rodar a ciência anterior ao M1. O que
    a auditoria de fato precisa — recompor uma trajetória gravada a partir da
    semente — continua valendo, e é o que este teste amarra (ADR 0014).
    """
    from ecosfera_ai.engines.bridge import snapshot_of
    from ecosfera_ai.shared_kernel.replay import verify_replay
    from ecosfera_ai.simulation_engine.params import initial_state
    from ecosfera_ai.simulation_engine.state import PlanetSeed

    planet = build_planet_engine(PARAMS, budget=PARAMS.engine_budget)
    seed = 4242
    start = snapshot_of(initial_state(PlanetSeed("rollback", seed), PARAMS))

    # Primeira execução: é ela que produz a trilha "gravada".
    recorded = verify_replay(seed, start, [], stepper=planet.stepper(), until_tick=25)

    # Reconstrução: mesma semente, mesmo checkpoint, mesmo motor.
    rebuilt = verify_replay(
        seed,
        start,
        recorded.events,
        stepper=planet.stepper(),
        until_tick=25,
        expected=recorded.snapshot,
    )
    assert rebuilt.deterministic, "o replay deixou de ser função da semente"
    assert rebuilt.snapshot == recorded.snapshot
