# Linguagem ubíqua (domain language)

Glossário dos termos de domínio usados pelo produto, para manter o
vocabulário consistente entre `platform-api` (TypeScript), `ai-sim-service`
(Python) e os scripts de infraestrutura (SQL/JS). Extraído dos schemas e
coleções já existentes — atualize esta lista sempre que um novo conceito de
domínio for introduzido em qualquer um dos serviços.

| Termo | Bounded context | Definição |
|---|---|---|
| **Planet** | Simulation | Instância de um ecossistema simulado; unidade principal de estado do produto. Identificada por `planetId`. |
| **Era** | Simulation | Checkpoint temporal da simulação de um planeta (`planet_state` é indexado por `planetId + era`). |
| **Species** | Simulation | Espécie simulada, com genoma/traços próprios, associada a um planeta. |
| **Ecosystem** | Simulation | Relações entre espécies dentro de um planeta (predação, competição, etc.). |
| **EventLog** | Simulation | Registro cronológico de eventos ocorridos na simulação de um planeta (não confundir com auditoria de acesso — ver `docs/adr/0004-lgpd-telemetry-retention.md`). |
| **Session** | Platform | Sessão de uso de um aluno na plataforma. |
| **Telemetry** | Simulation | Eventos brutos de uma sessão, usados para avaliação stealth do aprendizado. Dado pessoal enquanto associado a `sessionId` — ver ADR 0004. |
| **Embedding / Chunk** | Tutor | Pedaço de um documento fonte (`source_type`: `curriculum`, `planet_state`, ...) vetorizado e armazenado em `rag.embedding` para busca por similaridade (RAG). |
| **Curriculum** | Tutor | Conteúdo pedagógico fonte, ingerido e transformado em embeddings para o tutor responder com base nele. |

## Bounded contexts

- **Platform** — identidade, contas, sessões. Dono: `services/platform-api`.
- **Simulation** — planeta, espécies, ecossistema, eventos. Dono:
  `services/ai-sim-service` (`ai_sim_service.simulation`).
- **Tutor** — RAG/LLM, agentes, prompts, avaliação. Dono:
  `services/ai-sim-service` (`ai_sim_service.tutor`).

Ver `docs/adr/0002-platform-api-ai-sim-service-split.md` para o motivo da
divisão entre serviços e `docs/adr/0001-layered-module-convention.md` para a
convenção de camadas dentro de cada bounded context.
