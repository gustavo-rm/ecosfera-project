"""RNG semeado por (semente, engine, tick) — RF-023."""

from __future__ import annotations

import subprocess
import sys

from ecosfera_ai.shared_kernel.rng import engine_entropy, rng_for


def _draws(seed: int, engine_id: str, tick: int, n: int = 5) -> list[float]:
    return [float(x) for x in rng_for(seed, engine_id, tick).random(n)]


def test_same_triple_gives_the_same_sequence() -> None:
    assert _draws(2027, "climate", 10) == _draws(2027, "climate", 10)


def test_different_seeds_diverge() -> None:
    assert _draws(1, "climate", 10) != _draws(2, "climate", 10)


def test_different_engines_diverge_within_the_same_tick() -> None:
    """Fluxos independentes: acrescentar um Engine não desloca os sorteios dos outros."""
    assert _draws(7, "climate", 3) != _draws(7, "geology", 3)


def test_different_ticks_diverge_for_the_same_engine() -> None:
    assert _draws(7, "climate", 3) != _draws(7, "climate", 4)


def test_engine_entropy_is_stable_across_processes() -> None:
    """`hash()` é aleatorizado por processo; a entropia do Engine não pode ser.

    O subprocesso roda com um PYTHONHASHSEED diferente de propósito: se a
    derivação dependesse de `hash()`, a mesma semente daria trajetórias
    diferentes a cada execução do serviço.
    """
    local = engine_entropy("climate")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ecosfera_ai.shared_kernel.rng import engine_entropy;"
            " print(engine_entropy('climate'))",
        ],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONHASHSEED": "12345", "PATH": "/usr/bin:/bin", "PYTHONPATH": "src"},
    )
    assert int(result.stdout.strip()) == local


def test_generator_is_isolated_from_the_global_random_module() -> None:
    """Um Engine não pode ser afetado por quem chamou `random.seed()` antes."""
    import random

    random.seed(1)
    first = _draws(5, "life", 1)
    random.seed(999)
    assert _draws(5, "life", 1) == first
