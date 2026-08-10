"""O round-trip preserva a especiação — e o que "round-trip" significa aqui.

## A distinção que este arquivo precisa fazer antes de afirmar qualquer coisa

O **snapshot de world-state NÃO carrega eventos**, e isso é desenho, não lacuna:
`StateDelta.values` é `Mapping[str, float]` e aditivo, e o ADR 0006 mantém a
composição por espécie fora do world-state de propósito — é o que faz a física
ser bit-idêntica com a biologia ligada ou desligada. A composição viaja pelo
**Canal B** (ADR 0016 §2). Procurar o envelope de especiação dentro de
`WorldStateSnapshot` seria procurá-lo onde ele nunca esteve.

Então o round-trip se parte em dois, e os dois são verificados aqui:

* **Canal A — o snapshot.** O que a especiação deixa no world-state é o efeito
  agregado: `species_richness` sobe, o genoma médio se desloca. É isso que tem de
  sobreviver a `PlanetState ↔ WorldStateSnapshot`.
* **Canal B — o artefato portável.** `SimulationExport` é o que de fato carrega a
  trilha entre máquinas (M5, ADR 0021). É ali que o envelope inteiro — ancestral,
  duas linhagens e os três genomas — tem de atravessar a ida e a volta.

Afirmar só o primeiro e chamar de "o envelope sobrevive ao round-trip" seria a
mesma família de afirmação-sem-prova que esta auditoria veio fechar.
"""

from __future__ import annotations

from pathlib import Path

from tests.support import community_genome, speciation_event, speciation_snapshot

from ecosfera_ai.engines.bridge import planet_state_of, snapshot_of
from ecosfera_ai.engines.evolution.events import ANCESTOR_ROLE, LINEAGE_ROLE
from ecosfera_ai.shared_kernel.portable import EXPORT_FORMAT_VERSION, SimulationExport
from ecosfera_ai.shared_kernel.world_state import WORLD_STATE_VERSION
from ecosfera_ai.simulation_engine.params import load_params

PARAMS = load_params(Path("configs/simulation_params.yaml"))
TRAITS = ("temp_optimum", "temp_tolerance", "water_need", "size", "metabolism", "trophic_level")
GENE_KEYS = tuple(
    f"{prefix}_gene_{trait}"
    for prefix in ("ancestor", "lineage_a", "lineage_b")
    for trait in TRAITS
)


def _artefact() -> tuple[SimulationExport, object]:
    """Um artefato portável com uma especiação de verdade na trilha."""
    world = speciation_snapshot(community_genome(temp_optimum=26.0))
    event = speciation_event(world)
    export = SimulationExport(
        planet_id=world.planet_id,
        seed=world.seed,
        world_state_version=WORLD_STATE_VERSION,
        params_version=PARAMS.version,
        format_version=EXPORT_FORMAT_VERSION,
        checkpoints={"0": planet_state_of(world).to_dict()},
        events=SimulationExport.encode_events([event]),
    )
    return export, event


# --- Canal A: o efeito agregado sobrevive ao snapshot --------------------------


def test_the_biota_slice_survives_the_state_snapshot_round_trip() -> None:
    """O que a especiação deixa no world-state é o agregado — e ele volta inteiro."""
    world = speciation_snapshot(community_genome(temp_optimum=26.0))
    restored = snapshot_of(planet_state_of(world))

    assert restored.biota.species_richness == world.biota.species_richness
    assert restored.biota.biomass == world.biota.biomass
    for trait in TRAITS:
        assert getattr(restored.biota, f"mean_{trait}") == getattr(world.biota, f"mean_{trait}"), (
            f"o traço médio {trait} não sobreviveu ao round-trip do world-state"
        )


def test_the_snapshot_carries_no_event_and_that_is_by_design() -> None:
    """Trava contra a leitura errada deste arquivo.

    Se um dia o world-state passar a carregar eventos, esta asserção quebra — e
    quem a quebrar vai ler o porquê antes de "consertar" o teste.
    """
    world = speciation_snapshot(community_genome(temp_optimum=26.0))
    fields = set(type(world).__dataclass_fields__)
    assert "events" not in fields, (
        "o world-state passou a carregar eventos: a fronteira Canal A × Canal B "
        "mudou, e o ADR 0006/0016 precisa ser revisitado antes deste teste"
    )


# --- Canal B: o envelope inteiro sobrevive ao artefato portável ----------------


def test_the_speciation_event_survives_the_portable_round_trip() -> None:
    export, original = _artefact()
    restored = SimulationExport.from_json(export.to_json()).domain_events()

    assert len(restored) == 1, "a trilha exportada perdeu a especiação"
    assert restored[0] == original


def test_the_three_roles_survive_the_portable_round_trip() -> None:
    export, original = _artefact()
    restored = SimulationExport.from_json(export.to_json()).domain_events()[0]

    assert restored.participants == original.participants
    assert len([p for p in restored.participants if p.startswith(f"{ANCESTOR_ROLE}:")]) == 1
    assert len([p for p in restored.participants if p.startswith(f"{LINEAGE_ROLE}:")]) == 2


def test_every_genome_trait_survives_the_portable_round_trip() -> None:
    """Sem `approx`: o artefato existe para reproduzir, e reproduzir é bit-a-bit."""
    export, original = _artefact()
    restored = SimulationExport.from_json(export.to_json()).domain_events()[0]

    for key in GENE_KEYS:
        assert restored.cause_detail[key] == original.cause_detail[key], (
            f"o traço {key} não atravessou o artefato portável intacto"
        )


def test_the_lineage_identities_survive_the_portable_round_trip() -> None:
    export, original = _artefact()
    restored = SimulationExport.from_json(export.to_json()).domain_events()[0]

    for key in ("ancestor_lineage_id", "lineage_a_id", "lineage_b_id"):
        assert restored.cause_detail[key] == original.cause_detail[key]


def test_the_cause_of_the_speciation_survives_the_portable_round_trip() -> None:
    """O `cause_code` desserializa por varredura de subclasses de `CauseCodeEnum`.

    As causas do BIO-002 são novas: se a varredura não as alcançasse,
    `event_from_dict` levantaria `UnknownCauseCodeError` — falha alta, que é o
    comportamento certo, mas que tornaria o artefato ilegível.
    """
    export, original = _artefact()
    restored = SimulationExport.from_json(export.to_json()).domain_events()[0]
    assert restored.cause_code is original.cause_code


def test_the_exported_artefact_is_byte_stable() -> None:
    """Duas exportações da mesma simulação dão o MESMO arquivo (M5, ADR 0021).

    Com 22 chaves no `cause_detail`, uma ordenação instável passaria a produzir
    artefatos que diferem por hash sem diferir por conteúdo — e a comparação por
    hash é justamente o que o export promete.
    """
    first, _ = _artefact()
    second, _ = _artefact()
    assert first.to_json() == second.to_json()
