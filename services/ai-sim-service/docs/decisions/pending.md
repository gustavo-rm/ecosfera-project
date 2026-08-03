# Decisões PENDENTES — bloqueadores de marcos futuros

Registro do que está explicitamente **em aberto**, para que não vire silêncio.

---

## P-01 — O que `/species` significa para o aluno

**Estado:** aberto. **Bloqueia:** M5/M6 (códex e Tutor).
**Precisa de:** pergunta reformulada à especialista, no eixo **BIODIVERSIDADE** —
não no eixo evolução.

### O impasse

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
