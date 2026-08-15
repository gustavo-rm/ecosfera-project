"""O prompt é DADO versionado, inspecionável sem chamar modelo nenhum.

Mesma escolha que `causal_rules.yaml` e `explanation_templates.yaml` fizeram, e
pela razão de sempre nesta base: o texto que chega ao aluno — aqui, o texto que
governa o texto que chega ao aluno — é objeto de revisão pedagógica, não de
refatoração. Quem entende de ensino precisa poder corrigir uma instrução sem
abrir um módulo Python.

Há um agravante próprio do M6.3: a manutenção mais comum desta camada é ajustar a
redação da instrução. Se isso exigisse mexer na lógica de geração, cada correção
de palavra passaria a arriscar o caminho de recuo — que é justamente o que não
pode quebrar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from tests.support_generation import SPEC_PATH, spec

from ecosfera_ai.domain.consumers.templates import load_templates
from ecosfera_ai.domain.generation.prompt import MissingPromptSlotError, load_prompt_spec

SPEC = spec()


# --- A especificação vive fora do código --------------------------------------


def test_the_specification_is_a_versioned_file() -> None:
    assert SPEC_PATH.exists()
    assert SPEC.version >= 1
    assert SPEC.model and SPEC.timeout_seconds > 0


def test_no_prompt_text_is_hardcoded_in_the_generation_modules() -> None:
    """A instrução não pode ter uma segunda cópia no Python.

    Uma cópia no código venceria silenciosamente a do arquivo, e a revisão
    pedagógica passaria a editar um texto que não é o usado.
    """
    marker = "Regras absolutas"
    for module in sorted(Path("src/ecosfera_ai").rglob("*.py")):
        assert marker not in module.read_text(encoding="utf-8"), (
            f"{module} traz o texto da instrução embutido — ele vive no YAML"
        )


def test_the_prompt_can_be_built_and_read_without_any_model() -> None:
    """Inspecionável de fora: é o que permite revisar sem infraestrutura."""
    prompt = SPEC.build(floor_text="O piso do M6.1.", register_guidance="- uma regra")

    assert "O piso do M6.1." in prompt.user
    assert "uma regra" in prompt.user
    assert prompt.system.strip()


# --- O que a instrução tem de dizer -------------------------------------------


@pytest.mark.parametrize(
    "requirement",
    [
        "não decide o que aconteceu",  # a hierarquia
        "não houve meteoro",  # proibição de acrescentar fato
        "Não atribua intenção à evolução",  # BIO-005
        "não seleciona",  # catastrófica × ecológica
        "superiores",  # aptidão absoluta
    ],
)
def test_the_instruction_states_every_constraint_the_verifier_enforces(requirement: str) -> None:
    """Pedir e conferir têm de falar da mesma coisa.

    O verificador reprova saída teleológica; se a instrução não a proibisse,
    estaríamos punindo o modelo por uma regra que ninguém lhe deu — e o recuo
    viraria o caminho comum em vez da exceção.

    Sem sensibilidade a maiúsculas: a instrução as usa para dar ênfase ao modelo
    ("Você NÃO decide"), e cobrar a grafia exata faria este teste quebrar numa
    revisão de redação que não mudou regra alguma.
    """
    assert requirement.lower() in SPEC.system.lower()


def test_the_slice_of_facts_is_delimited_so_the_two_blocks_cannot_merge() -> None:
    """Sem delimitador, um bloco encostaria no outro e a hierarquia sumiria."""
    prompt = SPEC.build(floor_text="FATO", register_guidance="REGRA")
    assert re.search(r"<fatos>\s*FATO\s*</fatos>", prompt.user)
    assert re.search(r"<registro>\s*REGRA\s*</registro>", prompt.user)


# --- A recusa de montar um prompt sem fatos -----------------------------------


@pytest.mark.parametrize("empty", ["", "   ", "\n\t "])
def test_building_without_facts_is_refused(empty: str) -> None:
    """`<fatos>` em branco faria o modelo escrever ciência genérica plausível."""
    with pytest.raises(MissingPromptSlotError):
        SPEC.build(floor_text=empty, register_guidance="- uma regra")


def test_missing_register_guidance_is_allowed_and_stated() -> None:
    """Não recuperar nada é legítimo; fingir que recuperou não seria."""
    prompt = SPEC.build(floor_text="O piso.", register_guidance="")
    assert "nenhuma regra recuperada" in prompt.user


# --- As assinaturas de evento são dado, e não fantasia ------------------------


def test_event_signatures_come_from_the_m6_1_vocabulary() -> None:
    """Todo termo de assinatura tem de existir no substantivo que o M6.1 já usa.

    É o que impede a lista de virar invenção: sem esta amarra, alguém poderia
    escrever "vulcão" ali e o verificador passaria a procurar uma palavra que a
    explicação nunca produz — dando cobertura aparente sem cobertura real.
    """
    nouns = load_templates(Path("configs/explanation_templates.yaml")).nouns

    for event_type, terms in SPEC.event_signatures.items():
        assert event_type in nouns, f"{event_type} não tem substantivo no vocabulário do M6.1"
        for term in terms:
            assert term in nouns[event_type].lower(), (
                f"a assinatura {term!r} não aparece em {nouns[event_type]!r}"
            )


def test_the_uncovered_event_types_are_declared_in_the_file() -> None:
    """A cobertura é PARCIAL, e o arquivo diz quais tipos ficam de fora.

    Um verificador que escondesse a própria cobertura seria pior que um que não
    existisse: daria confiança onde não há.
    """
    raw = SPEC_PATH.read_text(encoding="utf-8")
    for uncovered in ("TemperatureShift", "PopulationDeclined", "SpeciationOccurred"):
        assert uncovered in raw, f"{uncovered} não é detectável e isso não está declarado"
        assert uncovered not in SPEC.event_signatures


def test_a_broken_specification_fails_loudly(tmp_path: Path) -> None:
    """Falta de campo obrigatório estoura ao carregar, e não na primeira geração."""
    broken = tmp_path / "sem_modelo.yaml"
    broken.write_text(yaml.safe_dump({"version": 1, "system": "s", "user": "u"}), encoding="utf-8")

    with pytest.raises(KeyError):
        load_prompt_spec(broken)
