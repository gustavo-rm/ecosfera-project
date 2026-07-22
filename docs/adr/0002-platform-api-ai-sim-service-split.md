# 0002 — Dois serviços de back-end: platform-api e ai-sim-service

- Status: Aceito (decisão já em vigor no scaffold; formalizada aqui)
- Data: 2026-07-22

## Contexto

O produto tem duas naturezas de responsabilidade bem distintas:

- **Platform**: identidade, contas, sessões — domínio transacional clássico, relacional.
- **Simulation + Tutor (IA/RAG)**: motor de simulação do ecossistema e tutor
  pedagógico via LLM/RAG — domínio orientado a documentos (Mongo), vetores
  (pgvector) e integração com um runtime de LLM (Ollama).

Essas duas naturezas têm ciclos de vida, linguagens e times de expertise
diferentes (TypeScript/NestJS para regras transacionais; Python para
simulação e IA, ecossistema com `sqlalchemy`/`pgvector`/`pymongo` já maduro
nessa linguagem).

## Decisão

Manter dois serviços de back-end separados desde o início:

- `services/platform-api` (NestJS + TypeORM) — bounded context **Platform**.
- `services/ai-sim-service` (Python) — bounded contexts **Simulation** e
  **Tutor**, ambos no mesmo processo/deploy por ora (ver também a
  modularização interna descrita no ADR 0001).

Não dividir `ai-sim-service` em dois microsserviços (`simulation-service` e
`tutor-service`) agora: não há evidência de necessidade de escalar ou
deployar essas duas responsabilidades de forma independente, e um split
prematuro adicionaria custo operacional (dois deploys, dois bancos de
observabilidade, mais uma fronteira de rede) sem benefício comprovado. A
separação em `simulation/` e `tutor/` como subpacotes internos (ADR 0001)
mantém essa opção barata de exercer no futuro, caso surja essa necessidade.

## Consequências

- Comunicação entre `platform-api` e `ai-sim-service` é feita via API (HTTP),
  nunca por acesso direto ao schema um do outro (ver ADR 0003).
- Cada serviço evolui seu próprio schema/coleções sem coordenar deploys com o outro.
- Se `tutor` precisar escalar de forma independente de `simulation` no futuro,
  a extração é uma questão de mover o subpacote `tutor/` para um novo
  serviço, não um redesenho de fronteiras.
