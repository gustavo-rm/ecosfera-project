# FE-0003 — Níveis de qualidade, LOD e queda automática

- Status: Aceito. Os limiares são provisórios até a medição em Chromebook real.
- Data: 2026-11-14

## Contexto

RNF-001 pede 30 FPS ou mais em Chromebook típico, com queda automática. RF-057 pede desempenho adaptativo. Não há Chromebook disponível; as medidas são em WebGL por software, que é um piso pessimista.

## Decisão

Três níveis, definidos em `render/quality.ts`:

| | Baixo | Médio | Alto |
|---|---|---|---|
| Malha de render | um nível abaixo dos dados (2 562 vértices) | igual aos dados (10 242) | um nível acima (40 962) |
| Teto de DPR | 1 | 1,25 | 2 |
| Oitavas de ruído | 2 | 3 | 5 |
| Ondas, espuma e ruído fino | não | sim | sim |
| Antisserrilhamento | não | sim | sim |
| Organismos instanciados | 160 | 500 | 1 400 |
| Quadros de estado por segundo | 3 | 5 | 8 |

Governador automático (`PerfGovernor` em `render/PlanetView.tsx`):

1. Mede o tempo de quadro com média móvel exponencial.
2. Acima de 36 ms por 2 s: reduz a escala de resolução em 20%, até 0,5.
3. Se já está em 0,5 e continua lento: desce um nível de qualidade e volta a escala a 1.
4. Abaixo de 19 ms por 6 s: sobe a escala em 15%.
5. O nível não sobe sozinho. Subir de nível é ação manual (console de laboratório), para evitar oscilação.

A escala de resolução passa pela propriedade `dpr` do `Canvas`, porque o React Three Fiber reaplica essa propriedade a cada render.

Disciplina de render: o laço por quadro do planeta não aloca; a aparência é calculada só quando o estado muda; a geração de dados roda em Web Worker; os shaders pulam por ramificação o que não se aplica ao pixel.

## Consequências

- Em WebGL por software e 1366×768, o governador chega ao nível baixo com escala 0,51 e fica em 34,8 FPS (28,2 FPS com CPU limitada em 4×). Detalhes em `relatorios/desempenho.md`.
- No avanço rápido (nível agregado do motor, §22.5) a fauna por organismo é ocultada e a fonte envia menos quadros.
- Não há pós-processamento em nenhum nível.
