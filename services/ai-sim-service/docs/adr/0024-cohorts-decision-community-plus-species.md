# ADR 0024 — Coortes: comunidade **e** espécies, não uma escolha entre as duas

## Status
Aceito — **decisão, não implementação**. Fecha a **P-01** de
`docs/decisions/pending.md`, aberta desde o M3. Aplica **BIO-003** do
`PLANO_EVOLUCAO_ECOSFERA.md`. Referências: ADR-ARCH-0001, ADR 0016 (genoma médio),
ADR 0017 (os dois caminhos e o bloqueio do tempo 2), ADR 0023 (ancestral comum),
auditoria de conformidade de 2026-07-29 (DEC-04).

## Contexto

A **P-01** perguntava o que `/species` significa para o aluno, e estava travada
desde o M3 por um achado de modelagem: **o Evolution Engine não tem espécies**.
Ele modela a comunidade como um genoma médio; `species_richness` é um float — uma
contagem, não um conjunto de identidades. Uma projeção só projeta o que existe a
montante, e não há como derivar um censo de espécies coexistentes, com população
e linhagem, de uma série de eventos sobre uma média.

O ADR 0017 registrou duas saídas (códex como linhagem da comunidade × coortes por
espécie no Engine) e devolveu a escolha ao dono do produto, porque ela decide o
que o aluno VÊ, não como o código fica.

A decisão vinha atrasada por um motivo que o Plano de Evolução tornou explícito:
ela **condiciona o M6**. O Tutor precisa saber se fala da "comunidade" ou da
"espécie X" — é isso que separa `TUT-001` (explicação ancorada no estado
observável, viável já) de `TUT-002` (contraste entre espécies: *"a Alpha dependia
de água fria e desapareceu; a Beta tolerava o calor e sobreviveu"*), que depende
de espécies existirem.

## Decisão

**Comunidade + espécies. As duas, em camadas — e não uma escolha entre elas.**

### 1. A comunidade continua sendo o MECANISMO evolutivo

O modelo de comunidade/população do ADR 0016 **não é substituído**. Ele é o motor:
a seleção local, a deriva do genoma médio, a extinção, a especiação por ancestral
comum (ADR 0023) — tudo continua acontecendo sobre a comunidade, no tick, dentro
da pureza de que o replay bit-a-bit depende.

Isto é a metade da decisão que mais importa proteger. Trocar o mecanismo pela
representação seria refazer o M3 inteiro para ganhar uma lista, e perderia a
propriedade que dá sentido ao projeto: a evolução emergindo de interação local,
sem otimização teleológica (ADR-ARCH-0001).

### 2. As espécies com identidade são uma camada de INVESTIGAÇÃO, OPCIONAL

Uma camada **sobre** o mecanismo: catálogo nomeável, contagem, filogenia
simplificada por ancestral comum. Ela enriquece; não substitui.

Três qualificadores fazem parte da decisão, e não são detalhes de implementação:

- **Opcional** — é atividade de investigação, não caminho obrigatório. Nada da
  dinâmica populacional depende dela.
- **Poucas espécies** — o Plano é explícito sobre carga cognitiva: excesso de
  espécies e de indicadores simultâneos é risco pedagógico declarado.
- **Filogenia simplificada** — árvore de ancestral comum apropriada à idade, e
  não todas as gerações. Árvores filogenéticas completas estão **fora de escopo**.

### 3. A implementação é PÓS-M6. Esta fase registra a decisão e nada mais

A Fase 0 é o pré-requisito do Tutor, e o que bloqueia o Tutor é a **decisão** —
saber de quem ele fala —, não a camada existir. Implementá-la agora seria a
reescrita que a própria auditoria de conformidade chama de *"distância de
arquitetura, não de refatoração"* (DEC-04: coortes em arrays colunares, malha
geodésica), no marco cujo objetivo é corrigir conceitos baratos e de alto impacto.

O que a Fase 0 fez, e só isso: garantiu que o **modelo de evento é compatível com
a decisão**. O `SpeciationOccurred` do ADR 0023 nomeia papéis
(`ancestor:` / `lineage:`) e não identidades de espécie, justamente porque o
modelo de comunidade não tem identidades — e inventá-las no envelope seria
antecipar a camada por baixo do pano, com o custo de um contrato que a simulação
não sustenta.

### 4. O que o M6 assume, explicitamente

- **O Tutor fala da COMUNIDADE.** É o que o modelo atual sustenta com honestidade:
  "a comunidade perdeu biomassa porque o calor passou do que ela tolera", "uma
  população ancestral se dividiu em duas linhagens".
- **`TUT-002` fica adiado, e a razão é esta**, não esquecimento. O contraste entre
  espécies exige espécies; ele entra quando a camada entrar.
- **`/species` permanece servido pelo caminho B dormente até o tempo 3 do
  ADR 0017.** O estado honesto continua sendo o que o ADR 0017 já registrou: o
  catálogo antigo está desativado porque a ciência dele é inválida, e o novo
  depende desta camada.

## Alternativas consideradas

- **Só comunidade (recusar a camada de espécies).** Rejeitada: fecharia
  `TUT-002`, o catálogo e a biodiversidade como objeto de investigação — três
  coisas que o Plano quer e que a especialista sustenta.
- **Só espécies (substituir o mecanismo).** Rejeitada: desfaz o ADR 0016 e a
  decisão adicional do ADR-ARCH-0001. É a inversão que o Plano nomeia ao dizer
  "não substituir o mecanismo pela representação".
- **Códex como linhagem da comunidade** (saída 1 do ADR 0017). Não rejeitada —
  **absorvida**: é a leitura de filogenia simplificada que a camada pode adotar
  quando for implementada. O que muda é que ela deixa de ser uma alternativa
  concorrente e passa a ser uma forma possível dentro de "comunidade + espécies".
- **Implementar a camada já na Fase 0.** Rejeitada: escopo. A Fase 0 existe para
  corrigir a ciência que o Tutor vai narrar, e a ausência da camada não faz o
  Tutor narrar nada errado — faz narrar menos.

## Consequências

**Ganhamos.** A P-01 deixa de bloquear o M6: o Tutor sabe de quem fala. E a
decisão preserva o mecanismo emergente, que era o risco real de resolvê-la na
direção oposta.

**Perdemos.** `TUT-002` e `BIO-004` (filogenia visual) ficam fora do M6. O
`/species` continua sem fonte válida por mais um marco — custo já aceito no
ADR 0017 e agora com prazo declarado.

**Fica em aberto.** A FORMA da camada (censo de coortes por espécie × linhagem da
comunidade no tempo) e o marco que a implementa. É a Fase 2 do Plano de Evolução,
e ela depende da Fase 1 (relações ecológicas) apenas na ordem, não na técnica.
