"""Contrato do World-State: snapshot imutável, fatias por domínio e deltas.

Canal A da moldura de Engines (Spec §2/§3): o Planet Engine publica um
`WorldStateSnapshot` **imutável e versionado**; cada Engine lê apenas as fatias
que declara e devolve um `StateDelta` **da sua única fatia**. Nenhum Engine
escreve no estado de outro — a fatia é a unidade de propriedade.

## Por que os deltas são aditivos

Um delta carrega a VARIAÇÃO de cada campo, não o valor final. Isso torna a
composição associativa (`merge`) e permite compor a ordem de acoplamento sem que
um Engine precise saber o que os anteriores fizeram: ele descreve só a própria
contribuição.

## Composição sequencial, não simultânea

`compose_delta` devolve um snapshot novo a cada delta, e o Planet Engine
republica esse snapshot para o Engine seguinte. A leitura literal da Spec §5.3
("publica snapshot read-only; cada Engine computa lendo o snapshot") admitiria
composição simultânea (todos leem o estado de abertura do tick), mas a própria
Spec justifica a ORDEM pelos acoplamentos — o que só faz sentido se o Engine N
enxerga o efeito dos Engines 1..N-1. É também o que o núcleo determinístico já
faz (química atualiza o CO2 ANTES de o clima calcular a estufa). Ver ADR 0008.

"Read-only" é regra de PROPRIEDADE (ninguém escreve a fatia alheia), não de
atualidade do dado.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol, cast

# Versão do esquema do world-state. Sobe quando uma fatia ganha/perde campos, de
# modo que um checkpoint gravado saiba sob qual formato foi escrito (RF-016).
#
# 1 -> 2 (M2): a `LegacySlice` foi REMOVIDA e o que ela guardava passou a ter
# Engine dono — órbita e irradiância na `AstronomySlice`, água e criosfera na
# `HydrologySlice`, biomassa na `BiotaSlice`. A `ClimateSlice` perdeu `ice_cover`
# (a criosfera é reservatório de água) e as fatias de química, recurso e biota
# ganharam seus campos. Checkpoints da versão 1 não são legíveis como 2.
#
# 2 -> 3 (M3): a biota passa a ter DOIS produtores — Evolution e Ecology — e a
# Spec §3 fala em uma única `BiotaSlice`. Como a moldura exige UM escritor por
# fatia (`validate_graph`), a biota foi desdobrada em `BiotaSlice` (Evolution) e
# `EcologySlice` (Ecology). Divergência consciente da letra da Spec para honrar
# a regra normativa dela (ADR 0016).
#
# 3 -> 4 (M4): entra a `EventSlice`, dona das perturbações extraordinárias. Ela
# existe porque um evento perturba grandezas de fatias que JÁ TÊM DONO — o
# Event Engine não pode escrever `climate.temperature` sem quebrar a regra de um
# escritor. A perturbação vira ESCALAR publicado aqui, e cada Engine afetado a
# lê e a incorpora à própria dinâmica (ADR 0018). Checkpoints da versão 3 não
# trazem a fatia; ler um deles como 4 devolve a `EventSlice` zerada, que é o
# mundo sem perturbação ativa — degradação correta, não silenciosa.
# 4 -> 5 (M5): sai `atmosphere.oxygen`. O campo existia desde o M1 e NUNCA teve
# escritor: nenhum Engine o produzia, a ponte não o mapeava, e ele valia 0,0 em
# toda corrida. O round-trip "passava" nele por vacuidade (0,0 == 0,0), que é
# justamente o tipo de verde que não afirma nada.
#
# Manter um campo sem dono contradiz a regra que o M2 fixou — toda grandeza do
# world-state tem um Engine dono (ADR 0014) — e ofereceria ao próximo leitor uma
# grandeza que parece existir e não existe. A oxigenação atmosférica é ciência
# AUSENTE, não ciência zerada: está registrada como pendência em
# `docs/decisions/deferred.md` (Grande Oxigenação) para um marco futuro.
#
WORLD_STATE_VERSION = 5


class SliceRef(StrEnum):
    """Identifica uma fatia do world-state (a unidade de propriedade de escrita).

    Desde o M2 não há mais fatia transitória: TODA grandeza tem um Engine dono
    (ADR 0014). A `LEGACY` foi removida junto com o adaptador.
    """

    ASTRONOMY = "astronomy"
    GEOLOGY = "geology"
    ATMOSPHERE = "atmosphere"
    CLIMATE = "climate"
    HYDROLOGY = "hydrology"
    CHEMISTRY = "chemistry"
    RESOURCE = "resource"
    BIOTA = "biota"
    ECOLOGY = "ecology"
    EVENT = "event"


@dataclass(frozen=True, slots=True)
class AstronomySlice:
    """Órbita e irradiância incidente no topo da atmosfera.

    A Spec §3 lista sete fatias mas inclui `physics` na ordem de tick (§5.3) sem
    lhe dar fatia. Esta fatia fecha a lacuna: o estado orbital não é atmosférico
    nem climático, e o integrador simplético precisa ser dono exclusivo dele.
    """

    orbital_x: float = 0.0
    orbital_y: float = 0.0
    orbital_vx: float = 0.0
    orbital_vy: float = 0.0
    solar_flux: float = 0.0


@dataclass(frozen=True, slots=True)
class GeologySlice:
    """Relevo, atividade vulcânica e o fluxo de CO2 desgaseificado.

    `co2_flux` é a saída do Geology Engine para a atmosfera. Publicá-lo aqui, e
    não escrever direto na `AtmosphereSlice`, é o que mantém a seta
    vulcanismo->CO2 cruzando a fronteira SOMENTE pelo Canal A (Spec §2).
    """

    relief: float = 0.0
    volcanism: float = 0.0
    co2_flux: float = 0.0


@dataclass(frozen=True, slots=True)
class AtmosphereSlice:
    """Composição atmosférica e forçamento radiativo (Atmosphere Engine, M1).

    `co2` é o ESTOQUE — dono único desde o M1. O ciclo do carbono inteiro
    (desgaseificação, intemperismo e absorção biótica) vive no Atmosphere
    Engine; o `chemistry` legado deixou de escrever carbono (ADR 0010).
    """

    co2: float = 0.0
    pressure: float = 0.0
    greenhouse_forcing: float = 0.0


@dataclass(frozen=True, slots=True)
class ClimateSlice:
    """Temperatura média e balanço de energia absorvida.

    `ice_cover` saiu daqui no M2: a criosfera é um reservatório de ÁGUA, e quem
    a governa é a Hydrology. O Climate a LÊ para o albedo (leitura defasada).
    """

    temperature: float = 0.0
    energy: float = 0.0


@dataclass(frozen=True, slots=True)
class HydrologySlice:
    """Ciclo da água completo: quatro reservatórios e os fluxos entre eles (M2).

    A soma `ocean + ice + vapour + freshwater` é conservada dentro da tolerância
    declarada — a água não é criada nem destruída, só muda de reservatório. É a
    invariante que o Planet Engine verifica (Spec §3).
    """

    ocean: float = 0.0
    ice: float = 0.0
    vapour: float = 0.0
    freshwater: float = 0.0
    salinity: float = 0.0
    ocean_circulation: float = 0.0
    # Fração da hidrosfera aprisionada em gelo — o que o albedo enxerga.
    # PUBLICADA aqui, e não recalculada pelo Climate, por duas razões: um Engine
    # não importa outro (contrato de import-linter), e derivar a mesma grandeza
    # em dois lugares é a definição de ciência duplicada.
    ice_fraction: float = 0.0
    # Fluxos do tick (diagnóstico observável, não reservatório).
    evaporation: float = 0.0
    precipitation: float = 0.0


@dataclass(frozen=True, slots=True)
class ChemistrySlice:
    """Ciclos biogeoquímicos: carbono NÃO-atmosférico, N/P/S, nutrientes e pH.

    O carbono ATMOSFÉRICO não mora aqui — é da Atmosphere (M1). Esta fatia detém
    os demais reservatórios e, sobretudo, o `air_sea_flux`: um fluxo ÚNICO,
    somado ao oceano e subtraído da atmosfera, para que o carbono não seja
    contado duas vezes (ADR 0012).
    """

    ocean_carbon: float = 0.0
    soil_carbon: float = 0.0
    nitrogen: float = 0.0
    phosphorus: float = 0.0
    sulfur: float = 0.0
    nutrients: float = 0.0
    ph: float = 0.0
    # Troca ar<->oceano do tick: positivo = oceano ABSORVE da atmosfera.
    air_sea_flux: float = 0.0


@dataclass(frozen=True, slots=True)
class ResourceSlice:
    """Estoques agregados de recurso e a CAPACIDADE DE SUPORTE derivada (M2).

    `carrying_capacity` é o único acoplamento entre a física determinística e a
    biologia: o Biota (M2, provisório) e a evolução emergente (M3) a consomem
    como orçamento, e nunca escrevem de volta.
    """

    water_available: float = 0.0
    nutrients_available: float = 0.0
    energy_available: float = 0.0
    carrying_capacity: float = 0.0
    consumed: float = 0.0


@dataclass(frozen=True, slots=True)
class BiotaSlice:
    """Vida agregada — escrita pelo **Evolution Engine** (M3).

    Carrega AGREGADOS escalares, não a composição por espécie. A composição
    (id, genoma, população, nível trófico, era de surgimento) vive no códex e
    viaja pelo Canal B como evento, por duas razões que se somam (ADR 0016):

    1. `StateDelta.values` é `Mapping[str, float]` e `apply_delta` SOMA floats.
       Uma lista de registros não trafega pelo Canal A — colocá-la ali mudaria o
       tipo do canal para o sistema inteiro e quebraria a semântica aditiva de
       que o replay depende.
    2. O ADR 0006 mantém espécies fora do world-state de propósito: é isso que
       faz a física ser bit-a-bit idêntica com biologia ligada ou desligada.

    O resultado materializa a Correção 2 do ADR-ARCH-0002: agregado por padrão no
    world-state, detalhe por espécie sob demanda, no códex.

    **`biomass` é OCUPAÇÃO, não limite.** O teto que o ambiente oferece é a
    `carrying_capacity` da `ResourceSlice`, e quem o deriva é o Resource. Este
    Engine gasta esse orçamento; nunca o redefine. A distinção é a fronteira em
    que um Engine futuro tende a se confundir.
    """

    biomass: float = 0.0
    species_richness: float = 0.0
    # GENOMA MÉDIO da comunidade viva. É a representação agregada que permite ao
    # Engine ser função PURA do snapshot: sem ela, a composição teria de viver
    # num atributo do Engine, e `tick()` deixaria de depender só do que recebe —
    # exatamente o que o replay bit-a-bit não admite (ADR 0011 §4).
    #
    # A seleção move estas médias na direção do ótimo LOCAL (genética
    # quantitativa); a composição por espécie é materializada no códex a partir
    # dos eventos do Canal B, que carregam o genoma no `cause_detail`.
    mean_temp_optimum: float = 0.0
    mean_temp_tolerance: float = 0.0
    mean_water_need: float = 0.0
    mean_size: float = 0.0
    mean_metabolism: float = 0.0
    mean_trophic_level: float = 0.0


@dataclass(frozen=True, slots=True)
class EcologySlice:
    """Dinâmica trófica agregada — escrita pelo **Ecology Engine** (M3).

    Existe como fatia SEPARADA da `BiotaSlice` porque a moldura exige um escritor
    por fatia e a biota tem dois produtores. A Spec §3 lista literalmente
    "`BiotaSlice` (evolução/ecologia)"; representá-la por duas fatias é a leitura
    que honra a regra normativa da própria Spec (ADR 0016).
    """

    producer_biomass: float = 0.0
    herbivore_biomass: float = 0.0
    predator_biomass: float = 0.0
    # Pressão de predação que o Evolution lê DEFASADA para a seleção local.
    predation_pressure: float = 0.0
    total_population: float = 0.0


# Mapa fatia -> atributo do snapshot. Explícito (dado), não derivado por
# convenção de nome: renomear um atributo não pode quebrar silenciosamente.
SLICE_ATTRIBUTE: Mapping[SliceRef, str] = MappingProxyType(
    {
        SliceRef.ASTRONOMY: "astronomy",
        SliceRef.GEOLOGY: "geology",
        SliceRef.ATMOSPHERE: "atmosphere",
        SliceRef.CLIMATE: "climate",
        SliceRef.HYDROLOGY: "hydrology",
        SliceRef.CHEMISTRY: "chemistry",
        SliceRef.RESOURCE: "resource",
        SliceRef.BIOTA: "biota",
        SliceRef.ECOLOGY: "ecology",
        SliceRef.EVENT: "event",
    }
)


@dataclass(frozen=True, slots=True)
class EventSlice:
    """Perturbações extraordinárias ATIVAS — escrita pelo **Event Engine** (M4).

    ## Por que os eventos extraordinários precisam de fatia própria

    Um meteoro esfria o planeta, uma seca reduz a precipitação, uma era glacial
    baixa a temperatura. Todas essas grandezas pertencem a fatias que JÁ TÊM
    DONO — `atmosphere`, `climate`, `hydrology` —, e a moldura admite **um
    escritor por fatia** (Spec §3): `validate_graph` recusa no boot um segundo
    escritor. O Event Engine, portanto, **não pode** aplicar a perturbação
    escrevendo na fatia perturbada.

    A saída é inverter a direção: o Event Engine publica a perturbação como
    ESCALAR na fatia dele, e cada Engine afetado **lê** esse escalar e o
    incorpora à própria dinâmica, na própria fatia. A física continua sendo
    decidida por quem a detém — o Event Engine descreve a causa, não o efeito.

    Isso mantém três coisas de pé ao mesmo tempo (ADR 0018):

    1. **um dono por fatia**, verificado no boot;
    2. **as perturbações no Canal A** (float, aditivo, replayável), e não no
       Canal B — o Canal B narra a OCORRÊNCIA (`MeteorImpact`), o Canal A carrega
       a CONSEQUÊNCIA física contínua;
    3. **nenhum Engine lendo o estado interno de outro** — tudo pelo world-state.

    ## Perturbações são estoques que decaem, não pulsos

    Cada campo é a intensidade CORRENTE da perturbação, já integrada pelo Event
    Engine (um meteoro injeta poeira que decai ao longo de dezenas de ticks). Os
    Engines afetados leem o valor de agora e não precisam saber há quanto tempo o
    evento ocorreu — o que os mantém ignorantes do catálogo de eventos.
    """

    # Poeira em suspensão: aumenta o albedo e reflete irradiância (meteoro,
    # supervulcanismo). Adimensional, 0 = céu limpo.
    dust_load: float = 0.0
    # Forçamento radiativo NEGATIVO imposto por evento (era glacial, inverno de
    # impacto). Em W/m², somado ao forçamento do Climate.
    cooling_forcing: float = 0.0
    # Intensidade da seca em [0,1]: fração da precipitação suprimida.
    drought_intensity: float = 0.0
    # Energia do impacto no tick em que ele ocorre — pico, não estoque. Alimenta
    # a magnitude do `MeteorImpact` e a mortalidade catastrófica.
    impact_energy: float = 0.0
    # Fração da biomassa removida por catástrofe neste tick, INDEPENDENTE de
    # adaptação (ADR 0019). É o mecanismo que torna possível uma espécie bem
    # adaptada ser extinta — a correção de concepção equivocada do M4.
    catastrophic_mortality: float = 0.0
    # Pulso de CO2 do SUPERVULCANISMO. Não é somado à atmosfera por este Engine:
    # quem o lê é a **Geology**, que o funde à própria desgaseificação para que
    # exista UM único fluxo de carbono vulcânico no mundo (ADR 0018, fronteira
    # basal x catastrófico). Publicá-lo aqui e somá-lo na atmosfera criaria dois
    # termos de entrada e a dupla contagem que o M2 já pagou uma vez para evitar.
    supervolcanic_intensity: float = 0.0

    # --- Telegrafia (RF-019/020) ----------------------------------------------
    # O evento agendado é ANUNCIADO antes de acontecer, para que o jogador possa
    # agir. Estes campos são o que a API expõe ao frontend.
    #
    # Escalares, e não uma lista de eventos, porque o Canal A é aditivo e de
    # floats: a identidade do evento anunciado viaja pelo Canal B
    # (`EventForecast`), e aqui fica o que a interface precisa para o aviso.
    forecast_kind: float = 0.0  # índice do evento no catálogo; 0 = nada anunciado
    forecast_ticks_ahead: float = 0.0  # quantos ticks faltam para ele ocorrer
    forecast_severity: float = 0.0  # intensidade prevista, em [0,1]

    # --- Bookkeeping do evento em curso ---------------------------------------
    # Mora AQUI, e não num atributo do Event Engine, por uma razão dura: `tick()`
    # tem de ser função PURA do snapshot — é disso que o replay bit-a-bit depende
    # (Spec §7). Um Engine que guardasse "qual evento está ativo e há quantos
    # ticks" num campo próprio deixaria de depender só do que recebe, e
    # reconstruir uma era a partir de `(seed, checkpoint)` pararia de funcionar.
    #
    # É o mesmo motivo pelo qual a Evolution carrega o genoma médio na fatia em
    # vez de guardar a lista de espécies (ADR 0016).
    active_kind: float = 0.0  # evento perturbando agora; 0 = nenhum
    active_elapsed: float = 0.0  # ticks desde o início dele
    active_severity: float = 0.0  # severidade sorteada quando foi agendado
    quiet_remaining: float = 0.0  # silêncio obrigatório após o último evento


@dataclass(frozen=True, slots=True)
class WorldStateSnapshot:
    """Estado do mundo em um instante — imutável, versionado e read-only.

    `version`/`tick`/`era`/`seed` são o cabeçalho exigido pela Spec §3: o
    primeiro identifica o formato, os demais situam o snapshot no tempo de
    simulação e na trajetória reprodutível (RF-023). `planet_id` acompanha-os
    porque um snapshot é sempre de UM planeta — sem ele, a borda de persistência
    teria de carregar a identidade num canal paralelo.
    """

    planet_id: str
    seed: int
    tick: int
    era: int
    version: int = WORLD_STATE_VERSION
    astronomy: AstronomySlice = AstronomySlice()
    geology: GeologySlice = GeologySlice()
    atmosphere: AtmosphereSlice = AtmosphereSlice()
    climate: ClimateSlice = ClimateSlice()
    hydrology: HydrologySlice = HydrologySlice()
    chemistry: ChemistrySlice = ChemistrySlice()
    resource: ResourceSlice = ResourceSlice()
    biota: BiotaSlice = BiotaSlice()
    ecology: EcologySlice = EcologySlice()
    event: EventSlice = EventSlice()
    # Proveniência causal: para cada fatia, os eventos que produziram o valor
    # corrente dela. Vive AQUI, e não em atributo do Planet Engine, por uma razão
    # de pureza: guardá-la fora do snapshot tornaria `tick()` dependente de
    # chamadas anteriores, e o replay deixaria de ser função da semente. Como é
    # derivada de um fluxo de eventos determinístico, ela é reproduzida idêntica
    # — e é o que permite encadear `causation_id` ENTRE ticks (uma erupção no
    # tick 12 explicando o forçamento que cruza o patamar no tick 40).
    provenance: Mapping[SliceRef, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))

    def with_provenance(self, updates: Mapping[SliceRef, tuple[str, ...]]) -> WorldStateSnapshot:
        """Novo snapshot com a proveniência das fatias tocadas atualizada."""
        if not updates:
            return self
        merged = dict(self.provenance)
        merged.update(updates)
        return replace(self, provenance=merged)

    def slice_of(self, ref: SliceRef) -> Any:
        """Lê uma fatia pelo seu identificador (acesso somente leitura)."""
        return getattr(self, SLICE_ATTRIBUTE[ref])

    def with_slice(self, ref: SliceRef, value: Any) -> WorldStateSnapshot:
        """Devolve um NOVO snapshot com a fatia substituída (nunca muta o atual)."""
        return replace(self, **{SLICE_ATTRIBUTE[ref]: value})

    def advanced(self) -> WorldStateSnapshot:
        """Novo snapshot com o contador de tick incrementado."""
        return replace(self, tick=self.tick + 1)


@dataclass(frozen=True, slots=True)
class StateDelta:
    """Contribuição aditiva de UM Engine a UMA fatia, em UM tick (Spec §3).

    `caused_by` liga o delta aos eventos que o motivaram, fechando a cadeia
    causal do Canal A para o Canal B (Spec §4).
    """

    engine_id: str
    tick: int
    writes: SliceRef
    values: Mapping[str, float] = field(default_factory=dict)
    caused_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Congela o mapa: um delta é um fato registrado, não um acumulador.
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def merge(self, other: StateDelta) -> StateDelta:
        """Soma dois deltas da MESMA fatia (associativo e determinístico).

        A identidade do Engine é preservada apenas quando ambos vêm do mesmo
        Engine; a composição de Engines distintos guarda a autoria em cada delta
        original — o merge é usado para agregar contribuições, não para apagar
        proveniência.
        """
        if other.writes is not self.writes:
            raise ValueError(
                f"não se somam deltas de fatias distintas: {self.writes} != {other.writes}"
            )
        merged: dict[str, float] = dict(self.values)
        for key, value in other.values.items():
            merged[key] = merged.get(key, 0.0) + value
        engine_id = self.engine_id if self.engine_id == other.engine_id else "composed"
        return StateDelta(
            engine_id=engine_id,
            tick=self.tick,
            writes=self.writes,
            values=merged,
            caused_by=self.caused_by + other.caused_by,
        )


@dataclass(frozen=True, slots=True)
class InvariantBreach:
    """Registro de uma invariante violada — insumo de `DiagnosticEvent`.

    Uma violação NUNCA altera a decisão da simulação: o reparo (quando existe) é
    parte determinística da composição, e o registro segue pelo Canal B.
    """

    invariant: str
    slice_ref: SliceRef
    field: str
    value: float
    limit: float


@dataclass(frozen=True, slots=True)
class InvariantOutcome:
    """Snapshot após aplicar uma invariante, com as violações observadas."""

    snapshot: WorldStateSnapshot
    breaches: tuple[InvariantBreach, ...] = ()


class Invariant(Protocol):
    """Regra de sanidade aplicada pelo Planet Engine ao compor um delta."""

    @property
    def name(self) -> str:
        """Rótulo que identifica a invariante no `DiagnosticEvent`."""
        ...

    def apply(self, before: WorldStateSnapshot, after: WorldStateSnapshot) -> InvariantOutcome: ...


@dataclass(frozen=True, slots=True)
class NonNegativeStocks:
    """Estoques não podem ficar negativos (Spec §3): recorta em zero e registra.

    O recorte é determinístico e faz parte do cálculo — é a mesma regra que o
    núcleo determinístico já aplica em `PlanetState.apply`. O que vai para a
    observabilidade é só o REGISTRO de que houve recorte.
    """

    targets: Mapping[SliceRef, tuple[str, ...]]
    floor: float = 0.0
    name: str = "non_negative_stocks"

    def apply(self, before: WorldStateSnapshot, after: WorldStateSnapshot) -> InvariantOutcome:
        del before  # a invariante é local ao estado resultante
        snapshot = after
        breaches: list[InvariantBreach] = []
        for ref, field_names in self.targets.items():
            current = snapshot.slice_of(ref)
            repairs: dict[str, float] = {}
            for field_name in field_names:
                value = float(getattr(current, field_name))
                if value < self.floor:
                    breaches.append(
                        InvariantBreach(self.name, ref, field_name, value, limit=self.floor)
                    )
                    repairs[field_name] = self.floor
            if repairs:
                snapshot = snapshot.with_slice(ref, replace(cast(Any, current), **repairs))
        return InvariantOutcome(snapshot, tuple(breaches))


@dataclass(frozen=True, slots=True)
class BoundedFraction:
    """Frações físicas confinadas a [0,1] (cobertura de gelo, circulação…)."""

    targets: Mapping[SliceRef, tuple[str, ...]]
    low: float = 0.0
    high: float = 1.0
    name: str = "bounded_fraction"

    def apply(self, before: WorldStateSnapshot, after: WorldStateSnapshot) -> InvariantOutcome:
        del before
        snapshot = after
        breaches: list[InvariantBreach] = []
        for ref, field_names in self.targets.items():
            current = snapshot.slice_of(ref)
            repairs: dict[str, float] = {}
            for field_name in field_names:
                value = float(getattr(current, field_name))
                clamped = max(self.low, min(self.high, value))
                if clamped != value:
                    limit = self.low if value < self.low else self.high
                    breaches.append(InvariantBreach(self.name, ref, field_name, value, limit))
                    repairs[field_name] = clamped
            if repairs:
                snapshot = snapshot.with_slice(ref, replace(cast(Any, current), **repairs))
        return InvariantOutcome(snapshot, tuple(breaches))


@dataclass(frozen=True, slots=True)
class ConservedTotal:
    """A soma de um conjunto de campos de UMA fatia não pode mudar (Spec §3).

    É a invariante da água: os fluxos apenas MOVEM massa entre reservatórios, e
    a soma dos quatro é constante dentro da tolerância declarada.

    **Não repara.** As demais invariantes recortam o valor e seguem, porque o
    recorte é regra determinística conhecida. Aqui não existe reparo correto:
    saber que a soma se moveu não diz de qual reservatório tirar a diferença, e
    escolher um esconderia o defeito exatamente onde ele precisa ser visto. A
    violação vira `DiagnosticEvent` e o número errado fica à vista.

    Aplica-se por delta, o que a torna precisa quanto à autoria: a soma só pode
    mudar no delta de quem escreve a fatia, então o Engine culpado é o que
    aparece no evento.
    """

    name: str
    slice_ref: SliceRef
    fields: tuple[str, ...]
    tolerance: float = 1e-9

    def _total(self, snapshot: WorldStateSnapshot) -> float:
        current = snapshot.slice_of(self.slice_ref)
        return sum(float(getattr(current, name)) for name in self.fields)

    def apply(self, before: WorldStateSnapshot, after: WorldStateSnapshot) -> InvariantOutcome:
        drift = self._total(after) - self._total(before)
        if abs(drift) <= self.tolerance:
            return InvariantOutcome(after)
        return InvariantOutcome(
            after,
            (
                InvariantBreach(
                    invariant=self.name,
                    slice_ref=self.slice_ref,
                    field="+".join(self.fields),
                    value=drift,
                    limit=self.tolerance,
                ),
            ),
        )


def apply_delta(snapshot: WorldStateSnapshot, delta: StateDelta) -> WorldStateSnapshot:
    """Soma o delta à fatia que ele declara escrever, sem tocar nas demais."""
    if not delta.values:
        return snapshot
    current = snapshot.slice_of(delta.writes)
    known = {f.name for f in fields(cast(Any, current))}
    unknown = set(delta.values) - known
    if unknown:
        raise ValueError(
            f"{delta.engine_id} tentou escrever campos inexistentes em "
            f"{delta.writes}: {sorted(unknown)}"
        )
    updates = {name: float(getattr(current, name)) + value for name, value in delta.values.items()}
    return snapshot.with_slice(delta.writes, replace(cast(Any, current), **updates))


@dataclass(frozen=True, slots=True)
class CompositionOutcome:
    """Resultado de compor deltas: novo snapshot + violações de invariante."""

    snapshot: WorldStateSnapshot
    breaches: tuple[InvariantBreach, ...] = ()


def compose(
    snapshot: WorldStateSnapshot,
    deltas: Sequence[StateDelta],
    invariants: Iterable[Invariant] = (),
) -> CompositionOutcome:
    """Compõe deltas EM ORDEM sobre o snapshot, aplicando as invariantes.

    Pura e determinística: a mesma sequência de deltas sobre o mesmo snapshot
    produz sempre o mesmo resultado. O Planet Engine chama esta função uma vez
    por Engine, republicando o snapshot resultante ao Engine seguinte.
    """
    invariant_list = tuple(invariants)
    current = snapshot
    breaches: list[InvariantBreach] = []
    for delta in deltas:
        before = current
        current = apply_delta(current, delta)
        for invariant in invariant_list:
            outcome = invariant.apply(before, current)
            current = outcome.snapshot
            breaches.extend(outcome.breaches)
    return CompositionOutcome(current, tuple(breaches))


# As fatias não têm um supertipo comum em runtime (são dataclasses distintas), e
# `DataclassInstance` só existe para o verificador de tipos. `Any` aqui é honesto:
# o contrato real é "instância de fatia", garantido por quem chama.
def slice_values(target: Any) -> Mapping[str, float]:
    """Lê uma fatia como mapa campo->valor (útil em testes e projeções)."""
    return {f.name: float(getattr(target, f.name)) for f in fields(target)}


def difference(before: Any, after: Any) -> Mapping[str, float]:
    """Delta campo a campo entre duas versões da MESMA fatia."""
    previous = slice_values(before)
    return {name: value - previous[name] for name, value in slice_values(after).items()}
