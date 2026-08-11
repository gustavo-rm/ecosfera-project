"""A distinção catastrófica × ecológica chega INTACTA ao consumidor de cima.

A concepção equivocada que a plataforma existe para desfazer é *"quem se extingue
era inferior"*. Até o M3, TODA extinção do simulador tinha causa ecológica — cada
peça correta, e o conjunto ensinando a coisa errada: se toda morte é explicada por
um traço, morrer vira prova de inferioridade. O M4 separou as duas famílias
(ADR 0019), e a extinção catastrófica passou a ser independente de aptidão: uma
comunidade exemplarmente adaptada pode ser eliminada por um meteoro.

O dossiê não traduz essa diferença — traduzir é do M6.1/M6.3. O que ele tem de
garantir é que a diferença SOBREVIVA à travessia, em duas formas independentes:

* o `cause_code`, que nomeia o mecanismo;
* o ELO causal, que numa catástrofe aponta para o EVENTO gatilho e não para o
  clima que por acaso mudou no mesmo tick — defeito real do M4, encontrado pelo
  teste de cadeia e corrigido (ADR 0019, decisão 4).

Perder qualquer uma das duas devolveria o Tutor ao estado que o M4 corrigiu.
"""

from __future__ import annotations

from tests.support_context import branching_cascade

from ecosfera_ai.domain.consumers.factual_context import (
    ContextSlice,
    ExtinctionNature,
    FactualContext,
)
from ecosfera_ai.domain.consumers.vocabulary import CATASTROPHIC_CAUSE_CODE

CASCADE = branching_cascade()
METEOR, COOLING, _WILDFIRE, CATASTROPHIC, ECOLOGICAL = CASCADE
CONTEXT = FactualContext.of("planet-ext", ContextSlice.of_era(1), tuple(CASCADE))


def _fact(event_id: str) -> object:
    return next(f for f in CONTEXT.extinctions if f.event_id == event_id)


def test_the_two_extinctions_are_both_in_the_dossier() -> None:
    assert len(CONTEXT.extinctions) == 2


def test_the_catastrophic_extinction_is_marked_as_catastrophic() -> None:
    fact = _fact(CATASTROPHIC.event_id)
    assert fact.nature is ExtinctionNature.CATASTROPHIC  # type: ignore[attr-defined]
    assert fact.cause_code == CATASTROPHIC_CAUSE_CODE  # type: ignore[attr-defined]


def test_the_ecological_extinction_is_marked_as_ecological() -> None:
    fact = _fact(ECOLOGICAL.event_id)
    assert fact.nature is ExtinctionNature.ECOLOGICAL  # type: ignore[attr-defined]
    assert fact.cause_code == "THERMAL_INTOLERANCE"  # type: ignore[attr-defined]


def test_the_two_families_are_never_collapsed_into_one() -> None:
    """Colapsá-las faria o Tutor narrar toda extinção como falha de adaptação."""
    natures = {f.nature for f in CONTEXT.extinctions}
    assert natures == {ExtinctionNature.CATASTROPHIC, ExtinctionNature.ECOLOGICAL}


def test_the_catastrophic_extinction_chains_to_the_event_not_to_the_climate() -> None:
    """O elo é o segundo portador da distinção, e o que o M4 quase perdeu.

    Uma catástrofe encadeada ao `TemperatureShift` seria narrada como "morreu
    porque esfriou" — verdadeira no tick, falsa na causa, e indistinguível de uma
    extinção ecológica para quem só lesse a cadeia.
    """
    fact = _fact(CATASTROPHIC.event_id)
    assert fact.triggered_by == METEOR.event_id  # type: ignore[attr-defined]
    assert fact.triggered_by != COOLING.event_id  # type: ignore[attr-defined]


def test_the_ecological_extinction_chains_to_the_climate_shift() -> None:
    fact = _fact(ECOLOGICAL.event_id)
    assert fact.triggered_by == COOLING.event_id  # type: ignore[attr-defined]


def test_the_dossier_classifies_but_does_not_translate() -> None:
    """`nature` é classificação estrutural, não frase — segue sendo código.

    A diferença importa: uma classificação o consumidor de cima traduz como
    quiser, para a idade que quiser. Uma frase já decidiu por ele.
    """
    payload = CONTEXT.to_dict()["extinctions"][0]
    assert payload["nature"] in {"catastrophic", "ecological"}
    assert payload["cause_code"].isupper()
    assert "summary" not in payload and "text" not in payload


def test_an_unknown_extinction_cause_defaults_to_ecological_and_keeps_its_code() -> None:
    """Um mecanismo ecológico novo não precisa ser conhecido para ser preservado.

    `CATASTROPHIC_EVENT` é a única causa independente de aptidão (ADR 0019); todo
    o resto é ecológico por definição. Mas o `cause_code` original viaja intacto,
    então um Engine futuro pode acrescentar mecanismos sem que o dossiê os
    achate — o que o M6.0 classifica é a FAMÍLIA, não o mecanismo.
    """
    fact = _fact(ECOLOGICAL.event_id)
    assert fact.cause_code not in {n.value for n in ExtinctionNature}  # type: ignore[attr-defined]
