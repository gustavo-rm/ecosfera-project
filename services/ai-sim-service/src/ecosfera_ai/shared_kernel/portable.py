"""Artefato PORTÁVEL de uma simulação: export, import e verificação de replay.

É o critério de conclusão do M5 na Spec §8. Uma simulação deixa de viver só no
banco de quem a rodou e passa a ser um arquivo que atravessa máquinas: o
pesquisador leva a corrida para analisar, o professor recebe o planeta da turma,
e um bug de campo vira um artefato anexado ao relato.

## O que o artefato carrega, e por que cada peça

  - **seed + params**: sem eles o replay não reproduz nada. A versão dos
    parâmetros vai junto porque recalibrar a ciência muda a trajetória — importar
    numa versão diferente tem de ser detectável, não silencioso.
  - **world_state_version**: a mesma razão, do lado do esquema. Um checkpoint da
    versão 3 lido como 5 traria fatias ausentes; o artefato diz sob qual formato
    foi escrito (RF-016).
  - **checkpoints por era**: os pontos de partida do replay.
  - **event log**: o Canal B íntegro, envelope §4 completo — é dele que a cadeia
    causal e as três projeções (ADR-ARCH-0002) são reconstruídas.

## O que ele NÃO carrega

Nenhum dado de aluno. O artefato é da SIMULAÇÃO — planeta, física, biologia. A
telemetria pedagógica (RF-071) vive noutra trilha, com consentimento e retenção
próprios (RNF-009), e misturá-las aqui faria de todo export de pesquisa um
export de dado pessoal.

## Pureza

Este módulo é dado e serialização — não roda tick, não conhece Engine, não lê
métrica. Quem reproduz é o motor de replay de sempre (Spec §7); aqui só se
constrói e se confere o pacote.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ecosfera_ai.shared_kernel.events import DomainEvent, event_from_dict, event_to_dict
from ecosfera_ai.shared_kernel.world_state import WORLD_STATE_VERSION

# Versão do FORMATO do artefato — distinta da versão do world-state. O formato
# pode ganhar um campo sem que o esquema do mundo mude, e vice-versa.
EXPORT_FORMAT_VERSION = 1


class IncompatibleExportError(ValueError):
    """O artefato não pode ser importado com segurança nesta versão.

    Falhar alto é deliberado. Um import silenciosamente degradado produziria um
    planeta parecido com o original e diferente dele — e a diferença só
    apareceria como divergência de replay muito depois, quando ninguém mais
    associa a causa.
    """


@dataclass(frozen=True, slots=True)
class SimulationExport:
    """Uma simulação inteira, portável e versionada."""

    planet_id: str
    seed: int
    world_state_version: int
    params_version: int
    format_version: int = EXPORT_FORMAT_VERSION
    # Estado por era: `{era: PlanetState.to_dict()}` — as âncoras do replay.
    checkpoints: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    # Canal B íntegro, na ordem de emissão.
    events: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self, *, indent: int | None = None) -> str:
        """Serializa de forma DETERMINÍSTICA (chaves ordenadas).

        Duas exportações da mesma simulação têm de dar byte a byte o mesmo
        arquivo — é o que permite comparar artefatos por hash e detectar deriva
        sem reimportar.
        """
        return json.dumps(
            {
                "format_version": self.format_version,
                "planet_id": self.planet_id,
                "seed": self.seed,
                "world_state_version": self.world_state_version,
                "params_version": self.params_version,
                "checkpoints": dict(self.checkpoints),
                "events": list(self.events),
                "metadata": dict(self.metadata),
            },
            sort_keys=True,
            indent=indent,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, raw: str) -> SimulationExport:
        data: dict[str, Any] = json.loads(raw)
        found = int(data.get("format_version", 0))
        if found != EXPORT_FORMAT_VERSION:
            raise IncompatibleExportError(
                f"artefato no formato {found}; esta versão lê {EXPORT_FORMAT_VERSION}"
            )

        world_version = int(data["world_state_version"])
        if world_version != WORLD_STATE_VERSION:
            raise IncompatibleExportError(
                f"artefato gravado com world-state v{world_version}; esta versão é "
                f"v{WORLD_STATE_VERSION}. Importar assim traria fatias ausentes ou "
                "sobrando, e a divergência só apareceria no replay"
            )

        return cls(
            planet_id=str(data["planet_id"]),
            seed=int(data["seed"]),
            world_state_version=world_version,
            params_version=int(data["params_version"]),
            format_version=found,
            checkpoints=dict(data.get("checkpoints", {})),
            events=tuple(data.get("events", ())),
            metadata=dict(data.get("metadata", {})),
        )

    # --- Canal B ---------------------------------------------------------------

    def domain_events(self) -> list[DomainEvent]:
        """Reconstrói os eventos como objetos de domínio."""
        return [event_from_dict(entry) for entry in self.events]

    @staticmethod
    def encode_events(events: Sequence[DomainEvent]) -> tuple[Mapping[str, Any], ...]:
        return tuple(event_to_dict(event) for event in events)

    # --- Conferência -----------------------------------------------------------

    def eras(self) -> list[int]:
        return sorted(int(era) for era in self.checkpoints)

    def checkpoint(self, era: int) -> Mapping[str, Any]:
        entry = self.checkpoints.get(str(era))
        if entry is None:
            raise KeyError(f"o artefato não traz checkpoint da era {era}")
        return entry
