"""No dossiê, especiação é ancestral comum — e "A deu origem a B" é INEXPRIMÍVEL.

A Fase 0 corrigiu o significado do evento (BIO-001) antes de o Tutor existir, e a
razão está registrada: no modelo "A→B" a espécie que continua existindo aparece
como progenitora da outra, o que reintroduz a escada de progresso que a plataforma
existe para desfazer — o aluno conclui que B é "mais evoluída" que A.

`test_factual_context_common_ancestor.py` já guarda a leitura do explicador de
regras. Este arquivo guarda o ANDAR DE BAIXO: a estrutura de dados que o M6.1 e o
M6.3 vão receber. A diferença importa, porque uma frase errada se corrige
reescrevendo um template, e um dossiê errado corrompe tudo o que vier depois —
inclusive um LLM que se comporte perfeitamente sobre a entrada que recebeu.

A garantia aqui não é de redação: é de TIPO. `SpeciationFact` não consegue
representar uma progenitora viva.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from tests.support import speciation_event

from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    FactualContext,
    MalformedSpeciationError,
    SpeciationFact,
)
from ecosfera_ai.domain.consumers.vocabulary import (
    ANCESTOR_ROLE,
    LINEAGE_ROLE,
    SPECIATION_OCCURRED,
    roles_in,
)


def _context_with_speciation() -> FactualContext:
    event = speciation_event()
    return FactualContext.of("planet-bio", ContextSlice.of_era(event.occurred_at.era), (event,))


# --- O fato tem a forma da divisão -------------------------------------------


def test_the_dossier_records_one_ancestor_and_two_lineages() -> None:
    fact = _context_with_speciation().speciations[0]
    assert fact.ancestor
    assert len(fact.lineages) == 2
    assert len(set(fact.lineages)) == 2


def test_the_ancestor_is_neither_of_the_two_lineages() -> None:
    """Uma divisão não deixa progenitora viva: as duas que seguem são IRMÃS."""
    fact = _context_with_speciation().speciations[0]
    assert fact.ancestor not in fact.lineages


def test_the_cause_of_the_split_survives_into_the_dossier() -> None:
    """Uma especiação sem causa vira, na boca de quem narra, especiação por acaso.

    Ou pior: especiação porque a espécie "precisava" de uma nova. A causa está no
    envelope desde a Fase 0 (BIO-002) e o dossiê a carrega adiante.
    """
    fact = _context_with_speciation().speciations[0]
    assert fact.cause_code
    assert fact.cause_code != "GENETIC_DIVERGENCE", (
        "a causa superada nomeia o CRITÉRIO da divergência, não o motivo dela"
    )


# --- O modelo A→B é INEXPRIMÍVEL, e não apenas desencorajado ------------------


def test_a_speciation_with_a_single_lineage_is_refused() -> None:
    """ "A espécie A gerou a espécie B" tem UMA linhagem resultante. Recusado."""
    with pytest.raises(MalformedSpeciationError, match="duas"):
        SpeciationFact(
            event_id="evt-a-to-b",
            occurred_at=speciation_event().occurred_at,
            cause_code="DIVERGENT_NICHE",
            ancestor="especie-A",
            lineages=("especie-B",),
        )


def test_a_speciation_whose_ancestor_survives_as_a_lineage_is_refused() -> None:
    """A forma mais sutil do erro: o ancestral REAPARECE como uma das linhagens.

    É assim que "A→B" se disfarça de ancestral comum — ancestral A, linhagens A e
    B. A estrutura passa a contar que A continua vivo e gerou B, que é exatamente
    a leitura proibida.
    """
    with pytest.raises(MalformedSpeciationError, match="ancestral"):
        SpeciationFact(
            event_id="evt-disguised",
            occurred_at=speciation_event().occurred_at,
            cause_code="DIVERGENT_NICHE",
            ancestor="especie-A",
            lineages=("especie-A", "especie-B"),
        )


def test_a_malformed_speciation_fails_loudly_instead_of_being_skipped() -> None:
    """Falhar é melhor que pular: um evento pulado emudece o Tutor em silêncio."""
    broken = speciation_event()
    stripped = type(broken)(
        event_id=broken.event_id,
        event_type=SPECIATION_OCCURRED,
        engine_id=broken.engine_id,
        occurred_at=broken.occurred_at,
        seed=broken.seed,
        cause_code=broken.cause_code,
        correlation_id=broken.correlation_id,
        participants=(f"{ANCESTOR_ROLE}:x", f"{LINEAGE_ROLE}:y"),
        cause_detail={},
    )
    with pytest.raises(MalformedSpeciationError):
        FactualContext.of("planet-bio", ContextSlice.of_era(1), (stripped,))


# --- A leitura não conhece o Engine ------------------------------------------


def test_the_roles_are_read_from_the_envelope_and_not_from_the_engine() -> None:
    """O consumidor lê `participants` pelo prefixo do papel, como manda a Spec §4."""
    event = speciation_event()
    assert len(roles_in(event.participants, ANCESTOR_ROLE)) == 1
    assert len(roles_in(event.participants, LINEAGE_ROLE)) == 2


def test_the_lineages_are_identifiers_and_not_species_names() -> None:
    """Grão de COMUNIDADE (ADR 0024): identidade de espécie é camada pós-M6.

    Inventar nomes de espécie aqui anteciparia por baixo do pano uma camada que a
    simulação não sustenta — o Evolution modela um genoma médio, e
    `species_richness` é um float, não um conjunto de identidades.
    """
    fact = _context_with_speciation().speciations[0]
    for lineage in (fact.ancestor, *fact.lineages):
        assert "-" in lineage and lineage.islower(), (
            f"{lineage!r} parece nome de espécie; o modelo atual só tem linhagens"
        )


def test_a_split_into_two_identical_lineages_is_refused() -> None:
    """Duas linhagens iguais não são uma divisão — são a mesma população contada duas vezes."""
    with pytest.raises(MalformedSpeciationError, match="idênticas"):
        SpeciationFact(
            event_id="evt-not-a-split",
            occurred_at=speciation_event().occurred_at,
            cause_code="DIVERGENT_NICHE",
            ancestor="linhagem-mae",
            lineages=("linhagem-x", "linhagem-x"),
        )


def test_more_than_one_ancestor_is_refused() -> None:
    """Uma divisão tem UM ancestral comum. Dois seriam uma fusão, que não existe aqui."""
    broken = speciation_event()
    two_ancestors = replace(
        broken,
        participants=(
            f"{ANCESTOR_ROLE}:a",
            f"{ANCESTOR_ROLE}:b",
            f"{LINEAGE_ROLE}:x",
            f"{LINEAGE_ROLE}:y",
        ),
    )
    with pytest.raises(MalformedSpeciationError, match="ancestrais"):
        SpeciationFact.from_event(two_ancestors)


def test_the_reader_falls_back_to_cause_detail_when_the_roles_are_absent() -> None:
    """Os dois caminhos do envelope dizem a mesma coisa, e o segundo é rede.

    `participants` é o campo comum e é por onde se lê. Mas os três ids também
    viajam em `cause_detail`, e uma trilha antiga (ou um Engine que ainda não
    escreva os papéis) continua legível sem que o dossiê invente nada — os dados
    vêm do MESMO evento, só de outro campo dele.
    """
    complete = SpeciationFact.from_event(speciation_event())
    without_roles = SpeciationFact.from_event(replace(speciation_event(), participants=()))
    assert without_roles == complete


def test_the_genetic_distance_travels_when_the_event_carries_it() -> None:
    """O número que sustenta a frase, e não a frase (Spec §4, `cause_detail`)."""
    fact = SpeciationFact.from_event(speciation_event())
    assert fact.genetic_distance is not None
    assert fact.to_dict()["genetic_distance"] == fact.genetic_distance
