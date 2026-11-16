# 0017 — Exportações, armazenamento de objetos e dataset anonimizado

- Status: Aceito (escopo do platform-api)
- Data: 2026-11-16

## Contexto

RF-066, RF-078, RNF-011.

## Decisão

- Porta `ObjectStorage`: MinIO/S3 real (buckets privados, URL assinada de `SIGNED_URL_TTL_SECONDS`, padrão 300 s) e fake em disco com URL HMAC servida em `/files` (expira igual).
- Relatório da turma em CSV (com proteção contra injeção de fórmula) ou PDF; só alunos com consentimento de avaliação; registro em `export_record` e auditoria; objetos expurgados pela retenção.
- Dataset de pesquisa: só alunos com `research` e `learning_assessment` **concedidos explicitamente**; pseudônimo com sal descartável por exportação; escola pseudonimizada; data generalizada para semana ISO; supressão de grupos (escola, nível) com menos de k=5 alunos; varredura de PII antes de gravar (falha fechada) e auditoria.
- Feedback do professor ao aluno é cifrado em repouso (AES-256-GCM).

## Consequências

- Risco residual de reidentificação por cruzamento externo em escolas pequenas; k é parâmetro de código hoje (5).
