"""O envelope de `SpeciationOccurred` é BIT-A-BIT reproduzível pela semente.

## Por que este arquivo existe, e o que ele corrige

`test_determinism_after_envelope_change` afirma que a trilha replaya "envelope a
envelope". A afirmação é verdadeira e **não cobre a especiação**: a corrida de
200 ticks daquele arquivo emite ZERO `SpeciationOccurred` (medido: 39 eventos na
semente 2027, 76 na 99, nenhum de especiação). Com o limiar de produção o evento
exige ~6 σ num único passo — é a dívida declarada do BIO-002, registrada no
ADR 0023 e em `docs/decisions/deferred.md`.

Ou seja: aquele teste comparava duas trilhas que **não continham** o envelope que
a Fase 0 mudou. Passava, e teria continuado passando com o `cause_detail` da
especiação inteiramente quebrado. É a armadilha dos dois envelopes vazios —
iguais entre si e vazios de conteúdo.

Aqui o cenário é DECLARADO (limiar baixado por parâmetro, produção intocada,
mesma técnica de `build_volcanic_planet`), o evento de fato acontece, e a
comparação é campo a campo — para que uma divergência futura aponte QUAL campo
quebrou, e não apenas que "os eventos diferem".

## As duas metades

Um teste que compara duas execuções da mesma semente pode passar porque nada
aconteceu nas duas. Por isso o arquivo tem duas metades e as duas são
obrigatórias:

* **igualdade** — mesma semente reproduz o envelope inteiro;
* **contraprova** — semente diferente produz envelope diferente, e nos campos
  que a Fase 0 introduziu. Sem ela, um envelope congelado (ou vazio) passaria na
  primeira metade.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from tests.support import community_genome, speciation_event, speciation_snapshot

from ecosfera_ai.engines.evolution.events import (
    ANCESTOR_ROLE,
    LINEAGE_ROLE,
    SPECIATION_CAUSES,
)
from ecosfera_ai.shared_kernel.events import DomainEvent

TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")

# Os campos do envelope §4, um a um. Comparar `event_a == event_b` cru passaria
# no teste e falharia no diagnóstico: a mensagem diria "os eventos diferem" e o
# próximo a investigar teria de descobrir sozinho onde.
ENVELOPE_FIELDS = (
    "event_id",
    "event_type",
    "engine_id",
    "seed",
    "cause_code",
    "correlation_id",
    "causation_id",
    "location",
    "participants",
    "genes",
    "resources",
    "consequences",
    "granularity",
)

# As chaves que a Fase 0 acrescentou ao `cause_detail` (BIO-001).
LINEAGE_KEYS = ("ancestor_lineage_id", "lineage_a_id", "lineage_b_id")
GENE_KEYS = tuple(
    f"{prefix}_gene_{trait}"
    for prefix in ("ancestor", "lineage_a", "lineage_b")
    for trait in TRAITS
)


def _replay(seed: int = 2027) -> DomainEvent:
    """Uma corrida completa, semeada, até a especiação de fato ocorrer."""
    return speciation_event(speciation_snapshot(community_genome(temp_optimum=26.0), seed=seed))


def _field(event: DomainEvent, name: str) -> Any:
    return getattr(event, name)


def _detail(event: DomainEvent) -> Mapping[str, Any]:
    return dict(event.cause_detail)


# --- O cenário não é vazio ----------------------------------------------------
#
# Vem PRIMEIRO de propósito: se o evento comparado adiante estiver vazio, os
# testes de igualdade passam sem afirmar nada. Esta é a trava.


def test_the_replayed_event_really_is_a_speciation_with_content() -> None:
    event = _replay()
    assert event.event_type == "SpeciationOccurred"
    assert event.cause_code in SPECIATION_CAUSES
    assert len([p for p in event.participants if p.startswith(f"{ANCESTOR_ROLE}:")]) == 1
    assert len([p for p in event.participants if p.startswith(f"{LINEAGE_ROLE}:")]) == 2

    detail = _detail(event)
    for key in (*LINEAGE_KEYS, *GENE_KEYS, "distance", "biomass"):
        assert key in detail, f"o envelope comparado não carrega {key!r} — o teste seria vazio"
    assert float(detail["distance"]) > 0.0


# --- Metade 1: a mesma semente reproduz o envelope inteiro ---------------------


@pytest.mark.parametrize("field", ENVELOPE_FIELDS)
def test_each_envelope_field_replays_under_the_same_seed(field: str) -> None:
    one, two = _replay(), _replay()
    assert _field(one, field) == _field(two, field), (
        f"o campo `{field}` do envelope de especiação não replaya sob a mesma semente"
    )


def test_the_instant_of_the_speciation_replays() -> None:
    one, two = _replay(), _replay()
    assert (one.occurred_at.tick, one.occurred_at.era) == (
        two.occurred_at.tick,
        two.occurred_at.era,
    )


@pytest.mark.parametrize("key", LINEAGE_KEYS)
def test_each_lineage_identity_replays_under_the_same_seed(key: str) -> None:
    """Um `uuid4()` aqui quebraria o replay sem que nada estourasse."""
    assert _detail(_replay())[key] == _detail(_replay())[key]


@pytest.mark.parametrize("key", GENE_KEYS)
def test_each_genome_trait_of_the_three_replays_under_the_same_seed(key: str) -> None:
    """Os genomas vêm da mutação, que é semeada — traço a traço."""
    assert _detail(_replay())[key] == _detail(_replay())[key]


def test_the_cause_detail_has_no_extra_or_missing_key_between_runs() -> None:
    """Comparar valores não pega uma chave que apareça só numa das corridas."""
    assert set(_detail(_replay())) == set(_detail(_replay()))


# --- Metade 2: a CONTRAPROVA --------------------------------------------------
#
# Sem esta metade, os testes acima passariam com um envelope congelado, ou com
# dois envelopes vazios. O que se exige aqui é que o envelope DEPENDA da semente.


def test_a_different_seed_produces_a_different_envelope() -> None:
    """A trava contra o teste decorativo: trocar a semente TEM de mudar o evento."""
    one, other = _replay(seed=2027), _replay(seed=99)
    assert one != other, (
        "trocar a semente não mudou o envelope de especiação: os testes de "
        "igualdade acima não estão afirmando determinismo, estão comparando "
        "duas cópias de algo constante"
    )


@pytest.mark.parametrize("key", LINEAGE_KEYS)
def test_a_different_seed_produces_different_lineage_identities(key: str) -> None:
    """As três identidades derivam da semente — nenhuma pode ser constante."""
    assert _detail(_replay(seed=2027))[key] != _detail(_replay(seed=99))[key], (
        f"{key} é o mesmo em sementes diferentes: a identidade não deriva da semente"
    )


def test_a_different_seed_produces_a_different_event_id() -> None:
    assert _replay(seed=2027).event_id != _replay(seed=99).event_id


def test_a_different_seed_moves_the_divergent_lineage() -> None:
    """A mutação é semeada: a linhagem divergente não pode sair igual.

    Só a B: a A segue com os traços ancestrais, que são do cenário e não do
    sorteio — exigir que ELA mudasse seria exigir a coisa errada.
    """
    one, other = _detail(_replay(seed=2027)), _detail(_replay(seed=99))
    diverged = [key for key in GENE_KEYS if key.startswith("lineage_b_") and one[key] != other[key]]
    assert diverged, "a linhagem divergente é idêntica em sementes diferentes"
