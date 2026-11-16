# Relatório de carga — platform-api

**Data:** 2026-11-16. **Script:** `services/platform-api/scripts/carga.ts` (`pnpm carga`). **Alvo:** uma instância (`node dist/main.js`, NODE_ENV=development, adaptadores falsos de simulação/tutor/armazenamento), PostgreSQL 16 e Redis 7 em contêiner local, na mesma máquina (4 vCPU, 15 GiB). O processo da aplicação conecta como o papel restrito `platform_app`.

## Método

1. Preparação por HTTP: escola, professor, responsável e **45 alunos menores** com vínculo e consentimento (`platform_use`, `learning_assessment`), todos na mesma turma.
2. Cenários, todos com as requisições disparadas ao mesmo tempo (`Promise.all`), do mesmo IP (como atrás do NAT de uma escola):
   - login simultâneo dos 45;
   - cada aluno cria o próprio planeta;
   - **45 WebSockets abertos** (um por planeta); cada aluno aplica 2 intervenções; mede-se do início do POST até o `delta` chegar no WebSocket (fan-out via Redis pub/sub);
   - 225 leituras de planeta;
   - 40 leituras do painel do professor (visão da turma e competências).
3. Percentis calculados sobre as latências medidas no cliente.

## Resultado

| Cenário | Requisições | Erros | p50 (ms) | p95 (ms) | p99 (ms) | máx (ms) |
|---|---|---|---|---|---|---|
| Login simultâneo (45) | 45 | 0 | 206 | 253 | 254 | 254 |
| Criar planeta simultâneo (45) | 45 | 0 | 140 | 159 | 159 | 159 |
| Ação → delta no WebSocket (45 conexões abertas) | 90 | 0 | 81 | 91 | 92 | 92 |
| GET planeta (225 disparadas ao mesmo tempo) | 225 | 0 | 273 | 532 | 545 | 546 |
| Painel do professor (40 em paralelo) | 40 | 0 | 548 | 566 | 570 | 570 |

Metas: RNF-005 (≥ 40 alunos simultâneos por instância, sem erro) **atingida**; RNF-002 (ação → feedback ≤ 1 s p95) **atingida** no caminho do gateway (91 ms p95 com o fake de simulação).

## Limites e nível de confiança

- **Confiança média.** O fake de simulação responde em microssegundos; com o `ai-sim-service` real, a latência ação→delta vai somar o tempo do serviço. O número mede o custo do platform-api (autorização, consentimento, outbox, fan-out).
- Cliente e servidor na mesma máquina: sem latência de rede real. Login é dominado pelo Argon2id (19 MiB, 2 iterações) — custo intencional.
- O painel faz uma checagem de consentimento por aluno (com cache Redis de 60 s). Para turmas muito maiores, convém consulta em lote (registrado em riscos).
- Teste único, sem aquecimento controlado. Não substitui k6 contínuo no CI (proposto).

Saída bruta da execução:

```
Preparação concluída.

| Cenário | Requisições | Erros | p50 (ms) | p95 (ms) | p99 (ms) | máx (ms) |
|---|---|---|---|---|---|---|
| Login simultâneo (45) | 45 | 0 | 206 | 253 | 254 | 254 |
| Criar planeta simultâneo (45) | 45 | 0 | 140 | 159 | 159 | 159 |
| Ação → delta no WebSocket (45 conexões abertas) | 90 | 0 | 81 | 91 | 92 | 92 |
| GET planeta (225 disparadas ao mesmo tempo) | 225 | 0 | 273 | 532 | 545 | 546 |
| Painel do professor (40 em paralelo) | 40 | 0 | 548 | 566 | 570 | 570 |

Metas: login e painel sem erro; ação→delta p95 ≤ 1000 ms (RNF-002). Obtido: login p95=253 ms, ação→delta p95=91 ms, painel p95=566 ms.
```
