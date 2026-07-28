# ADR 0007 — Porta de fila assíncrona com adaptadores inline e ARQ

## Status
Aceito.

## Contexto
A evolução (AG) é o primeiro processo do serviço caro o bastante para não caber
confortavelmente no ciclo request/response: um avanço de era com muitas espécies
roda várias gerações de seleção/cruzamento/mutação. O Dossiê §4 já prevê
processamento assíncrono para trabalho pesado, e o `docker-compose` do serviço já
traz Redis desde o Inc 0/1.

Acoplar o caso de uso ao Redis, porém, teria um custo alto e imediato: a suíte de
testes — hoje verde **sem nenhuma infraestrutura** — passaria a exigir um broker
para exercitar o fluxo principal do incremento.

## Decisão

**Uma porta `JobQueue`** (`enqueue`, `get_status`) com dois adaptadores:

| Adaptador | Onde roda | Uso |
| --- | --- | --- |
| `InlineJobQueue` | mesmo processo, na hora | dev e **testes** (padrão) |
| `ArqJobQueue` | Redis + worker ARQ | staging/produção |

Selecionados por `ECOSFERA_JOB_BACKEND=inline\|arq`. O import do ARQ é
**preguiçoso**, então o serviço sobe em modo inline sem o extra `infra` instalado.

**O corpo do job é o mesmo nos dois caminhos.** `EvolveBiologyUseCase` é um caso
de uso próprio, e tanto o handler inline quanto o worker ARQ apenas o invocam. O
backend muda ONDE o trabalho roda, nunca O QUE ele faz — é isso que faz o teste
inline ter valor real sobre o caminho de produção.

**Dois contratos HTTP para o mesmo endpoint**, conforme o backend:

- inline → **200** com o resumo biológico já resolvido no corpo;
- ARQ → **202** com `job` (referência), consultável em
  `GET /simulation/jobs/{job_id}`.

Responder 202 é o que honestamente descreve o estado: a era está fechada e
persistida, mas a biologia ainda está sendo computada. O cliente que precisa do
resultado faz *polling* no endpoint de status.

**Falha de job é ESTADO, não exceção que vaza.** Um erro na evolução vira
`JobStatus.FAILED` com a mensagem — o avanço de era (que já persistiu o
checkpoint determinístico) não é derrubado por um problema da camada emergente.
Coerente com a fronteira do ADR 0006: a ciência não depende do emergente.

O worker (`infrastructure/jobs/worker.py`) é um **segundo composition root**:
roda em outro processo, sem FastAPI, e monta suas dependências a partir das
settings — com persistência real, nunca in-memory.

## Consequências
+ O fluxo completo do Inc 3 é testável ponta a ponta sem Redis, Docker ou worker.
+ Trocar de backend é variável de ambiente; o rollback é imediato.
+ A porta serve aos próximos jobs pesados (indexação de RAG no Inc 6, inferência
  bayesiana no Inc 7) sem novo desenho.
− Dois caminhos de código a manter em paridade de contrato. Mitigado por o corpo
  do job ser compartilhado e pelo teste de integração com Redis via Testcontainers
  (pulado quando não há Docker).
− Com ARQ o cliente precisa fazer *polling*; não há push. Aceitável para a
  granularidade de uma era. Notificação por WebSocket/SSE fica para quando o
  front exigir.
− `InlineJobQueue` guarda os resultados em memória do processo: reiniciar o
  serviço perde o histórico de jobs. É adequado a dev/testes, que é o seu escopo.
