"""Vocabulário de evento que o CONSUMIDOR conhece — sem importar Engine algum.

A Spec §2 é dura quanto a isto: *"Consumidores só leem o Event Store"*. Um
consumidor que importasse `ecosfera_ai.engines.evolution.events` para saber o que
é `"SpeciationOccurred"` estaria acoplado ao Engine que emite, e não ao envelope
§4 que ele lê — e o `import-linter` o barra por isso.

## Por que a duplicação é DELIBERADA, e por que ela é segura

Repetir as constantes aqui é duplicação, e duplicação envelhece. A alternativa —
importar do Engine — troca a duplicação por acoplamento, que é a troca errada:
o vocabulário do envelope é CONTRATO entre a simulação e todos os consumidores
(Spec §4), e um contrato existe justamente para que os dois lados possam mudar
sozinhos. É a mesma escolha que `configs/event_observations.yaml` já fez para o
explicador de regras: ele conhece nomes de tipo e campos de `cause_detail`, e não
conhece Engine nenhum.

O que torna a duplicação segura é `test_consumer_vocabulary_matches_engines`: o
TESTE importa os dois lados e exige igualdade termo a termo. Se um Engine
renomear `SpeciesExtinct`, o teste falha e nomeia o que divergiu — em vez de o
Tutor emudecer em silêncio sobre extinções, que é como esta classe de defeito se
manifestaria em produção.
"""

from __future__ import annotations

from collections.abc import Iterable

# --- Tipos de evento que este consumidor sabe ler ----------------------------

LIFE_EMERGED = "LifeEmerged"
SPECIATION_OCCURRED = "SpeciationOccurred"
SPECIES_EXTINCT = "SpeciesExtinct"
MASS_MORTALITY = "MassMortality"
TROPHIC_COLLAPSE = "TrophicCollapse"
POPULATION_DECLINED = "PopulationDeclined"
METEOR_IMPACT = "MeteorImpact"
SUPERVOLCANIC_ERUPTION = "SupervolcanicEruption"
ICE_AGE_ONSET = "IceAgeOnset"

# --- Papéis de participante de uma especiação (envelope §4, `participants`) ---
#
# São PAPÉIS, não identidades de espécie: o modelo é de comunidade, e a camada
# de espécies com identidade é pós-M6 (ADR 0024). Ver `SpeciationFact`.
ANCESTOR_ROLE = "ancestor"
LINEAGE_ROLE = "lineage"

# --- Campos de `cause_detail` que o dossiê promove a fato estruturado ---------

ANCESTOR_LINEAGE_FIELD = "ancestor_lineage_id"
LINEAGE_A_FIELD = "lineage_a_id"
LINEAGE_B_FIELD = "lineage_b_id"
GENETIC_DISTANCE_FIELD = "distance"

# --- A fronteira que o M4 pagou caro para existir (ADR 0019) ------------------
#
# `CATASTROPHIC_EVENT` é a ÚNICA causa de extinção independente de aptidão: um
# meteoro mata quem estava embaixo, e uma comunidade exemplarmente adaptada morre
# igual. Todas as outras causas de extinção são ECOLÓGICAS — a comunidade não se
# sustentou nas condições que encontrou.
#
# O dossiê preserva a distinção como DADO (`ExtinctionNature`) para que o
# consumidor de cima possa traduzi-la. Colapsá-la aqui faria o Tutor narrar toda
# extinção como falha de adaptação, que é exatamente a concepção equivocada que a
# plataforma existe para desfazer.
CATASTROPHIC_CAUSE_CODE = "CATASTROPHIC_EVENT"

# --- Marcos de era e transições notáveis --------------------------------------
#
# O que merece virar marcador do dossiê: o surgimento da vida, as mudanças de
# linhagem, os colapsos e as ocorrências extraordinárias. Não é "os eventos
# importantes" no sentido pedagógico — essa é decisão do consumidor de cima. É a
# lista dos tipos que mudam o ESTADO QUALITATIVO do planeta, e por isso servem de
# âncora temporal para qualquer narrativa que venha depois.
NOTABLE_TRANSITIONS: frozenset[str] = frozenset(
    {
        LIFE_EMERGED,
        SPECIATION_OCCURRED,
        SPECIES_EXTINCT,
        MASS_MORTALITY,
        TROPHIC_COLLAPSE,
        METEOR_IMPACT,
        SUPERVOLCANIC_ERUPTION,
        ICE_AGE_ONSET,
    }
)


def roles_in(participants: Iterable[str], role: str) -> tuple[str, ...]:
    """Extrai os participantes de um papel, pelo prefixo `papel:identidade`.

    É como um consumidor lê `participants` sem conhecer o Engine que o escreveu:
    o prefixo é parte do envelope, não da implementação de quem emitiu.
    """
    prefix = f"{role}:"
    return tuple(p.removeprefix(prefix) for p in participants if p.startswith(prefix))
