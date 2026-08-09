"""Vocabulário de evento do Evolution Engine (Canal B, envelope §4).

Os `cause_code` são enum e NUNCA prosa pedagógica: o Engine entrega o esqueleto
causal como dado, e a frase é do Tutor (ADR-ARCH-0002, Correção 1).

`THERMAL_INTOLERANCE` é o elo que fecha a cadeia ambiental→biológica: uma
`TemperatureShift` do Climate causa uma `SpeciesExtinct` com esta causa, e o
`causation_id` liga as duas sem que o Evolution conheça o Climate.

## Especiação é ANCESTRAL COMUM, e não "A originou B" (BIO-001, Fase 0)

Um evento de especiação registra **um ancestral** e **duas linhagens** que
passam a divergir a partir dele. Nunca "a espécie X (atual) gerou a espécie Y
(atual)": as duas linhagens que seguem adiante são IRMÃS, e o ancestral que se
dividiu é o que ambas compartilham — ele não é nenhuma das duas.

A diferença não é de redação. No modelo "A→B", a espécie que continua existindo
aparece como progenitora da outra, o que reintroduz a escada de progresso que a
plataforma existe para desfazer (o aluno conclui que B é "mais evoluída" que A, e
que A é uma versão antiga de B). No modelo de ancestral comum não há progenitora
viva: há uma população ancestral que se dividiu, e duas linhagens contemporâneas.

**Regra dura para todo consumidor destes eventos** (regras causais de hoje e
Tutor do M6): é proibido gerar texto que afirme que uma espécie deu origem a
outra. A forma correta é *"duas linhagens compartilham um ancestral comum que
sofreu especiação"*.

## Linguagem anti-teleológica (BIO-005)

Toda narração derivada destes códigos descreve mutação como **evento aleatório**
("surgiu uma mutação aleatória") e seleção como **consequência ambiental** ("a
característica aumentou a sobrevivência porque o ambiente era X"). Nenhuma
formulação de intenção — a espécie não desenvolve, não cria, não busca e não
persegue nada. `test_no_teleological_language` guarda a proibição.

## ADAPTAÇÃO não é ESPECIAÇÃO (PED-003)

São dois fenômenos distintos, e confundi-los reduz evolução a adaptação:

* **ADAPTAÇÃO** — mudança na FREQUÊNCIA dos traços dentro de UMA população ao
  longo do tempo. É o que `TraitShift` (`DIRECTIONAL_SELECTION`) registra: a
  comunidade continua sendo uma, com o traço médio deslocado.
* **ESPECIAÇÃO** — surgimento de uma NOVA LINHAGEM a partir de um ancestral
  comum. É o que `SpeciationOccurred` registra: onde havia uma linhagem, passam a
  existir duas, e o ancestral é de ambas.

Adaptação acumulada pode LEVAR à especiação, mas não É especiação: enquanto a
população não se divide, houve adaptação e nada mais.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecosfera_ai.shared_kernel.events import CauseCodeEnum, deterministic_id

LIFE_EMERGED = "LifeEmerged"
SPECIATION_OCCURRED = "SpeciationOccurred"
SPECIES_EXTINCT = "SpeciesExtinct"
TRAIT_SHIFT = "TraitShift"

# Mortandade em massa SEM extinção total. É o caso comum e faltava: a extinção
# só dispara quando a comunidade inteira cai abaixo do piso de viabilidade, o que
# quase nunca acontece. Um choque térmico que custa um quarto da biomassa não
# produzia evento algum — o diagnóstico de causa existia e era inalcançável.
#
# Para uma plataforma cujo produto é explicar POR QUÊ, "a comunidade perdeu 23%
# da biomassa porque o calor passou do que ela tolera" é justamente o evento que
# precisa existir (ADR 0016).
MASS_MORTALITY = "MassMortality"

# Papéis dos participantes de uma especiação (envelope §4, campo `participants`).
# São PAPÉIS, não nomes de espécie: o modelo de comunidade não tem identidades de
# espécie (ADR 0016), e inventá-las aqui seria antecipar a camada de espécies que
# a decisão de coortes deixou para depois do M6 (BIO-003).
ANCESTOR_ROLE = "ancestor"
LINEAGE_ROLE = "lineage"


class EvolutionCauseCode(CauseCodeEnum):
    """Causas estruturadas da evolução — código, nunca prosa."""

    HABITABILITY_THRESHOLD = "HABITABILITY_THRESHOLD"
    THERMAL_INTOLERANCE = "THERMAL_INTOLERANCE"
    RESOURCE_SCARCITY = "RESOURCE_SCARCITY"
    PREDATION_PRESSURE = "PREDATION_PRESSURE"
    DIRECTIONAL_SELECTION = "DIRECTIONAL_SELECTION"

    # CAUSAS DA ESPECIAÇÃO (BIO-002, parte pré-M6) ---------------------------
    #
    # A mecânica continua sendo divergência por limiar; o que a Fase 0 acrescenta
    # é a CAUSA que a disparou, para que a explicação não precise inventá-la.
    # Sem isso, o consumidor recebe "houve especiação" e nada mais — e uma
    # especiação sem causa vira, na boca de quem narra, especiação por acaso puro
    # ou, pior, especiação porque a espécie "precisava" de uma nova.
    #
    # Os nomes do Plano de Evolução aparecem aqui em inglês por consistência com
    # todo o vocabulário de `cause_code` do serviço. A correspondência é direta:
    # BARREIRA_GEOGRAFICA → GEOGRAPHIC_BARRIER; ISOLAMENTO_REPRODUTIVO →
    # REPRODUCTIVE_ISOLATION; NICHO_DIVERGENTE → DIVERGENT_NICHE;
    # PRESSAO_AMBIENTAL → ENVIRONMENTAL_PRESSURE.
    GEOGRAPHIC_BARRIER = "GEOGRAPHIC_BARRIER"
    REPRODUCTIVE_ISOLATION = "REPRODUCTIVE_ISOLATION"
    DIVERGENT_NICHE = "DIVERGENT_NICHE"
    ENVIRONMENTAL_PRESSURE = "ENVIRONMENTAL_PRESSURE"

    # SUPERADA pelas quatro acima (BIO-002). Nomeava o CRITÉRIO ("os genomas
    # ficaram distantes"), não a causa — e o critério é a régua, não o motivo.
    # Continua declarada porque `event_from_dict` recusa um `cause_code` que não
    # pertença a vocabulário algum: removê-la tornaria ilegível toda trilha já
    # gravada antes da Fase 0.
    GENETIC_DIVERGENCE = "GENETIC_DIVERGENCE"

    # CATASTRÓFICA — abrupta e INDEPENDENTE de aptidão (Q11/Q8, ADR 0019).
    #
    # As causas acima são ECOLÓGICAS: a comunidade não se sustentou nas condições
    # que encontrou, e o traço dela explica por quê — a aptidão CONTEXTUAL dela
    # àquele ambiente era baixa. Esta não é: um meteoro mata quem estava embaixo.
    # Uma espécie de aptidão contextual ALTA pode ser eliminada por ela, e é isso
    # que separa as duas famílias (Q5, Q8).
    #
    # Manter as duas famílias SEPARADAS é o ponto pedagógico do M4. Colapsá-las
    # numa só faria o Tutor narrar toda extinção como falha de adaptação, que é a
    # concepção equivocada que a plataforma existe para desfazer.
    CATASTROPHIC_EVENT = "CATASTROPHIC_EVENT"


# As causas que podem acompanhar uma `SpeciationOccurred`.
SPECIATION_CAUSES: frozenset[EvolutionCauseCode] = frozenset(
    {
        EvolutionCauseCode.GEOGRAPHIC_BARRIER,
        EvolutionCauseCode.REPRODUCTIVE_ISOLATION,
        EvolutionCauseCode.DIVERGENT_NICHE,
        EvolutionCauseCode.ENVIRONMENTAL_PRESSURE,
    }
)

# Códigos DECLARADOS que hoje ninguém emite, e a razão de cada um. O registro
# existe para que o buraco seja RUIDOSO: um código sem emissor é exatamente a
# família de furo silencioso que o M2 encontrou no `solar_flux` — o vocabulário
# anuncia uma explicação que a simulação nunca produz.
#
# * GEOGRAPHIC_BARRIER — o modelo não tem geografia. Toda `location` é
#   `region_id: global`, então não há barreira a detectar. Declarado porque é a
#   causa canônica de especiação alopátrica e o vocabulário do Tutor a exige;
#   ganha emissor quando existirem regiões (pós-M6).
# * GENETIC_DIVERGENCE — superada, mantida só para ler trilhas antigas.
CAUSES_WITHOUT_EMITTER: frozenset[EvolutionCauseCode] = frozenset(
    {
        EvolutionCauseCode.GEOGRAPHIC_BARRIER,
        EvolutionCauseCode.GENETIC_DIVERGENCE,
    }
)


@dataclass(frozen=True, slots=True)
class SpeciationLineages:
    """As três identidades de uma especiação: o ancestral e as duas linhagens.

    `ancestor` NÃO é nenhuma das duas linhagens resultantes — é a população como
    ela era no instante anterior à divisão. `first` e `second` são irmãs, e a
    ordem entre elas não expressa precedência alguma: `first` é a que segue com
    os traços ancestrais, `second` a que carrega a divergência.
    """

    ancestor: str
    first: str
    second: str

    @property
    def participants(self) -> tuple[str, ...]:
        """O campo `participants` do envelope §4, com os papéis explícitos."""
        return (
            f"{ANCESTOR_ROLE}:{self.ancestor}",
            f"{LINEAGE_ROLE}:{self.first}",
            f"{LINEAGE_ROLE}:{self.second}",
        )


def lineages_for(seed: int, era: int, tick: int) -> SpeciationLineages:
    """Deriva as três identidades da especiação daquele instante.

    Determinístico por construção, como os `event_id`: a mesma semente reconstrói
    exatamente as mesmas linhagens (RF-023). Um `uuid4()` aqui quebraria o replay
    bit-a-bit tanto quanto quebraria no envelope.
    """
    return SpeciationLineages(
        ancestor=deterministic_id("lineage", seed, era, tick, ANCESTOR_ROLE),
        first=deterministic_id("lineage", seed, era, tick, f"{LINEAGE_ROLE}_a"),
        second=deterministic_id("lineage", seed, era, tick, f"{LINEAGE_ROLE}_b"),
    )
