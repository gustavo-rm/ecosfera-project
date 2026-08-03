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
