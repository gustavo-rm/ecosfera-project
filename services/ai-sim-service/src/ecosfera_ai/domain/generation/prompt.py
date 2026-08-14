"""A especificação do prompt ancorado, carregada como DADO.

O texto que instrui o modelo vive em `configs/generation_prompt.yaml`, não
espalhado em concatenações pelo código. A razão é a mesma dos templates do M6.1,
com um agravante: corrigir a redação de uma instrução é a manutenção MAIS comum
desta camada, e se isso exigir tocar na lógica de geração, cada ajuste de palavra
passa a arriscar o caminho de recuo.

## O que a especificação decide, e o que ela não decide

Ela decide COMO se pede. Não decide o que aconteceu — isso vem do piso do M6.1 —
nem qual passagem entra, que é arbitragem do caso de uso.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SPEC_PATH = Path("configs/generation_prompt.yaml")


class MissingPromptSlotError(KeyError):
    """A especificação pede um slot que quem monta o prompt não preencheu.

    Falha alto pelo motivo de sempre nesta base: montar o prompt com o slot vazio
    mandaria ao modelo uma seção `<fatos>` em branco, e um modelo sem fatos
    escreve ciência genérica plausível — a alucinação que o M6 existe para
    impedir, produzida pelo nosso próprio descuido.
    """


@dataclass(frozen=True, slots=True)
class AnchoredPrompt:
    """O que efetivamente vai ao modelo, nas duas metades que a API espera."""

    system: str
    user: str

    def to_dict(self) -> dict[str, str]:
        return {"system": self.system, "user": self.user}


@dataclass(frozen=True, slots=True)
class PromptSpec:
    """A especificação versionada: instrução, modelo, tempo e assinaturas."""

    version: int
    model: str
    timeout_seconds: int
    system: str
    user_template: str
    event_signatures: Mapping[str, tuple[str, ...]]

    def build(self, *, floor_text: str, register_guidance: str) -> AnchoredPrompt:
        """Monta o prompt, recusando-se a mandar uma seção vazia."""
        if not floor_text.strip():
            raise MissingPromptSlotError(
                "o piso do M6.1 veio vazio; o modelo receberia <fatos> em branco e "
                "escreveria ciência genérica sem nada que a ancorasse"
            )
        try:
            user = self.user_template.format(
                floor_text=floor_text.strip(),
                register_guidance=register_guidance.strip() or "(nenhuma regra recuperada)",
            )
        except KeyError as missing:
            raise MissingPromptSlotError(
                f"a especificação pede o slot {missing.args[0]!r}, que não foi preenchido"
            ) from missing
        return AnchoredPrompt(system=self.system.strip(), user=user.strip())

    def signatures_for(self, event_type: str) -> tuple[str, ...]:
        return self.event_signatures.get(event_type, ())

    @property
    def detectable_event_types(self) -> frozenset[str]:
        """Os tipos cuja invenção esta especificação consegue detectar.

        Exposto de propósito: o conjunto é PARCIAL, e o ADR 0028 diz quais ficam
        de fora e por quê. Um verificador que escondesse a própria cobertura
        seria pior que um que não existisse.
        """
        return frozenset(self.event_signatures)


def load_prompt_spec(path: Path = DEFAULT_SPEC_PATH) -> PromptSpec:
    """Lê a especificação versionada."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    signatures = {
        str(event_type): tuple(str(term).lower() for term in terms)
        for event_type, terms in (raw.get("event_signatures") or {}).items()
    }
    return PromptSpec(
        version=int(raw.get("version", 1)),
        model=str(raw["model"]),
        timeout_seconds=int(raw.get("timeout_seconds", 60)),
        system=str(raw["system"]),
        user_template=str(raw["user"]),
        event_signatures=signatures,
    )


__all__ = [
    "DEFAULT_SPEC_PATH",
    "AnchoredPrompt",
    "MissingPromptSlotError",
    "PromptSpec",
    "load_prompt_spec",
]
