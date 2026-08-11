"""O dossiê é PROJEÇÃO PURA dos eventos: sem world-state, sem prosa, sem pedagogia.

É a asserção fundadora do M6. O marco inteiro se apoia numa definição de correção
— *um consumidor está correto quando o que ele afirma é derivável do event log* —
e essa definição só vale enquanto o dossiê não tiver outra fonte além da trilha.

Duas contaminações são possíveis, e as duas são silenciosas:

1. **Fato que não veio do evento.** Um número lido do world-state, uma média
   recalculada. O dossiê pareceria mais rico e deixaria de ser verificável.
2. **Prosa.** Um `cause_code` traduzido, uma frase montada, uma escolha de
   registro. Aí a fronteira entre "o que aconteceu" e "como se conta" some — e
   com ela some o critério que separa o Tutor correto do Tutor que inventa.

O teste ataca as duas: uma trilha ARBITRÁRIA (`consequences` vazio, `location`
global, `cause_detail` mínimo) tem de produzir um dossiê cujo conteúdo textual
inteiro se explique pelos eventos que entraram.
"""

from __future__ import annotations

import json

import pytest
from tests.support_context import branching_cascade, life_emerged

from ecosfera_ai.domain.consumers.factual_context import ContextSlice, FactualContext

TRAIL = (life_emerged(era=1, tick=99), *branching_cascade())
SLICE = ContextSlice.of_era(1)
CONTEXT = FactualContext.of("planet-pure", SLICE, TRAIL)


def test_every_event_in_the_dossier_came_from_the_trail() -> None:
    """Nada entra que a trilha não tenha trazido — nem um evento sintetizado."""
    assert {e.event_id for e in CONTEXT.events} == {e.event_id for e in TRAIL}


def test_the_dossier_carries_the_explainability_fields_of_the_envelope() -> None:
    """Os campos §4 chegam INTEIROS ao consumidor de cima (Spec §4, ADR-ARCH-0002).

    O dossiê não pode ser um resumo: quem vai narrar precisa da causa, do elo, do
    instante e dos números que sustentam a frase. Empobrecer aqui obrigaria o
    M6.1/M6.3 a completar de memória — que é a definição operacional de alucinar.
    """
    meteor = CONTEXT.events[1]
    payload = CONTEXT.to_dict()["events"][1]
    for required in (
        "cause_code",
        "cause_detail",
        "participants",
        "environmental_factors",
        "resources",
        "consequences",
        "correlation_id",
        "causation_id",
        "tick",
        "era",
    ):
        assert required in payload, f"o dossiê perdeu o campo §4 {required!r}"
    assert payload["cause_code"] == str(meteor.cause_code.value)


def test_the_cause_code_stays_an_enum_and_is_never_translated() -> None:
    """`cause_code` sai como veio: código estruturado, nunca frase pedagógica.

    A tradução é do consumidor (ADR-ARCH-0002, Correção 1). Um dossiê que já
    traduz decide, sozinho e cedo demais, o que a criança vai ouvir.
    """
    codes = {str(e.cause_code.value) for e in CONTEXT.events}
    assert codes <= {
        "EVENT_ONSET",
        "RADIATIVE_FORCING",
        "CATASTROPHIC_EVENT",
        "THERMAL_INTOLERANCE",
        "HABITABILITY_THRESHOLD",
    }
    for code in codes:
        assert code.isupper(), f"{code!r} não parece um enum — parece prosa"
        assert " " not in code


def test_no_prose_anywhere_in_the_serialized_dossier() -> None:
    """Varredura do JSON inteiro: nenhuma string de dossiê é uma frase.

    O critério é mecânico de propósito — nada de "parece pedagógico". Toda string
    que sai daqui é identificador, código, chave de campo ou referência
    `tipo:valor`. Uma frase em português tem espaços e minúsculas soltas, e é
    exatamente isso que o teste recusa.
    """
    payload = json.dumps(CONTEXT.to_dict(), ensure_ascii=False)
    for suspicious in ("porque", "espécie", "aluno", "aconteceu", " o ", " a "):
        assert suspicious not in payload, (
            f"o dossiê factual contém prosa ({suspicious!r}) — a frase é do M6.1/M6.3"
        )


def test_the_dossier_has_no_pedagogical_dimension() -> None:
    """Nem faixa etária, nem BNCC, nem nível de linguagem — nada disso é fato."""
    payload = CONTEXT.to_dict()
    forbidden = {"age", "age_band", "bncc", "reading_level", "summary", "explanation", "narrative"}
    assert not forbidden & set(payload), "o dossiê ganhou uma dimensão pedagógica"
    for event in payload["events"]:
        assert not forbidden & set(event)


def test_the_domain_model_cannot_reach_the_world_state() -> None:
    """A pureza afirmada como IMPORTAÇÃO, e não só como conteúdo.

    O conteúdo pode estar limpo hoje e sujar amanhã. O que impede a regressão é a
    ausência do caminho: o módulo do dossiê não tem como alcançar o world-state
    nem os Engines. O `import-linter` verifica o mesmo em CI
    (`test_consumer_reads_only_event_store`); aqui a asserção é local ao módulo.
    """
    import ecosfera_ai.domain.consumers.factual_context as module

    imported = {
        value.__module__
        for value in vars(module).values()
        if getattr(value, "__module__", None) is not None
    }
    for reached in imported:
        assert not reached.startswith("ecosfera_ai.engines"), reached
        assert not reached.startswith("ecosfera_ai.simulation_engine"), reached
        assert "world_state" not in reached, reached


def test_an_empty_trail_projects_an_empty_dossier_and_not_an_error() -> None:
    with pytest.raises(ValueError, match="from_tick"):
        ContextSlice.of_ticks(200, 100)
    assert FactualContext.of("planet-pure", SLICE, ()).is_empty
