# FE-0006 — Estrutura de PWA sem sincronização

- Status: Aceito. A sincronização fica **adiada** até existir contrato.
- Data: 2026-11-14

## Contexto

RNF-021 pede uso offline parcial: continuar um planeta já carregado e sincronizar depois. A TASK-0039 inclui sincronização offline. Não existe servidor nem contrato para sincronizar.

## Decisão

Entregue agora:

- `public/manifest.webmanifest` e ícone local.
- `public/sw.js`: cache da casca (rotas do estudante), dos arquivos de build e das fixtures. Só mesma origem. Registrado apenas no build de produção.
- IndexedDB (`store/idb.ts`) guarda o jogo local: cenário, semente, parâmetros, o instante no tempo e as intervenções, que são reaplicadas ao retomar.
- Preferências de acessibilidade em `localStorage`.

Fica para quando houver contrato:

1. Fila de comandos do estudante para envio posterior e a regra de reconciliação com o servidor.
2. Envio dos eventos de evidência (hoje ficam só no barramento local) e a política de consentimento antes de enviar (RNF-009).
3. Versão de dados no IndexedDB e migração.
4. Estratégia de atualização do service worker com aviso ao usuário.
5. O que roda offline quando o motor é remoto: hoje funciona porque a fonte é local.

## Consequências

- O painel do professor não funciona offline (correto: depende de servidor).
- O funcionamento offline foi verificado só pela estrutura; não houve teste de instalação em Chromebook.
