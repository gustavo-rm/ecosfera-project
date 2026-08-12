"""Os templates de explicação como DADO versionado — texto fora do código.

Mesma escolha que `configs/causal_rules.yaml` fez no MVP e pela mesma razão: a
frase que chega ao aluno é objeto de revisão PEDAGÓGICA, não de refatoração.
Quem entende de ensino precisa poder corrigir uma palavra sem abrir um módulo
Python, e sem que a correção arraste a lógica de seleção junto.

O arquivo traz três coisas, e a separação entre elas importa:

* **`nouns`** — como um `event_type` se chama em português. Vocabulário puro.
* **`mechanisms`** — como um `cause_code` vira oração causal. É aqui que o enum
  neutro do Engine finalmente encontra a prosa, e em nenhum lugar antes
  (ADR-ARCH-0002, Correção 1).
* **`templates`** — a frase, com slots.

Nenhum dos três decide O QUE aconteceu: isso já está decidido no dossiê do M6.0.
Eles decidem apenas COMO se conta.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ecosfera_ai.domain.consumers.explanation import Register


class MissingTemplateError(KeyError):
    """O renderizador pediu um template que o arquivo não tem.

    Falha alto, e a razão é a de sempre nesta base: a degradação silenciosa seria
    pular o fato, e um fato pulado é um acontecimento do planeta sobre o qual o
    Tutor simplesmente emudece. Ausência não se denuncia sozinha.
    """


class MissingSlotError(KeyError):
    """O template pede um slot que o dossiê não preencheu.

    É o guarda contra a alucinação por descuido: renderizar com o slot vazio (ou
    com um valor plausível qualquer) produziria uma frase bem formada afirmando
    algo que o Event Store não contém.
    """


@dataclass(frozen=True, slots=True)
class ExplanationTemplate:
    """Uma frase parametrizada, num registro de leitura."""

    template_id: str
    register: Register
    text: str

    def render(self, slots: Mapping[str, str]) -> str:
        """Substitui os slots, recusando-se a inventar o que falta."""
        try:
            rendered = self.text.format(**slots)
        except KeyError as missing:
            raise MissingSlotError(
                f"o template {self.template_id!r} pede o slot {missing.args[0]!r}, "
                "que o dossiê não preencheu — a frase seria uma afirmação sem origem"
            ) from missing
        return " ".join(rendered.split())


@dataclass(frozen=True, slots=True)
class TemplateSet:
    """Os templates carregados, indexados por (id, registro)."""

    version: int
    templates: Mapping[tuple[str, Register], ExplanationTemplate]
    nouns: Mapping[str, str]
    mechanisms: Mapping[str, str]
    # Códigos que nunca chegam ao aluno (moldura, diagnóstico). Declarados para
    # que a ausência de frase seja DECISÃO registrada, e não lacuna silenciosa.
    not_narrated: frozenset[str] = frozenset()

    def get(self, template_id: str, register: Register) -> ExplanationTemplate:
        """Busca o template no registro pedido, CAINDO para `STANDARD`.

        O recuo é o que torna a costura de registro extensível linha a linha: o
        M6.3 acrescenta uma variante nova ao YAML e ela passa a valer, sem que
        nenhum template existente precise ganhar variante ao mesmo tempo.
        """
        found = self.templates.get((template_id, register))
        if found is None:
            found = self.templates.get((template_id, Register.STANDARD))
        if found is None:
            raise MissingTemplateError(
                f"nenhum template {template_id!r} em registro algum — "
                "um acontecimento do planeta ficaria sem narração"
            )
        return found

    def noun_for(self, event_type: str) -> str | None:
        """O substantivo do tipo de evento, ou None quando não há vocabulário.

        None não é erro: o Event Store cresce com Engines novos, e um tipo que o
        vocabulário ainda não conhece deve ser SILENCIADO, nunca narrado com um
        nome inventado. O consumidor pula o que não sabe dizer — a mesma regra
        que `EventTranslation.observations` já aplica desde o M1.
        """
        return self.nouns.get(event_type)

    def mechanism_for(self, cause_code: str) -> str | None:
        """A oração causal do `cause_code`, ou None quando não há vocabulário."""
        return self.mechanisms.get(cause_code)


def load_templates(path: Path) -> TemplateSet:
    """Lê o arquivo versionado de templates."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    templates: dict[tuple[str, Register], ExplanationTemplate] = {}
    for entry in raw.get("templates", []):
        register = Register(str(entry.get("register", Register.STANDARD.value)))
        template = ExplanationTemplate(
            template_id=str(entry["id"]),
            register=register,
            text=" ".join(str(entry["text"]).split()),
        )
        templates[(template.template_id, register)] = template
    return TemplateSet(
        version=int(raw.get("version", 1)),
        templates=templates,
        nouns={str(k): str(v) for k, v in (raw.get("nouns") or {}).items()},
        mechanisms={str(k): str(v) for k, v in (raw.get("mechanisms") or {}).items()},
        not_narrated=frozenset(str(code) for code in (raw.get("not_narrated") or ())),
    )


__all__ = [
    "ExplanationTemplate",
    "MissingSlotError",
    "MissingTemplateError",
    "TemplateSet",
    "load_templates",
]
