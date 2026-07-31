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
WORLD_STATE_VERSION = 1


class SliceRef(StrEnum):
    """Identifica uma fatia do world-state (a unidade de propriedade de escrita).

    `LEGACY` é transitória: hospeda o estado do núcleo determinístico atual
    enquanto os Engines científicos não assumem a autoria das suas fatias
    (M1/M2). Ver `engines/legacy/adapter.py` e ADR 0008.
    """

    ASTRONOMY = "astronomy"
    GEOLOGY = "geology"
    ATMOSPHERE = "atmosphere"
    CLIMATE = "climate"
    HYDROLOGY = "hydrology"
    CHEMISTRY = "chemistry"
    RESOURCE = "resource"
    BIOTA = "biota"
    LEGACY = "legacy"


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
    oxygen: float = 0.0
    greenhouse_forcing: float = 0.0


@dataclass(frozen=True, slots=True)
class ClimateSlice:
    """Temperatura média, criosfera e balanço de energia absorvida.

    No M1 o Climate Engine é dono de `temperature` e `energy`. `ice_cover`
    continua com o ciclo água/gelo do `chemistry` legado e migra no M2, junto
    com a hidrologia — por isso o Climate LÊ o gelo da fatia legada.
    """

    temperature: float = 0.0
    ice_cover: float = 0.0
    energy: float = 0.0


@dataclass(frozen=True, slots=True)
class HydrologySlice:
    """Ciclo da água: estoque líquido, salinidade e circulação termohalina."""

    water: float = 0.0
    salinity: float = 0.0
    ocean_circulation: float = 0.0


@dataclass(frozen=True, slots=True)
class ChemistrySlice:
    """Estoques químicos acoplados ao clima (carbono em primeiro lugar)."""

    co2: float = 0.0
    nutrients: float = 0.0


@dataclass(frozen=True, slots=True)
class ResourceSlice:
    """Recursos disponíveis à biota (assumida pelo Resource Engine em M2)."""

    available: float = 0.0
    consumed: float = 0.0


@dataclass(frozen=True, slots=True)
class BiotaSlice:
    """Vida agregada: biomassa e riqueza de espécies (Evolution/Ecology, M3)."""

    biomass: float = 0.0
    species_richness: float = 0.0


@dataclass(frozen=True, slots=True)
class LegacySlice:
    """O que ainda NÃO tem Engine dono (transitória, encolhendo a cada marco).

    O M1 tirou daqui `temperature`/`energy` (Climate), `co2` (Atmosphere) e
    `relief`/`volcanism` (Geology). Tirá-los do TIPO, e não só parar de
    escrevê-los, é o que torna a dupla autoria impossível por construção:
    `apply_delta` rejeita campo inexistente, então um delta legado que tentasse
    mexer em temperatura falharia no ato, em vez de divergir em silêncio.

    Restam a hidrologia (água, gelo, salinidade, circulação), a astronomia
    (órbita e irradiância) e a biomassa. Migram no M2/M3, e a fatia desaparece.
    """

    water: float = 0.0
    ice_cover: float = 0.0
    biomass: float = 0.0
    orbital_x: float = 0.0
    orbital_y: float = 0.0
    orbital_vx: float = 0.0
    orbital_vy: float = 0.0
    solar_flux: float = 0.0
    salinity: float = 0.0
    ocean_circulation: float = 0.0


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
        SliceRef.LEGACY: "legacy",
    }
)


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
    legacy: LegacySlice = LegacySlice()
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
