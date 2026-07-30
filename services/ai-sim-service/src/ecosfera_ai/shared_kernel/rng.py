"""Fábrica determinística de RNG por (semente, engine, tick) — RF-023.

Cada Engine recebe do Planet Engine um `numpy.random.Generator` derivado da
tripla (semente do planeta, `engine_id`, tick). Consequências desejadas:

* **Reprodutível:** a mesma tripla devolve sempre a mesma sequência.
* **Independente:** dois Engines no mesmo tick não compartilham fluxo, então
  acrescentar, remover ou reordenar um Engine não desloca os sorteios dos
  outros — o que tornaria o replay de eras antigas irreprodutível.
* **Sem estado global:** `random.seed()` do módulo `random` é estado de
  processo; qualquer biblioteca que sorteie no meio do tick contaminaria o
  resultado. Engines usam SÓ o gerador recebido.
"""

from __future__ import annotations

import hashlib

import numpy as np

# Tamanho do resumo do engine_id em bytes. 8 bytes (64 bits) tornam colisão
# entre nomes de Engine irrelevante na prática, e cabem numa entrada de
# SeedSequence sem truncamento.
_DIGEST_BYTES = 8


def engine_entropy(engine_id: str) -> int:
    """Converte o nome do Engine em entropia ESTÁVEL entre processos.

    `hash()` do Python é aleatorizado por processo (PYTHONHASHSEED), portanto
    inutilizável aqui: a mesma semente daria trajetórias diferentes a cada
    execução. BLAKE2b é determinístico e independente de plataforma.
    """
    digest = hashlib.blake2b(engine_id.encode("utf-8"), digest_size=_DIGEST_BYTES).digest()
    return int.from_bytes(digest, "big")


def seed_sequence_for(seed: int, engine_id: str, tick: int) -> np.random.SeedSequence:
    """Sequência de semente do par (Engine, tick) sob a semente do planeta."""
    return np.random.SeedSequence([seed, tick, engine_entropy(engine_id)])


def rng_for(seed: int, engine_id: str, tick: int) -> np.random.Generator:
    """Gerador semeado que o Planet Engine entrega ao Engine no `TickContext`."""
    return np.random.default_rng(seed_sequence_for(seed, engine_id, tick))
