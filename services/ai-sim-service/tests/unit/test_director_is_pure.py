"""O Diretor decide a partir do world-state e do RNG — de mais nada.

A tentação é evidente: "agendar uma seca porque o aluno vem prosperando há muitas
eras" pede o histórico. É exatamente o que a moldura proíbe — a observabilidade é
LATERAL e não realimenta a simulação (ADR-ARCH-0002). Um Diretor que lesse a
trilha tornaria o replay impossível a partir de `(seed, checkpoint)`, porque a
trilha é EFEITO da execução, não entrada dela.

Não há RL aqui, e a ausência é deliberada: um agente treinado seria estatal e
dependeria de histórico — as duas coisas que a pureza acima recusa.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from ecosfera_ai.engines.event.contracts import load_params
from ecosfera_ai.engines.event.director import Schedule, decide, plausible_kinds
from ecosfera_ai.engines.event.domain import EventKind
from ecosfera_ai.shared_kernel.world_state import ClimateSlice, WorldStateSnapshot

PARAMS = load_params()
_DIRECTOR = Path("src/ecosfera_ai/engines/event/director.py")

# Nomes cuja presença no Diretor indicaria realimentação ou aprendizado.
FORBIDDEN = (
    "observability",
    "EventStore",
    "event_store",
    "sink",
    "metrics",
    "prometheus",
    "logger",
    "structlog",
    "history",
    "reward",
    "policy",
    "train",
)


def _snapshot(**climate: float) -> WorldStateSnapshot:
    return WorldStateSnapshot(
        planet_id="director", seed=1, tick=0, era=0, climate=ClimateSlice(**climate)
    )


def test_the_director_imports_nothing_observational() -> None:
    """Auditoria estrutural: o módulo não alcança o Canal B nem a medição."""
    source = _DIRECTOR.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert "observability" not in name, f"o Diretor importa {name}"
            assert "events" not in name, f"o Diretor alcança o Canal B via {name}"


def test_no_feedback_vocabulary_survives_in_the_director() -> None:
    body = _DIRECTOR.read_text(encoding="utf-8")
    # Só o corpo executável: as docstrings EXPLICAM por que essas coisas não
    # entram, e proibir a palavra na explicação apagaria a explicação.
    code = "\n".join(line for line in body.splitlines() if not line.strip().startswith("#"))
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name | ast.Attribute):
            text = ast.unparse(node)
            for word in FORBIDDEN:
                assert word not in text, f"o Diretor referencia {word!r}"


def test_the_decision_is_a_function_of_snapshot_and_rng_only() -> None:
    """Mesmo estado + mesmo RNG => mesma decisão, sempre."""
    snapshot = _snapshot(temperature=18.0)
    a = decide(snapshot, np.random.default_rng(7), PARAMS, quiet=False)
    b = decide(snapshot, np.random.default_rng(7), PARAMS, quiet=False)
    assert a == b


def test_a_quiet_window_never_schedules() -> None:
    for seed in range(30):
        out = decide(_snapshot(temperature=18.0), np.random.default_rng(seed), PARAMS, quiet=True)
        assert out == Schedule(EventKind.NONE, 0, 0.0)


def test_context_rules_out_the_absurd_without_scripting_the_plot() -> None:
    """Era glacial num planeta fervendo é descartada — mas nada é ROTEIRIZADO.

    O Diretor não escolhe o evento "certo" para a lição: ele descarta o
    fisicamente incoerente e sorteia entre o que resta.
    """
    hot = plausible_kinds(_snapshot(temperature=40.0), PARAMS)
    cold = plausible_kinds(_snapshot(temperature=2.0), PARAMS)

    assert EventKind.ICE_AGE not in hot, "era glacial sorteada num planeta a 40 C"
    assert EventKind.ICE_AGE in cold
    assert EventKind.DROUGHT not in cold, "seca num mundo congelado não é o limitante"
    assert len(hot) > 1, "o contexto não pode reduzir o catálogo a um roteiro"


def test_the_candidate_order_is_stable() -> None:
    """Ordem instável faria o sorteio depender de iteração de dicionário."""
    snapshot = _snapshot(temperature=18.0)
    assert plausible_kinds(snapshot, PARAMS) == plausible_kinds(snapshot, PARAMS)
    assert plausible_kinds(snapshot, PARAMS) == sorted(plausible_kinds(snapshot, PARAMS), key=int)
