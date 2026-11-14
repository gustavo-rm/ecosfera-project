# FE-0001 — Estratégia de shaders: GLSL em `WebGLRenderer` (WebGL 2), com WebGPU como evolução

- Status: Aceito para o frontend. **Propõe ajustar a decisão RT-003 do Dossiê** (ver "Relação com decisões existentes").
- Data: 2026-11-14
- Série: ADRs do frontend (`docs/frontend/adr/`), no mesmo formato de `docs/adr/`.

## Contexto

O Dossiê (§12, RT-003) indica "WebGPU com fallback WebGL 2". As tarefas TASK-0034 e TASK-0066 do backlog repetem isso. As tarefas TASK-0067, TASK-0068 e TASK-0069 pedem shaders em GLSL. As duas coisas não cabem juntas no Three.js atual.

Consulta à documentação em novembro de 2026:

- O manual oficial do Three.js diz que materiais baseados em `ShaderMaterial`, `RawShaderMaterial` e `onBeforeCompile()` **não são suportados** no `WebGPURenderer`. Esse código precisa ser portado para materiais de nós e TSL. ([manual: WebGPURenderer](https://threejs.org/manual/en/webgpurenderer))
- O mesmo manual diz que o `WebGLRenderer` continua mantido e é a escolha recomendada para aplicações WebGL 2 puras.
- O `WebGPURenderer` tem um backend WebGL 2 de fallback, mas ele só recebe o que foi escrito em TSL.

As opções eram: (a) TSL com fallback automático para WebGL 2; (b) GLSL em `WebGLRenderer`, com WebGPU como evolução futura.

## Decisão

Adotar a opção **(b)**: os shaders do planeta são GLSL em `ShaderMaterial`, renderizados por `WebGLRenderer` (WebGL 2).

Critérios, na ordem de peso:

1. **30 FPS em Chromebook (RNF-001).** O alvo é hardware modesto. WebGL 2 existe em todo Chromebook em uso; WebGPU depende de modelo, driver e política da escola. O planeta não usa nada que só o WebGPU oferece (não há simulação em compute shader no cliente: a simulação não é do frontend).
2. **Estabilidade da API.** GLSL e `ShaderMaterial` não mudam há anos. A TSL ainda muda entre versões.
3. **Manutenção por equipe pequena.** GLSL é conhecimento comum, tem ferramentas e exemplos. O time mantém um único caminho de render, não dois.
4. **Verificação.** O caminho WebGL 2 roda em Chromium headless com rasterização por software. Isso permitiu capturar e medir tudo nesta entrega.

Para manter a porta aberta para a opção (a):

- Todo GLSL fica em `apps/web-client/src/render/shaders/`. Nenhum componente monta shader em linha.
- A aparência é calculada fora dos shaders, em `core/appearance/appearance.ts` (função pura). Os shaders só consomem canais por célula e uniformes. Portar para TSL significa reescrever cinco arquivos de shader, sem tocar em estado, store ou interface.

## Relação com decisões existentes

- RF-057 ("sem WebGPU, cai para WebGL 2 sem quebrar") fica atendido de forma trivial: o cliente sempre roda em WebGL 2.
- RT-003 fala em WebGPU como caminho principal. Este ADR **não o revoga**; propõe que a equipe o leia como "WebGL 2 agora, WebGPU quando houver ganho medido". Se a equipe mantiver RT-003 ao pé da letra, o trabalho é o porte dos cinco shaders para TSL.

## Consequências

- Sem compute shaders no cliente. Hoje não há uso para eles.
- Quando o Three.js remover ou congelar o `WebGLRenderer`, o porte para TSL passa a ser obrigatório. O isolamento acima limita o custo.
- O desempenho foi medido só em WebGL por software (ver `relatorios/desempenho.md`). Falta medir em Chromebook real.
