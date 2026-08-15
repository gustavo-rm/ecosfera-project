"""BIO-005 — o vocabulário anti-teleológico, em UM lugar só.

A regra: nada no sistema atribui INTENÇÃO à evolução. As formulações do tipo
"a espécie desenvolveu resistência" são Lamarckismo com roupa nova — o organismo
mudando porque precisava. A formulação correta tem duas metades: a variação vem
ANTES e sem propósito, e o ambiente decide DEPOIS.

## Por que esta lista migrou de `tests/` para cá

Ela **já era a fonte única** — não é uma cópia da Fase 0, é a forma operacional
que a Fase 0 deu ao BIO-005. O ADR 0023 e o `configs/causal_rules.yaml` v5
enunciam a diretriz em prosa; a enumeração verificável nasceu em
`tests/unit/test_no_teleological_language.py`, e `tests/contract/
test_non_teleological_wording_preserved.py` já a IMPORTAVA de lá, afirmando
inclusive identidade de objeto para impedir que alguém a substituísse por outra.

O que mudou no M6.3 é quem precisa dela: até aqui só testes liam a lista, porque
só havia prosa determinística para conferir. Agora existe um verificador em tempo
de execução — a saída do LLM passa por ele antes de chegar ao aluno —, e código
de produção não importa de `tests/`. Mover é o que mantém a lista única; copiá-la
para `src/` criaria a segunda cópia que a Fase 0 evitou, e a que envelheceria
seria justamente a consultada por quem escrevesse a frase seguinte.

Quem acrescentar uma formulação proibida acrescenta-a AQUI, e ela passa a valer
ao mesmo tempo para os templates do M6.1, para o código, para os ADRs e para o
que o modelo gerar.

## A prosa do corpus não é uma segunda lista

`VOC-001`, no corpus pedagógico do M6.2, enuncia a mesma regra em português para
o Tutor LER — inclusive citando algumas formulações proibidas. Aquilo é material
de registro, não mecanismo de imposição, e por isso os dois artefatos coexistem
legitimamente. O que impede a deriva é `test_the_corpus_rule_matches_the_canonical_list`:
toda formulação citada na VOC-001 tem de constar desta lista.
"""

from __future__ import annotations

# Lista negra MÍNIMA: formulações que afirmam intenção, propósito ou progresso.
# Curta de propósito — uma lista longa vira ruído e ninguém a mantém.
TELEOLOGICAL: tuple[str, ...] = (
    "desenvolveu resistência",
    "desenvolveram resistência",
    "criou resistência",
    "criaram resistência",
    "desenvolveu a capacidade",
    # Acrescentadas na consolidação do M6.3, e não por gosto: a VOC-001 do corpus
    # já ENSINAVA ao Tutor que esta formulação é proibida, e a lista de imposição
    # não a alcançava — só as completações mais específicas acima. Uma frase como
    # "a espécie desenvolveu uma casca mais grossa" passaria pelo verificador
    # depois de o próprio corpus tê-la declarado errada.
    "a espécie desenvolveu",
    "as espécies desenvolveram",
    "a comunidade desenvolveu",
    "evoluiu para",
    "evoluir para",
    "evoluíram para",
    "para se adaptar",
    "a fim de se adaptar",
    "se adaptou para",
    "adaptou-se para",
    "a fim de sobreviver",
    "com o objetivo de sobreviver",
    "a espécie quis",
    "a espécie decidiu",
    "a espécie precisava",
    "a espécie precisou",
    "a natureza escolheu",
    "a evolução escolheu",
    "mais evoluída",
    "mais evoluído",
)

# Aptidão ABSOLUTA — o que a Q5 nega. Nega-se o número único que ordenaria
# espécies fora de qualquer contexto, não a aptidão, que é propriedade da RELAÇÃO
# entre a comunidade e o ambiente.
#
# Eixo distinto do anterior, e por isso lista distinta: "era inferior" não
# atribui intenção a ninguém — afirma uma ordenação que não existe. Fundi-las
# numa só faria a mensagem de erro apontar a regra errada.
ABSOLUTE_FITNESS: tuple[str, ...] = (
    "era fraca",
    "era inferior",
    "não servia",
    "menos evoluída",
    "mais evoluída",
    "não era boa o suficiente",
    "perdeu a competição da evolução",
)


def teleological_phrases_in(text: str) -> tuple[str, ...]:
    """As formulações teleológicas presentes no texto, se houver.

    Devolve TODAS as encontradas, e não a primeira: uma frase gerada pode violar
    a regra de mais de um jeito, e o M6.4 vai montar conjunto de avaliação a
    partir destes registros — saber que houve duas violações é diferente de saber
    que houve alguma.

    Sem a distinção uso × menção que os testes de código-fonte aplicam: aqui o
    texto é prosa que chega ao aluno, onde toda ocorrência é uso.
    """
    lowered = text.lower()
    return tuple(phrase for phrase in TELEOLOGICAL if phrase in lowered)


def absolute_fitness_phrases_in(text: str) -> tuple[str, ...]:
    """As formulações de aptidão absoluta presentes no texto, se houver."""
    lowered = text.lower()
    return tuple(phrase for phrase in ABSOLUTE_FITNESS if phrase in lowered)


__all__ = [
    "ABSOLUTE_FITNESS",
    "TELEOLOGICAL",
    "absolute_fitness_phrases_in",
    "teleological_phrases_in",
]
