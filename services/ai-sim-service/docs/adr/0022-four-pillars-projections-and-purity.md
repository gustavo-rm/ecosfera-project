# ADR 0022 — Quatro pilares, três projeções, e a pureza preservada

## Status
Aceito. Fecha o M5 junto com o **ADR 0021**. Referências: Spec §6, ADR-ARCH-0002,
ADR 0020 (dívida de carbono).

## Decisão

### 1. Três projeções sobre UMA fonte de verdade

O ADR-ARCH-0002 fala em "três públicos, uma fonte de verdade". O M5 entrega:

| Projeção | Para quem | Conteúdo |
| --- | --- | --- |
| **Científica** | pesquisa, replay, professor avançado | o fenômeno, ordenado por tempo de SIMULAÇÃO — não por ordem de chegada, que é acidente de execução |
| **Técnica** | operação, diagnóstico | só `DiagnosticEvent`: orçamento estourado, invariante violada |
| **Educacional** | aluno | **NÃO implementada — é do M6** |

Científica e técnica **particionam** a trilha: nada some, nada duplica, e o teste
afirma isso somando as duas. A separação não é organizacional — é para que o
pesquisador nunca trate um estouro de orçamento como fenômeno do planeta.

Da educacional, o M5 garante só o que lhe cabe garantir: que o envelope carrega
tudo de que ela precisará (mecanismo, elo causal, instante, números que sustentam
a frase). Descobrir uma falta no M6 seria descobrir tarde.

### 2. O contrato de query, sem consumidores

O M5 entrega a SUPERFÍCIE de leitura — por planeta, era, janela de ticks,
correlação, causação, `cause_code`, Engine, tipo — mais o passeio da cadeia
causal do efeito até a raiz.

**Não implementa consumidores de propósito.** Fazê-lo agora fixaria decisões de
produto ainda abertas (o que `/species` significa —
`docs/decisions/pending.md`). O M6 assina o contrato sem renegociar o formato.

Diagnóstico técnico fica **fora por padrão** na consulta: quem quiser vê-lo pede.

### 3. A pureza é invariante, e o M5 é o marco que mais poderia quebrá-la

Consolidar observabilidade convida a fechar o laço: "o Diretor podia olhar as
métricas", "o Engine podia consultar a trilha". Qualquer um desses laços **mata o
replay**, porque trilha e métrica são EFEITO da execução, não entrada dela.

A emissão continua determinística e dentro do loop; a consumação — persistir,
projetar, exportar — é lateral e fora dele.

Afirmado de duas formas: **estruturalmente** (nenhum Engine importa a camada de
plataforma, verificado por AST) e **funcionalmente** (rodar com e sem sink produz
trajetórias bit-a-bit idênticas). A segunda é a que pega o laço sutil — um import
pode ser inocente; uma trajetória que muda quando se liga a observação, não.

### 4. A dívida de carbono fica INSTRUMENTADA, não corrigida

O M4 mediu que o CO₂ não tem equilíbrio de longo prazo (ADR 0020) e **não tinha
como mostrar**: a suíte verificava correção por tick, e o colapso só aparece na
trajetória. Faltava a ferramenta.

O M5 entrega a série temporal: os termos do ciclo do carbono **separados** —
desgaseificação, estoque atmosférico, oceano, solo, troca ar↔oceano, sumidouro
biótico —, porque ver o CO₂ subir diz QUE o carbono escapa e não ONDE. Com os
termos em série, soma-se entrada e saída e vê-se qual não fecha.

Exporta em CSV, deliberadamente: quem investiga a dívida é um humano com uma
planilha, e um formato que exija ferramenta própria não serviria.

**O teste correspondente roda 900 ticks — além do horizonte válido de ~500 — e
não afirma NADA sobre estabilidade.** Afirmar seria esconder a dívida sob um
teste verde. Ele afirma que a série que a REVELA está íntegra. A instabilidade
segue como `xfail` anotado, e continua sendo marco próprio.

## Consequências

**Ganhamos.** A dívida deixou de ser um parágrafo num ADR e virou um artefato que
se abre e se olha. Quem for consertá-la começa com os dados, não com uma
reprodução do zero.

**Perdemos.** A série é coletada de snapshots já executados, o que significa
guardar a trajetória em memória durante a corrida. Para 900 ticks é trivial; para
corridas muito longas precisará de streaming — e aí será decisão do marco que
precisar dela.
