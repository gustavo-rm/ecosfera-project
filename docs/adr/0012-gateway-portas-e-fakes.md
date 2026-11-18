# 0012 — Gateway de simulação e tutor por portas e fakes honestos

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

O `ai-sim-service` ainda não expõe planeta, tick nem tutor (é só esqueleto). O platform-api não calcula ciência.

## Decisão

- Portas `SimulationGateway` e `TutorGateway`. Adaptadores reais HTTP (timeout por chamada, repetição limitada só em operações idempotentes, propagação W3C `traceparent`, erro tratado 503/504) e fakes determinísticos por seed, com estado no Redis.
- Fakes honestos: nome `FAKE:*`, aviso no log de boot, lista em `/ready`, e a validação de configuração **impede** fakes em produção (teste unitário e teste da imagem).
- O fake de simulação emite `EvidenciaGerada`/`CompetenciaAtualizada` **sintéticas** (marcadas) no stream de avaliação, como o serviço real faria.
- Pontos de ação: o `ai-sim-service` é autoritativo; o gateway repassa e valida o formato (pedido P4).
- O contexto enviado à IA só tem identificadores opacos; texto livre passa por redação de PII; o texto que volta é tratado como dado (caracteres de controle removidos, SSE em JSON por trecho).

## Consequências

- O contrato interno com o `ai-sim-service` é uma proposta (`/simulation/api/v1`, `/tutor/api/v1`) e precisa ser confirmado pela outra frente.
