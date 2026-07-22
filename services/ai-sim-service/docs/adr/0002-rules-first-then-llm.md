# ADR 0002 — Feedback causal por regras antes do LLM

## Status
Aceito.

## Contexto
A hipótese pedagógica central H2 (aprender por causa-efeito) precisa ser testável
já no MVP (Dossiê §2.1/§2.2). O tutor LLM+RAG só entra no Incremento 6 (§3.2). Subir
LLM cedo adiciona risco (alucinação RSK-03, latência, custo) sem necessidade.

## Decisão
No MVP, a explicação causal (RF-033/039) é gerada por um motor de **regras
determinísticas** cujas regras são **dados versionados** (`configs/causal_rules.yaml`),
revisáveis por pedagogos sem redeploy. O contrato de saída (`CausalExplanation`) é o
mesmo que o LLM produzirá no Inc 6; a cadeia causal rastreável vira **âncora
anti-alucinação** do RAG (RF-034).

## Consequências
+ H2 validável no primeiro playtest; determinismo (RF-023) garante reprodutibilidade.
+ Migração para LLM não quebra clientes: mesmo schema, apenas outro adaptador.
− Cobertura causal limitada às regras cadastradas — aceitável para o MVP.
