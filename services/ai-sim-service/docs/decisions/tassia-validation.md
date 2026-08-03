# Validação científica — Biologia (Tássia)

Registro RASTREÁVEL das questões submetidas à especialista em Biologia: o
veredito, se entrou no escopo, e o requisito/ADR correspondente.

**Validadora:** Tássia (especialista em Biologia).
**Rodada registrada:** M4 (2026-08).
**Regra de leitura:** "validado em princípio" significa que a especialista
confirmou o FENÔMENO; quando a FORMA matemática foi decisão de engenharia sobre
esse princípio, está dito explicitamente e fica a confirmar quando ela estiver
ambientada no modelo.

| # | Questão | Veredito | Escopo | Onde |
| --- | --- | --- | --- | --- |
| **Q5** | "Não há aptidão" é formulação correta? | **Não.** A aptidão existe; o que não existe é aptidão ABSOLUTA. A aptidão é CONTEXTUAL — propriedade da relação organismo↔ambiente | **M4, aplicado** | ADR 0019 §5; `test_contextual_fitness_wording` |
| **Q8** | Toda extinção deve ter causa adaptativa? | **Não.** Extinção catastrófica é independente de aptidão — uma espécie bem adaptada pode morrer num evento extremo. Colapsar as duas ensina "quem se extingue era inferior" | **M4, aplicado** | ADR 0019 §1–§4; `test_catastrophic_extinction_is_fitness_independent` |
| **Q11** | A capacidade de suporte limita só produtores? | **Não.** Limita TODOS os níveis tróficos | **M4, aplicado em PRINCÍPIO** | ADR 0019 §6; `test_carrying_capacity_all_levels` |
| Q3 | Sequência adaptação ↔ cladogênese por era | Acatada | **Adiada — M6** | `deferred.md` |
| Q12 | Progressão cadeias → teias | Acatada | **Adiada — M6** | `deferred.md` |
| Q15 | Pequeno × grande ciclo da água | Acatada | **Adiada — M6** | `deferred.md` |
| Q2 | Linhagem para biodiversidade | Acatada | **Bloqueada** por P-01 | `pending.md` |

## Nota sobre a FORMA da Q11

A especialista validou o **princípio** (capacidade em todos os níveis). A forma
adotada — teto de cada nível ancorado no nível **abaixo** dele, e não numa fração
fixa do ambiente — foi **decisão de engenharia**, tomada depois de medir que a
forma plana levava os predadores à extinção por fome e achatava a cadeia em dois
níveis.

A forma eltoniana é defensável cientificamente (Elton, 1927: a pirâmide de
biomassa não inverte porque a conversão dissipa energia), mas **não foi ela que a
especialista viu**. Fica marcada como *"validada em princípio, forma a confirmar"*
para que a próxima rodada de validação a examine explicitamente, e para que
ninguém a cite depois como se tivesse sido aprovada tal como está.

## O que NÃO foi validado por ela

O pino de CO₂ e a estabilidade de longo prazo da linha de base (ADR 0019 §7) são
achado de ENGENHARIA, não questão biológica submetida. Não estão nesta tabela e
não devem ser atribuídos à validação científica.
