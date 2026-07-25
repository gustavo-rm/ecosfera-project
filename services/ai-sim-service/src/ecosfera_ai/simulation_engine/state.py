"""Estado do planeta e álgebra de deltas do núcleo de simulação determinístico.

Puro: sem FastAPI, sem numpy, sem I/O. O RNG e os subsistemas vivem em
`orchestrator`/`subsystems`; aqui ficam apenas os dados imutáveis do estado e os
métodos puros para aplicar variações (`StateDelta`) e derivar observações
(`Observation`), estas consumidas sem alteração pelo motor de feedback causal já
existente (RF-013/023).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ecosfera_ai.domain.feedback.models import Observation

# Variáveis de estado expostas como observações causais, na ordem canônica da
# narrativa (co2 primeiro: é a alavanca pedagógica de 'CO2↑ -> temperatura↑').
OBSERVABLE_VARIABLES: tuple[str, ...] = (
    "co2",
    "temperature",
    "ice_cover",
    "water",
    "biomass",
    "energy",
)


@dataclass(frozen=True, slots=True)
class PlanetSeed:
    """Semente de criação de um planeta (RF-011/012).

    `seed` fixa o RNG do motor, garantindo trajetórias reprodutíveis (RF-023). O
    estado inicial em si vem dos parâmetros versionados (simulation_params.yaml),
    não da semente — a semente controla apenas a estocasticidade dos ticks.
    """

    planet_id: str
    seed: int


@dataclass(frozen=True, slots=True)
class StateBounds:
    """Faixas físicas válidas de cada variável (dados versionados).

    Garante sanidade científica: a cobertura de gelo é uma fração [0,1]; água,
    CO2, biomassa e energia não podem ser negativos (RF-014).
    """

    ice_cover_min: float = 0.0
    ice_cover_max: float = 1.0
    water_min: float = 0.0
    co2_min: float = 0.0
    biomass_min: float = 0.0
    energy_min: float = 0.0


@dataclass(frozen=True, slots=True)
class StateDelta:
    """Variação aditiva do estado produzida por um subsistema em um passo.

    Somável (padrão Strategy): o orquestrador combina os deltas dos subsistemas
    sem conhecer seus detalhes internos.
    """

    d_temperature: float = 0.0
    d_co2: float = 0.0
    d_water: float = 0.0
    d_ice_cover: float = 0.0
    d_biomass: float = 0.0
    d_energy: float = 0.0

    def __add__(self, other: StateDelta) -> StateDelta:
        return StateDelta(
            d_temperature=self.d_temperature + other.d_temperature,
            d_co2=self.d_co2 + other.d_co2,
            d_water=self.d_water + other.d_water,
            d_ice_cover=self.d_ice_cover + other.d_ice_cover,
            d_biomass=self.d_biomass + other.d_biomass,
            d_energy=self.d_energy + other.d_energy,
        )


@dataclass(frozen=True, slots=True)
class PlanetState:
    """Estado imutável do planeta em um instante (checkpoint de era — Dossiê §9).

    Imutável por design: cada tick produz um NOVO estado (append-only), o que
    habilita replay determinístico (RF-016) e auditoria da trajetória.
    """

    planet_id: str
    seed: int
    tick: int
    temperature: float  # °C, temperatura média global
    co2: float  # ppm, estoque de dióxido de carbono
    water: float  # estoque relativo de água líquida
    ice_cover: float  # fração [0,1] da superfície coberta por gelo
    biomass: float  # estoque relativo de biomassa (vida)
    energy: float  # energia solar líquida absorvida (diagnóstico)

    def value(self, variable: str) -> float:
        """Lê uma variável de estado pelo nome da linguagem ubíqua do domínio."""
        return float(getattr(self, variable))

    def apply(self, delta: StateDelta, bounds: StateBounds) -> PlanetState:
        """Aplica um delta e recorta cada variável à sua faixa física válida."""
        return replace(
            self,
            temperature=self.temperature + delta.d_temperature,
            co2=max(bounds.co2_min, self.co2 + delta.d_co2),
            water=max(bounds.water_min, self.water + delta.d_water),
            ice_cover=_clamp(
                self.ice_cover + delta.d_ice_cover,
                bounds.ice_cover_min,
                bounds.ice_cover_max,
            ),
            biomass=max(bounds.biomass_min, self.biomass + delta.d_biomass),
            energy=max(bounds.energy_min, self.energy + delta.d_energy),
        )

    def advanced(self) -> PlanetState:
        """Retorna o mesmo estado com o contador de tick incrementado (nova era)."""
        return replace(self, tick=self.tick + 1)

    def delta_from(self, previous: PlanetState) -> StateDelta:
        """Delta absoluto agregado deste estado em relação a um anterior."""
        return StateDelta(
            d_temperature=self.temperature - previous.temperature,
            d_co2=self.co2 - previous.co2,
            d_water=self.water - previous.water,
            d_ice_cover=self.ice_cover - previous.ice_cover,
            d_biomass=self.biomass - previous.biomass,
            d_energy=self.energy - previous.energy,
        )

    def observe(self, previous: PlanetState, *, epsilon: float = 1e-9) -> list[Observation]:
        """Deriva observações (variação relativa) para o motor de feedback causal.

        A variação é relativa ao valor anterior (adimensional), coerente com o
        contrato de `Observation` já consumido por `/ai/explain`. Variáveis com
        variação desprezível (< epsilon) são omitidas para não poluir a cadeia.
        """
        observations: list[Observation] = []
        for variable in OBSERVABLE_VARIABLES:
            before = previous.value(variable)
            change = self.value(variable) - before
            if abs(change) < epsilon:
                continue
            scale = max(abs(before), epsilon)
            observations.append(Observation(variable=variable, delta=change / scale))
        return observations


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
