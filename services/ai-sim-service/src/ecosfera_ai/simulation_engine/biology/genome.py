"""Genoma inspecionável das espécies (RF-031).

O genoma é um vetor de traços fenotípicos com faixas válidas explícitas. Duas
exigências moldam este módulo:

1. **Inspecionabilidade (RF-031).** O aluno precisa poder abrir o códex e ver
   *por que* uma espécie prosperou ou morreu. Por isso os traços têm nomes do
   domínio (tolerância térmica, necessidade de água, nível trófico) e não pesos
   opacos, e o genoma serializa para dicionário sem perda.
2. **Emergente porém reproduzível (RF-023).** O genoma em si é um dado imutável e
   puro; toda a estocasticidade vive no motor evolutivo, que recebe RNG semeado.

Puro: sem DEAP, sem Mesa, sem I/O — o AG opera SOBRE esta estrutura.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, ClassVar

# Níveis tróficos suportados no MVP da cadeia alimentar.
TROPHIC_PRODUCER = 1  # fotossíntese: come luz/nutrientes
TROPHIC_HERBIVORE = 2  # come produtores
TROPHIC_PREDATOR = 3  # come herbívoros


@dataclass(frozen=True, slots=True)
class Genome:
    """Traços fenotípicos de uma espécie, todos dentro de faixas válidas.

    `trophic_level` é armazenado como float para que o AG possa cruzá-lo e
    mutá-lo continuamente (a mutação de nicho é gradual); a leitura ecológica
    usa `trophic_class`, que discretiza o valor.
    """

    temp_optimum: float  # °C preferido
    temp_tolerance: float  # largura da janela térmica suportada
    water_need: float  # água mínima para prosperar
    size: float  # massa corporal relativa
    metabolism: float  # custo energético por indivíduo
    trophic_level: float  # 1=produtor, 2=herbívoro, 3=predador (contínuo)

    # Faixas válidas de cada traço (dados de domínio, não mágicos no código).
    BOUNDS: ClassVar[dict[str, tuple[float, float]]] = {
        "temp_optimum": (-40.0, 80.0),
        "temp_tolerance": (1.0, 60.0),
        "water_need": (0.0, 2.0),
        "size": (0.01, 100.0),
        "metabolism": (0.05, 3.0),
        "trophic_level": (1.0, 3.0),
    }

    @property
    def trophic_class(self) -> int:
        """Nível trófico discreto usado pela cadeia alimentar da ecologia."""
        return round(self.trophic_level)

    def clamped(self) -> Genome:
        """Retorna o genoma com todos os traços recortados às faixas válidas.

        Chamado após cruzamento/mutação: o AG pode gerar valores fora da faixa e
        um organismo fora da física do mundo não é biologicamente admissível.
        """
        values: dict[str, float] = {}
        for field in fields(self):
            low, high = self.BOUNDS[field.name]
            values[field.name] = _clamp(float(getattr(self, field.name)), low, high)
        return replace(self, **values)

    def distance(self, other: Genome) -> float:
        """Distância genética normalizada [0,1] entre dois genomas.

        Cada traço contribui com sua diferença relativa à própria faixa, de modo
        que traços em escalas diferentes pesem igual. É o critério de
        **especiação**: divergência acima do limiar cria uma espécie nova.
        """
        total = 0.0
        for field in fields(self):
            low, high = self.BOUNDS[field.name]
            span = high - low
            delta = float(getattr(self, field.name)) - float(getattr(other, field.name))
            total += (delta / span) ** 2
        return math.sqrt(total / len(fields(self)))

    def to_dict(self) -> dict[str, float]:
        """Serializa para o catálogo/API (inspecionável — RF-031)."""
        return {key: float(value) for key, value in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Genome:
        """Reconstrói tolerando chaves desconhecidas (evolução de schema)."""
        names = {f.name for f in fields(cls)}
        return cls(**{k: float(v) for k, v in data.items() if k in names}).clamped()

    def to_vector(self) -> list[float]:
        """Vetor ordenado de traços — representação que o DEAP manipula."""
        return [float(getattr(self, f.name)) for f in fields(self)]

    @classmethod
    def from_vector(cls, vector: list[float]) -> Genome:
        """Reconstrói a partir do vetor do DEAP, recortando às faixas válidas."""
        names = [f.name for f in fields(cls)]
        return cls(**dict(zip(names, (float(v) for v in vector), strict=True))).clamped()

    @classmethod
    def trait_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
