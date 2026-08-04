"""Série temporal de um escalar ao longo de uma corrida — a ferramenta que faltou.

O M4 descobriu que o carbono não tem equilíbrio de longo prazo (ADR 0020) e não
conseguiu mostrar isso a ninguém: a suíte verificava correção POR TICK, e o
colapso só aparece na TRAJETÓRIA. Faltava exatamente isto — um jeito de extrair a
série de um reservatório ao longo de centenas de ticks e olhar para ela.

Este módulo **não analisa e não corrige nada**. Ele torna a dívida OBSERVÁVEL e
EXPORTÁVEL, que é o que o M5 se propõe: instrumentar, não consertar.

## Por que os fluxos de carbono, e não só o estoque

Ver o CO₂ subir diz QUE o carbono escapa; não diz ONDE. O diagnóstico futuro
precisa dos termos separados — desgaseificação (Geology), estoque atmosférico
(Atmosphere), troca ar↔oceano e solo (Chemistry), sumidouro biótico (a biomassa
que a Atmosphere absorve). Com os quatro em série, some-se entrada e saída e
vê-se qual termo não fecha. Com só o estoque, não.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from ecosfera_ai.shared_kernel.world_state import WorldStateSnapshot

# Séries do CICLO DO CARBONO. As chaves são os nomes que o diagnóstico futuro vai
# procurar; os extratores leem o world-state e nada além dele.
CARBON_CHANNELS: Mapping[str, Callable[[WorldStateSnapshot], float]] = {
    # Fonte: desgaseificação vulcânica (basal + supervulcanismo, ADR 0018).
    "geology_outgassing": lambda s: s.geology.co2_flux,
    # Estoque atmosférico — o número que dispara o alarme.
    "atmosphere_co2": lambda s: s.atmosphere.co2,
    # Reservatórios não-atmosféricos.
    "ocean_carbon": lambda s: s.chemistry.ocean_carbon,
    "soil_carbon": lambda s: s.chemistry.soil_carbon,
    # Troca ar<->oceano: um fluxo ÚNICO, somado a um lado e subtraído do outro.
    "air_sea_flux": lambda s: s.chemistry.air_sea_flux,
    # Sumidouro biótico: a Atmosphere absorve proporcionalmente à biomassa.
    "biomass": lambda s: s.biota.biomass,
    # Contexto mínimo para interpretar os anteriores.
    "temperature": lambda s: s.climate.temperature,
}


@dataclass(frozen=True, slots=True)
class TimeSeries:
    """Uma corrida, canal a canal, tick a tick."""

    planet_id: str
    seed: int
    ticks: Sequence[int] = field(default_factory=tuple)
    channels: Mapping[str, Sequence[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, values in self.channels.items():
            if len(values) != len(self.ticks):
                raise ValueError(
                    f"canal {name!r} tem {len(values)} pontos para {len(self.ticks)} ticks; "
                    "uma série desalinhada mentiria sobre QUANDO cada valor ocorreu"
                )

    def channel(self, name: str) -> Sequence[float]:
        return self.channels[name]

    def to_csv(self) -> str:
        """CSV — o formato que abre em qualquer planilha ou notebook.

        A finalidade é ser ABERTO por um humano investigando a dívida; um formato
        que exija ferramenta própria não serviria.
        """
        buffer = io.StringIO()
        names = sorted(self.channels)
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["tick", *names])
        for index, tick in enumerate(self.ticks):
            writer.writerow([tick, *(self.channels[name][index] for name in names)])
        return buffer.getvalue()

    def to_json(self) -> str:
        return json.dumps(
            {
                "planet_id": self.planet_id,
                "seed": self.seed,
                "ticks": list(self.ticks),
                "channels": {k: list(v) for k, v in self.channels.items()},
            },
            sort_keys=True,
            ensure_ascii=False,
        )


def collect(
    snapshots: Iterable[WorldStateSnapshot],
    *,
    channels: Mapping[str, Callable[[WorldStateSnapshot], float]] = CARBON_CHANNELS,
    planet_id: str = "",
    seed: int = 0,
) -> TimeSeries:
    """Extrai as séries de uma trajetória JÁ EXECUTADA.

    Consome snapshots; não roda tick. É observação lateral — a mesma disciplina
    do sink de observabilidade, que só é chamado depois de o tick fechar.
    """
    ticks: list[int] = []
    collected: dict[str, list[float]] = {name: [] for name in channels}
    identifier, run_seed = planet_id, seed

    for snapshot in snapshots:
        ticks.append(snapshot.tick)
        identifier = identifier or snapshot.planet_id
        run_seed = run_seed or snapshot.seed
        for name, extract in channels.items():
            collected[name].append(float(extract(snapshot)))

    return TimeSeries(
        planet_id=identifier,
        seed=run_seed,
        ticks=tuple(ticks),
        channels={name: tuple(values) for name, values in collected.items()},
    )
