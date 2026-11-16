# Decisões tomadas em lacunas da documentação

Cada decisão tem motivo. As de arquitetura têm ADR próprio em `docs/adr/`.

| # | Decisão | Motivo |
|---|---|---|
| DEC-01 | Prefixo HTTP `/platform/api/v1` | Briefing pede `/{service}/api/v1`; "platform" é o nome do contexto e do schema |
| DEC-02 | Valores de papel na API iguais ao enum da baseline (`student`, `teacher`...) | Evita uma camada de tradução e diverge menos do banco. O domínio usa nomes em português |
