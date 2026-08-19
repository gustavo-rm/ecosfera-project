# Decisões PENDENTES — bloqueadores de marcos futuros

Registro do que está explicitamente **em aberto**, para que não vire silêncio.

---

## P-01 — O que `/species` significa para o aluno

**Estado: FECHADA** pela Fase 0 — decisão **BIO-003** do
`PLANO_EVOLUCAO_ECOSFERA.md`, registrada no **ADR 0024**.

**A resposta: comunidade + espécies, e não uma escolha entre as duas.** A
comunidade continua sendo o MECANISMO evolutivo (ADR 0016 preservado); espécies
com identidade entram como camada de INVESTIGAÇÃO **opcional** — poucas espécies,
filogenia simplificada por ancestral comum. A **implementação da camada é
pós-M6**; o que a Fase 0 precisava era da decisão, porque é ela que define se o
Tutor fala de "comunidade" ou de "espécie X".

**Consequências imediatas:** o Tutor do M6 fala da COMUNIDADE; `TUT-002`
(contraste entre espécies) fica adiado com razão declarada; `/species` segue
servido pelo caminho B dormente até o tempo 3 do ADR 0017.

O registro abaixo é mantido como o **contexto** que levou à decisão — não é mais
uma pergunta em aberto.

**Segue em aberto, e é outra pergunta:** a FORMA da camada (censo de coortes por
espécie × linhagem da comunidade no tempo) e o marco que a implementa. É a Fase 2
do Plano de Evolução.

### O impasse (registro HISTÓRICO — resolvido pelo ADR 0024)

> Uma frase abaixo envelheceu e a correção importa: `SpeciationOccurred` **não**
> nomeia mais `species:community`. Desde a Fase 0 (BIO-001, ADR 0023) ele nomeia
> um `ancestor:` e duas `lineage:`, com a causa da divisão no `cause_code`. O
> achado de fundo continua verdadeiro — o Engine não tem IDENTIDADES de espécie,
> e é por isso que os papéis do evento são papéis, e não nomes.

O `/species` hoje é servido pelo caminho de biologia por era
(`simulation_engine/biology/`), que está **DORMENTE** desde o M3
(`biology_enabled=False`, ADR 0017) porque roda um AG com aptidão escalar que a
DEC-01 proíbe.

Reparentar o códex sobre os eventos do Evolution Engine — o plano do ADR 0017,
tempo 2 — esbarrou num achado de modelagem: **o Evolution Engine não tem
espécies**. Ele modela a comunidade como UM genoma médio (ADR 0016); todo evento
seu nomeia `species:community`, e `species_richness` é um escalar, uma contagem e
não um conjunto de identidades. `SpeciationOccurred` significa "o genoma médio
divergiu além do limiar", e **não** "a espécie X nasceu da espécie Y".

Uma projeção só projeta o que existe a montante. Não há como derivar um catálogo
de espécies coexistentes, com população e linhagem, de eventos sobre uma média.

### As duas saídas

1. **Códex como LINHAGEM da comunidade** — barata e honesta. Cada
   `LifeEmerged`/`SpeciationOccurred` abre uma entrada com o genoma médio daquele
   momento. O `/species` vira uma **cadeia filogenética no tempo**, não um censo
   de espécies coexistentes. Poucas entradas por partida.
2. **Coortes por espécie no Engine (DEC-04)** — o que a auditoria de conformidade
   pede: coortes em arrays colunares, malha geodésica. Restaura o censo. É a
   reescrita que a própria auditoria chama de "distância de arquitetura, não de
   refatoração".

### Por que a decisão não é de engenharia

Ela define o que o aluno VÊ quando pergunta "quais espécies vivem no meu
planeta?" — um painel de comunidade ou um censo. É decisão de produto e de
pedagogia, e por isso volta ao dono do produto e à especialista.

**Coortes/DEC-04 seguem FORA de escopo até essa decisão.** O caminho B permanece
dormente, e `test_path_b_is_dormant` guarda isso.

---

## P-02 — Termostato de carbono de longo prazo

**Estado:** aberto. **Bloqueia:** sessões longas e pilotos (não o desenvolvimento).
**Registro completo:** `docs/adr/0020-long-horizon-carbon-instability.md`.

Não existe equilíbrio de CO₂: o carbono passa de 870 ppm e continua subindo em
t=3000, com deriva positiva em toda semente medida, e em parte delas a biosfera
colapsa sem retornar.

**A dívida é HERDADA** — o M3 é igual ou pior, e a Q11 do M4 não é a causa (ela
melhora a semente 99). Ficou invisível porque nenhum teste passava de ~600 ticks:
a suíte verifica correção POR TICK, e o sistema derrapa com cada passo correto.

**Hipótese:** falta a dependência TÉRMICA do intemperismo de silicatos, que na
Terra fecha o laço negativo (mais CO₂ → mais calor → mais intemperismo → menos
CO₂). O modelo tem intemperismo proporcional ao estoque, não à temperatura.

**Consequência de produto:** horizonte de jogo válido de ~500 ticks até a
correção.

**Precisa de:** um marco científico próprio, com dono. Investigar a hipótese
antes de implementar — o número não foi verificado, só é coerente com os dados.

### Adendo (Fase 1, ECO-001): a dívida é MAIOR do que a caracterização original

Achado LATERAL do varrido de sementes da Fase 1 — não é sobre onivoria, e por
isso está aqui, e não no ADR 0030. A tabela de dados está no
**ADR 0030, seção "O padrão medido (16 sementes...)"**; não é re-derivada aqui.

**Caracterização original (ADR 0020):** 4 sementes escolhidas (2027, 99, 11, 5),
todas DENTRO do teto em 500 ticks — amplitude de 18–59 ppm —, o que sustentou o
horizonte de jogo válido de ~500 ticks.

**Novo achado (varrido de 16 sementes, 500 ticks, janela assentada):** na **cadeia
estrita**, **7 de 16 sementes já passam de 60 ppm** — 3, 8, 17, 50, 123, 777 e
2024 —, com a pior (777) em **129,4 ppm**, mais que o dobro do teto. **Sem
onivoria alguma envolvida:** é a dívida de carbono pura. Medido nos dois regimes
(era 0, como o ADR 0020 mediu, e com eras avançando, como o jogo roda) com
resultado **idêntico** — logo é propriedade do modelo, não do regime de eras nem
da Fase 1.

**O que isso muda:** o teto de 60 ppm e o horizonte de ~500 ticks são propriedade
das **4 sementes escolhidas**, não do modelo. Em quase metade das sementes o
planeta já não é quase-estacionário DENTRO do horizonte que hoje chamamos de
válido. A dívida não mudou de natureza — mudou de TAMANHO conhecido.

**Implicação para o sequenciamento (nota de escopo, NÃO uma decisão):** a Fase 3
(correção de carbono de longo prazo) pode precisar vir ANTES na ordem do Plano
§9, por dois motivos independentes:

1. **Independente da Fase 1** — este adendo: a dívida atinge mais planetas do que
   se sabia, e limita o horizonte válido de sessões reais por semente.
2. **Dependente da Fase 1** — o ADR 0030: a onivoria de força plena está
   BLOQUEADA por esta dívida, e `ECO-002` (competição/mutualismo/parasitismo) é
   candidato a compor a mesma amplificação.

A decisão de resequenciar é do arquiteto, na próxima rodada de planejamento.
**Nada foi resequenciado nem corrigido na Fase 1 por conta deste achado.**
