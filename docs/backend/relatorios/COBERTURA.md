# Relatório de cobertura — platform-api

**Data:** 2026-11-17. **Comando:** `pnpm --filter platform-api test:cov` (Jest, unitários + integração com Testcontainers, `--runInBand`). **Resultado:** 21 suítes, 156 testes, todos passando.

## Gate

`jest.config.js` falha o comando abaixo de: linhas 80%, statements 78%, funções 70%, ramos 60% (DEC-29). O job de CI proposto (P5) roda esse gate em todo PR.

## Por área

| Área | Linhas | Ramos |
|---|---|---|
| `configurar-aplicacao.ts` | 100.0% (26/26) | 50.0% |
| `instrumentacao.ts` | 0.0% (0/2) | — |
| `migrar.ts` | 0.0% (0/14) | 0.0% |
| `modules/assessment` | 87.8% (617/703) | 64.1% |
| `modules/education` | 87.9% (405/461) | 67.6% |
| `modules/identity` | 87.9% (960/1092) | 68.1% |
| `modules/orchestration` | 82.4% (601/729) | 63.6% |
| `outros` | 100.0% (13/13) | — |
| `shared/armazenamento` | 89.1% (41/46) | 78.6% |
| `shared/auditoria` | 100.0% (22/22) | 86.4% |
| `shared/autorizacao` | 94.5% (69/73) | 87.5% |
| `shared/config` | 90.7% (39/43) | 90.3% |
| `shared/database` | 100.0% (33/33) | 71.4% |
| `shared/eventos` | 74.1% (103/139) | 58.7% |
| `shared/http` | 95.1% (232/244) | 81.2% |
| `shared/infraestrutura` | 100.0% (47/47) | 60.0% |
| `shared/kernel` | 87.5% (77/88) | 89.8% |
| `shared/observabilidade` | 49.3% (35/71) | 23.8% |
| `shared/redis` | 95.5% (21/22) | — |
| `shared/saude` | 56.8% (21/37) | 42.9% |
| `shared/seguranca` | 94.8% (55/58) | 85.4% |
| **Total** | **86.22%** | **68.73%** (statements 84.54%, funções 79.76%) |

## Leitura

- **Bem coberto:** autorização central (94,5%), HTTP/contrato/erros (95%), segurança (95%), auditoria (100%), contextos de domínio (82–88%).
- **Fraco, conscientemente:** `shared/observabilidade` (49%: rastreamento OTel só liga exportador com coletor; métricas só lidas por `/metrics`), `shared/saude` (57%: ramos de dependência fora do ar e `/metrics` com token), `shared/eventos` (74%: reivindicação de pendentes e fila de mensagens mortas do consumidor não têm teste dedicado), `migrar.ts` e `instrumentacao.ts` (entradas de processo, exercitadas só pela imagem Docker).
- **Método e confiança:** cobertura de linha medida sobre testes que exercitam a aplicação real (banco, Redis e MinIO reais em contêiner) e validam toda resposta contra o OpenAPI congelado. Confiança alta para autorização, consentimento e contrato; média para os caminhos de falha do barramento de eventos.
