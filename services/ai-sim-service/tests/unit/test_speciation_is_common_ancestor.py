"""BIO-001 — a especiação é ANCESTRAL COMUM, nunca "a espécie A gerou a B".

O requisito P0 da Fase 0 e o único que, sozinho, bloqueia o M6: o Tutor narra a
ciência da simulação, e uma ancestralidade errada no evento vira ancestralidade
errada ensinada com autoridade.

O que este arquivo afirma:

  1. o evento nomeia UM ancestral e DUAS linhagens, com papéis explícitos;
  2. o ancestral não é nenhuma das duas — é a população anterior à divisão;
  3. nada no evento nomeia uma espécie ATUAL como progenitora de outra;
  4. as identidades são derivadas (replay bit-a-bit), nunca sorteadas;
  5. o caminho legado, que de fato modela "A→B", continua dormente e fora da
     trilha (ADR 0017 tempo 1, ADR 0024).
"""

from __future__ import annotations

from pathlib import Path

from tests.support import (
    community_genome,
    speciation_event,
    speciation_snapshot,
)

from ecosfera_ai.engines.evolution.events import (
    ANCESTOR_ROLE,
    LINEAGE_ROLE,
    lineages_for,
)
from ecosfera_ai.shared_kernel.events import DomainEvent

TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")


def _roles(event: DomainEvent, role: str) -> list[str]:
    prefix = f"{role}:"
    return [p.removeprefix(prefix) for p in event.participants if p.startswith(prefix)]


# --- O evento nomeia um ancestral e duas linhagens -----------------------------


def test_the_event_names_one_ancestor_and_two_lineages() -> None:
    event = speciation_event()
    assert len(_roles(event, ANCESTOR_ROLE)) == 1, (
        f"a especiação registrou {_roles(event, ANCESTOR_ROLE)} ancestrais; "
        "o modelo de ancestral comum exige exatamente um"
    )
    assert len(_roles(event, LINEAGE_ROLE)) == 2, (
        "a especiação não registrou DUAS linhagens resultantes — sem as duas, "
        "o evento volta a descrever uma espécie virando outra"
    )


def test_the_ancestor_is_neither_of_the_two_lineages() -> None:
    """O ancestral é a população ANTERIOR à divisão, não uma das irmãs."""
    event = speciation_event()
    ancestor = _roles(event, ANCESTOR_ROLE)[0]
    lineages = _roles(event, LINEAGE_ROLE)
    assert ancestor not in lineages, (
        "o ancestral aparece também como linhagem resultante: isso é "
        "exatamente 'a espécie atual gerou a outra' com outro nome"
    )
    assert lineages[0] != lineages[1], "as duas linhagens são a mesma"


def test_the_three_identities_are_also_in_the_cause_detail() -> None:
    """O consumidor não precisa reparsear `participants` para achar os papéis."""
    event = speciation_event()
    detail = event.cause_detail
    assert detail["ancestor_lineage_id"] == _roles(event, ANCESTOR_ROLE)[0]
    assert [detail["lineage_a_id"], detail["lineage_b_id"]] == _roles(event, LINEAGE_ROLE)


def test_the_genome_of_the_ancestor_and_of_both_lineages_travels_with_the_event() -> None:
    """As três, explícitas: implícito obrigaria o consumidor a saber a regra."""
    event = speciation_event()
    for prefix in ("ancestor", "lineage_a", "lineage_b"):
        for trait in TRAITS:
            assert f"{prefix}_gene_{trait}" in event.cause_detail, (
                f"falta o traço {trait} de {prefix} no evento de especiação"
            )


def test_one_lineage_keeps_the_ancestral_traits_and_the_other_diverges() -> None:
    """A bifurcação é REAL: uma linhagem seguiu igual, a outra mudou."""
    detail = speciation_event().cause_detail
    ancestral = [detail[f"ancestor_gene_{t}"] for t in TRAITS]
    kept = [detail[f"lineage_a_gene_{t}"] for t in TRAITS]
    diverged = [detail[f"lineage_b_gene_{t}"] for t in TRAITS]

    assert kept == ancestral, "nenhuma das linhagens preservou os traços ancestrais"
    assert diverged != ancestral, "as duas linhagens são idênticas: não houve divisão"
    assert float(detail["distance"]) > 0.0


# --- A ancestralidade proibida não aparece em lugar nenhum ---------------------


def test_no_current_species_is_named_as_the_parent_of_another() -> None:
    """O vocabulário antigo (`species:community`) sai do evento de especiação.

    Ele nomeava UM sujeito só — a comunidade —, e um evento de divisão com um
    sujeito só só pode ser lido de um jeito: aquele sujeito produziu a novidade.
    """
    event = speciation_event()
    assert "species:community" not in event.participants
    for participant in event.participants:
        assert participant.split(":", 1)[0] in {ANCESTOR_ROLE, LINEAGE_ROLE}, (
            f"participante {participant!r} sem papel declarado na especiação"
        )


def test_the_prohibition_is_written_where_a_consumer_would_look() -> None:
    """A regra dura vale para as regras causais de hoje e para o Tutor do M6."""
    text = Path("src/ecosfera_ai/engines/evolution/events.py").read_text(encoding="utf-8")
    assert "ancestral comum" in text.lower()
    assert "irmãs" in text or "irmas" in text, (
        "o vocabulário de evento não diz que as duas linhagens são irmãs"
    )


def test_the_legacy_a_to_b_lineage_is_documented_as_superseded() -> None:
    """O códex do caminho B é a única ancestralidade "A→B" que restou no código.

    Ela não é reescrita aqui — reescrevê-la seria implementar a camada de
    espécies, que é pós-M6 (BIO-003/ADR 0024). O que a Fase 0 exige é que ela
    esteja MARCADA, para que ninguém a tome pelo modelo vigente.
    """
    codex = Path("src/ecosfera_ai/simulation_engine/biology/codex.py").read_text(encoding="utf-8")
    assert "BIO-001" in codex, "o códex legado não avisa que sua ancestralidade foi superada"

    legacy = Path("src/ecosfera_ai/simulation_engine/biology/evolution.py").read_text(
        encoding="utf-8"
    )
    assert "BIO-001" in legacy, "a escolha de ancestral entre espécies VIVAS segue sem aviso"


# --- Identidades determinísticas ----------------------------------------------


def test_the_lineage_identities_are_derived_not_drawn() -> None:
    """Um `uuid4()` aqui quebraria o replay tanto quanto quebraria no envelope."""
    one = lineages_for(2027, 0, 7)
    two = lineages_for(2027, 0, 7)
    assert (one.ancestor, one.first, one.second) == (two.ancestor, two.first, two.second)

    other_tick = lineages_for(2027, 0, 8)
    assert other_tick.ancestor != one.ancestor, "instantes distintos colidiram"

    other_seed = lineages_for(99, 0, 7)
    assert other_seed.ancestor != one.ancestor, "sementes distintas colidiram"


def test_the_three_roles_never_collide_with_each_other() -> None:
    lineages = lineages_for(2027, 0, 7)
    assert len({lineages.ancestor, lineages.first, lineages.second}) == 3


def test_the_same_scenario_produces_the_same_event_twice() -> None:
    """Determinismo do cenário inteiro, e não só do derivador de identidades."""
    world = speciation_snapshot(community_genome(temp_optimum=26.0))
    first = speciation_event(world)
    second = speciation_event(world)
    assert first == second
