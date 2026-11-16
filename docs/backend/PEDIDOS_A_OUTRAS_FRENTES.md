# Pedidos a outras frentes

O `platform-api` não altera pacotes de outras frentes. O que precisa mudar fora dele fica aqui.

| # | Frente | Pedido | Por quê | Estado |
|---|---|---|---|---|
| P1 | Infra (`infra/compose/dev.yml`) | Trocar `minio/minio:latest` e `minio/mc:latest` por imagem disponível (ex.: `chainguard/minio`) ou fixar versão espelhada | A imagem do Docker Hub não baixa mais | aberto |
| P2 | Docs (`docs/domain-language.md`, README raiz) | Atualizar o contexto "Platform": além de identidade, inclui educação, avaliação (leitura) e orquestração | Glossário desatualizado em relação ao Dossiê v3 | aberto |
| P3 | Raiz do monorepo (`pnpm-workspace.yaml`) — **precisa de aprovação** | Acrescentar em `allowBuilds`: `cpu-features: false`, `ssh2: false`, `protobufjs: false` | O pnpm 11 falha no `pnpm install --frozen-lockfile` quando há scripts de build sem decisão. Esses três vêm de dependências de desenvolvimento/observabilidade do `platform-api` (Testcontainers e exportador OTLP). `false` nega a execução dos scripts; nenhum deles é necessário (são binários opcionais) | aguardando aprovação |
