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
# As coordenadas orbitais ficam de fora de propósito: são estado interno do
# integrador, não grandeza que o aluno interpreta.
OBSERVABLE_VARIABLES: tuple[str, ...] = (
    "co2",
    "temperature",
    "ice_cover",
    "water",
    "biomass",
    "energy",
    "solar_flux",
    "volcanism",
    "relief",
    "salinity",
    "ocean_circulation",
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
    # Subsistemas estendidos (física/geologia/oceano)
    solar_flux_min: float = 0.0
    relief_min: float = 0.0
    relief_max: float = 1.0
    volcanism_min: float = 0.0
    salinity_min: float = 0.0
    ocean_circulation_min: float = 0.0
    ocean_circulation_max: float = 1.0


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
    # Física orbital (integrador de Verlet) e irradiância incidente
    d_orbital_x: float = 0.0
    d_orbital_y: float = 0.0
    d_orbital_vx: float = 0.0
    d_orbital_vy: float = 0.0
    d_solar_flux: float = 0.0
    # Geologia
    d_relief: float = 0.0
    d_volcanism: float = 0.0
    # Oceano
    d_salinity: float = 0.0
    d_ocean_circulation: float = 0.0

    def __add__(self, other: StateDelta) -> StateDelta:
        return StateDelta(
            d_temperature=self.d_temperature + other.d_temperature,
            d_co2=self.d_co2 + other.d_co2,
            d_water=self.d_water + other.d_water,
            d_ice_cover=self.d_ice_cover + other.d_ice_cover,
            d_biomass=self.d_biomass + other.d_biomass,
            d_energy=self.d_energy + other.d_energy,
            d_orbital_x=self.d_orbital_x + other.d_orbital_x,
            d_orbital_y=self.d_orbital_y + other.d_orbital_y,
            d_orbital_vx=self.d_orbital_vx + other.d_orbital_vx,
            d_orbital_vy=self.d_orbital_vy + other.d_orbital_vy,
            d_solar_flux=self.d_solar_flux + other.d_solar_flux,
            d_relief=self.d_relief + other.d_relief,
            d_volcanism=self.d_volcanism + other.d_volcanism,
            d_salinity=self.d_salinity + other.d_salinity,
            d_ocean_circulation=self.d_ocean_circulation + other.d_ocean_circulation,
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

    # Campos dos subsistemas estendidos. Têm default para que estados legados
    # (e testes que só exercitam clima/química/vida) continuem construíveis.
    orbital_x: float = 0.0  # UA, posição orbital (integrador de Verlet)
    orbital_y: float = 0.0  # UA
    orbital_vx: float = 0.0  # UA/tick, velocidade orbital
    orbital_vy: float = 0.0  # UA/tick
    solar_flux: float = 0.0  # irradiância incidente no topo da atmosfera
    relief: float = 0.0  # rugosidade/relevo médio [0,1]
    volcanism: float = 0.0  # atividade vulcânica (fonte de CO2)
    salinity: float = 0.0  # salinidade média do oceano
    ocean_circulation: float = 0.0  # índice de circulação termohalina [0,1]

    # ── Estoques das fatias do M2 ───────────────────────────────────────────
    # A borda HTTP e a persistência guardam ESTE objeto, e o tick faz o ciclo
    # `snapshot -> Engines -> PlanetState` a cada passo. Um estoque sem lugar
    # aqui voltaria a zero uma vez por tick, e a hidrologia, a química, o recurso
    # e a biota nunca realimentariam nada (ADR 0012).
    #
    # `water` e `ice_cover` acima continuam sendo os AGREGADOS publicados,
    # derivados destes reservatórios — o contrato HTTP não mudou.
    ocean_water: float = 0.0  # reservatório oceânico (líquido salgado)
    ice_mass: float = 0.0  # criosfera (massa, não fração)
    vapour: float = 0.0  # vapor de água na atmosfera
    freshwater: float = 0.0  # água doce continental
    evaporation: float = 0.0  # fluxo do tick (diagnóstico)
    precipitation: float = 0.0  # fluxo do tick (diagnóstico)

    ocean_carbon: float = 0.0  # carbono dissolvido no oceano
    soil_carbon: float = 0.0  # carbono soterrado no sedimento
    nitrogen: float = 0.0
    phosphorus: float = 0.0
    sulfur: float = 0.0
    nutrients: float = 0.0  # estoque agregado de nutrientes
    ph: float = 0.0  # pH oceânico
    air_sea_flux: float = 0.0  # troca ar<->oceano (positivo = oceano absorve)

    water_available: float = 0.0  # recurso hídrico biologicamente utilizável
    nutrients_available: float = 0.0  # nutriente aproveitável (lei do mínimo)
    energy_available: float = 0.0  # energia biologicamente útil
    # Capacidade de suporte derivada pelo Resource Engine. PUBLICADA aqui porque
    # é o único acoplamento entre a física e a biologia: o M3 a lê deste campo em
    # vez de instanciar um subsistema de vida (ADR 0006/0013).
    carrying_capacity: float = 0.0
    consumed: float = 0.0  # recurso retirado pela biomassa no tick

    species_richness: float = 0.0  # riqueza de espécies (camada emergente, M3)

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
            # Órbita: sem recorte — a posição/velocidade são livres por construção
            # (o integrador simplético é quem garante a estabilidade).
            orbital_x=self.orbital_x + delta.d_orbital_x,
            orbital_y=self.orbital_y + delta.d_orbital_y,
            orbital_vx=self.orbital_vx + delta.d_orbital_vx,
            orbital_vy=self.orbital_vy + delta.d_orbital_vy,
            solar_flux=max(bounds.solar_flux_min, self.solar_flux + delta.d_solar_flux),
            relief=_clamp(self.relief + delta.d_relief, bounds.relief_min, bounds.relief_max),
            volcanism=max(bounds.volcanism_min, self.volcanism + delta.d_volcanism),
            salinity=max(bounds.salinity_min, self.salinity + delta.d_salinity),
            ocean_circulation=_clamp(
                self.ocean_circulation + delta.d_ocean_circulation,
                bounds.ocean_circulation_min,
                bounds.ocean_circulation_max,
            ),
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
            d_orbital_x=self.orbital_x - previous.orbital_x,
            d_orbital_y=self.orbital_y - previous.orbital_y,
            d_orbital_vx=self.orbital_vx - previous.orbital_vx,
            d_orbital_vy=self.orbital_vy - previous.orbital_vy,
            d_solar_flux=self.solar_flux - previous.solar_flux,
            d_relief=self.relief - previous.relief,
            d_volcanism=self.volcanism - previous.volcanism,
            d_salinity=self.salinity - previous.salinity,
            d_ocean_circulation=self.ocean_circulation - previous.ocean_circulation,
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
