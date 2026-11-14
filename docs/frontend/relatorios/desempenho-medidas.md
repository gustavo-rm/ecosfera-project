# Medidas de tempo de quadro

Geradas por `scripts/perf.mjs` em 2026-11-14. Renderizador: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver). Máquina: 4 núcleos, sem GPU.

| Janela | Qualidade | Limitação de CPU | Vista | Quadro médio (ms) | FPS médio | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|
| 1366x768 | low | 1× | planeta inteiro | 62.1 | 16.1 | 66.6 | 83.3 |
| 1366x768 | low | 1× | zoom com organismos | 119.9 | 8.3 | 16.7 | 283.4 |
| 1366x768 | low | 1× | camada de temperatura | 50.4 | 19.8 | 50.0 | 83.3 |
| 1366x768 | low | 4× | planeta inteiro | 77.6 | 12.9 | 66.7 | 133.3 |
| 1366x768 | low | 4× | zoom com organismos | 131.2 | 7.6 | 16.7 | 316.7 |
| 1366x768 | low | 4× | camada de temperatura | 55.2 | 18.1 | 50.0 | 66.7 |
| 1366x768 | medium | 1× | planeta inteiro | 106.4 | 9.4 | 33.3 | 333.3 |
| 1366x768 | medium | 1× | zoom com organismos | 168.0 | 6.0 | 16.7 | 883.2 |
| 1366x768 | medium | 1× | camada de temperatura | 79.4 | 12.6 | 116.6 | 133.4 |
| 1366x768 | medium | 4× | planeta inteiro | 119.2 | 8.4 | 99.9 | 383.4 |
| 1366x768 | medium | 4× | zoom com organismos | 181.4 | 5.5 | 16.7 | 1116.7 |
| 1366x768 | medium | 4× | camada de temperatura | 98.4 | 10.2 | 133.3 | 166.7 |
| 1366x768 | high | 1× | planeta inteiro | 152.9 | 6.5 | 16.7 | 616.6 |
| 1366x768 | high | 1× | zoom com organismos | 199.5 | 5.0 | 16.7 | 1150.0 |
| 1366x768 | high | 1× | camada de temperatura | 116.7 | 8.6 | 33.3 | 300.0 |
| 1366x768 | high | 4× | planeta inteiro | 159.4 | 6.3 | 16.7 | 433.4 |
| 1366x768 | high | 4× | zoom com organismos | 209.4 | 4.8 | 16.7 | 899.9 |
| 1366x768 | high | 4× | camada de temperatura | 132.6 | 7.5 | 83.3 | 283.4 |
| 683x384 | low | 1× | planeta inteiro | 21.4 | 46.7 | 16.7 | 33.4 |
| 683x384 | medium | 1× | planeta inteiro | 79.8 | 12.5 | 83.3 | 150.0 |
| 683x384 | high | 1× | planeta inteiro | 108.3 | 9.2 | 83.3 | 366.6 |
| 1366x768 | low | 1× | planeta inteiro, após 25 s | 32.3 | 30.9 | 33.3 | 50.0 |
| 1366x768 | low | 4× | planeta inteiro, após 25 s | 34.8 | 28.8 | 33.3 | 50.0 |
