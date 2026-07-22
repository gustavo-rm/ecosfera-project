# ADR 0001 — Arquitetura hexagonal no ai-sim-service

## Status
Aceito.

## Contexto
O Dossiê PD&I (§1.1, §15) adota Clean/Hexagonal + DDD internamente a cada serviço.
O ai-sim-service precisa trocar LLM, banco e fila sem tocar na regra de negócio, e
manter a fronteira determinístico × IA (§8, GDD §10) explícita no código.

## Decisão
Camadas: `domain` (puro) → `application` (casos de uso + portas) → `infrastructure`
(adaptadores de saída) e `interfaces` (adaptadores de entrada HTTP). O único lugar
que conhece implementações concretas é o composition root (`interfaces/http/deps.py`).

## Consequências
+ Domínio testável sem FastAPI/rede (ver tests/unit).
+ Adaptadores substituíveis por incremento (NullLLM→Ollama; InMemory→Mongo) sem
  refatorar as camadas superiores.
− Verbosidade inicial (portas/Protocols) — aceitável para manutenção por equipe.
