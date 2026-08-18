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


class MalformedVariantError(ValueError):
    """As formas de um mesmo template não numeram 0, 1, 2, … sem buracos.

    Falha no CARREGAMENTO, e não na renderização, porque o custo do silêncio aqui
    é alto e tardio: até o M6.5 duas entradas com o mesmo `id` e `register`
    simplesmente se sobrescreviam no dicionário, e a segunda vencia. Uma revisão
    pedagógica que duplicasse um id por engano perdia uma frase sem aviso, e o
    sintoma só apareceria como "aquele texto que eu escrevi não está no ar".

    Com formas alternativas isso deixa de ser hipótese: passa a ser o jeito
    normal de escrever no arquivo, e o modo de errar mais provável é numerar
    errado. Um `variant: 2` sem o `variant: 1` produziria uma tupla de dois
    elementos em que a posição 1 é o texto que o autor numerou como 2 — variação
    silenciosamente diferente da escrita.
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
    """Os templates carregados, indexados por (id, registro).

    O valor é uma TUPLA de formas, e não uma frase só. Quase todo template tem
    uma forma; a família da cascata tem três, porque um piso que repete a si
    mesmo faz o M6.3 devolver quase-cópia em vez de paráfrase (ADR 0029, M6.5).
    """

    version: int
    templates: Mapping[tuple[str, Register], tuple[ExplanationTemplate, ...]]
    nouns: Mapping[str, str]
    mechanisms: Mapping[str, str]
    # Códigos que nunca chegam ao aluno (moldura, diagnóstico). Declarados para
    # que a ausência de frase seja DECISÃO registrada, e não lacuna silenciosa.
    not_narrated: frozenset[str] = frozenset()

    def get(self, template_id: str, register: Register, *, variant: int = 0) -> ExplanationTemplate:
        """Busca o template no registro pedido, CAINDO para `STANDARD`.

        O recuo é o que torna a costura de registro extensível linha a linha: o
        M6.3 acrescenta uma variante nova ao YAML e ela passa a valer, sem que
        nenhum template existente precise ganhar variante ao mesmo tempo.

        `variant` é reduzido módulo o número de formas, e a razão é a mesma que
        justifica o recuo de registro: quem chama não deveria precisar saber
        quantas formas um template tem para pedir a frase. Um template de forma
        única devolve sempre a mesma frase, qualquer que seja o índice — que é
        exatamente o comportamento anterior ao M6.5, preservado por construção.
        """
        forms = self.templates.get((template_id, register))
        if not forms:
            forms = self.templates.get((template_id, Register.STANDARD))
        if not forms:
            raise MissingTemplateError(
                f"nenhum template {template_id!r} em registro algum — "
                "um acontecimento do planeta ficaria sem narração"
            )
        return forms[variant % len(forms)]

    def variants_of(self, template_id: str, register: Register) -> tuple[ExplanationTemplate, ...]:
        """Todas as formas daquele template, na ordem em que foram numeradas.

        Existe para que os testes possam cobrar de CADA forma o que cobram da
        primeira — a lição do ADR 0019, o vocabulário da Fase 0, os slots. Sem
        isto, acrescentar uma forma seria acrescentar prosa que chega ao aluno
        sem passar por verificação alguma, que é precisamente o risco que este
        arquivo inteiro existe para conter.
        """
        return self.templates.get((template_id, register), ())

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
    """Lê o arquivo versionado de templates, com as formas de cada um em ordem."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    numbered: dict[tuple[str, Register], dict[int, ExplanationTemplate]] = {}

    for entry in raw.get("templates", []):
        register = Register(str(entry.get("register", Register.STANDARD.value)))
        template = ExplanationTemplate(
            template_id=str(entry["id"]),
            register=register,
            text=" ".join(str(entry["text"]).split()),
        )
        variant = int(entry.get("variant", 0))
        forms = numbered.setdefault((template.template_id, register), {})
        if variant in forms:
            raise MalformedVariantError(
                f"{template.template_id} ({register.value}) declara duas vezes a forma "
                f"{variant} — uma delas nunca chegaria a aluno algum"
            )
        forms[variant] = template

    templates: dict[tuple[str, Register], tuple[ExplanationTemplate, ...]] = {}
    for key, forms in numbered.items():
        expected = set(range(len(forms)))
        if set(forms) != expected:
            raise MalformedVariantError(
                f"{key[0]} ({key[1].value}) numera as formas {sorted(forms)}, e não "
                f"{sorted(expected)} — a escolha por posição leria a frase errada"
            )
        templates[key] = tuple(forms[index] for index in sorted(forms))

    return TemplateSet(
        version=int(raw.get("version", 1)),
        templates=templates,
        nouns={str(k): str(v) for k, v in (raw.get("nouns") or {}).items()},
        mechanisms={str(k): str(v) for k, v in (raw.get("mechanisms") or {}).items()},
        not_narrated=frozenset(str(code) for code in (raw.get("not_narrated") or ())),
    )


__all__ = [
    "ExplanationTemplate",
    "MalformedVariantError",
    "MissingSlotError",
    "MissingTemplateError",
    "TemplateSet",
    "load_templates",
]
