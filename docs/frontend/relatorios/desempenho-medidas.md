# Medidas de tempo de quadro

Geradas por `scripts/perf.mjs` em 2026-11-15. Renderizador: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver). Máquina: 4 núcleos, sem GPU.

| Janela | Qualidade | Limitação de CPU | Vista | Quadro médio (ms) | FPS médio | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|
| 1366x768 | low | 1× | planeta inteiro | 86.2 | 11.6 | 83.3 | 166.7 |
| 1366x768 | low | 1× | zoom com organismos | 118.6 | 8.4 | 16.7 | 383.4 |
| 1366x768 | low | 1× | camada de temperatura | 38.3 | 26.1 | 33.4 | 50.1 |
| 1366x768 | low | 4× | planeta inteiro | 68.8 | 14.5 | 66.7 | 133.3 |
| 1366x768 | low | 4× | zoom com organismos | 127.1 | 7.9 | 50.0 | 300.1 |
| 1366x768 | low | 4× | camada de temperatura | 44.0 | 22.7 | 49.9 | 66.6 |
| 1366x768 | medium | 1× | planeta inteiro | 100.0 | 10.0 | 66.6 | 316.6 |
| 1366x768 | medium | 1× | zoom com organismos | 154.3 | 6.5 | 16.7 | 766.6 |
| 1366x768 | medium | 1× | camada de temperatura | 74.9 | 13.4 | 99.9 | 150.0 |
| 1366x768 | medium | 4× | planeta inteiro | 110.6 | 9.0 | 166.7 | 233.4 |
| 1366x768 | medium | 4× | zoom com organismos | 176.7 | 5.7 | 16.7 | 850.0 |
| 1366x768 | medium | 4× | camada de temperatura | 87.4 | 11.4 | 116.7 | 150.0 |
| 1366x768 | high | 1× | planeta inteiro | 154.4 | 6.5 | 16.7 | 683.3 |
| 1366x768 | high | 1× | zoom com organismos | 193.9 | 5.2 | 16.7 | 1133.3 |
| 1366x768 | high | 1× | camada de temperatura | 117.0 | 8.5 | 16.7 | 433.3 |
| 1366x768 | high | 4× | planeta inteiro | 156.7 | 6.4 | 16.7 | 416.7 |
| 1366x768 | high | 4× | zoom com organismos | 200.0 | 5.0 | 16.7 | 833.2 |
| 1366x768 | high | 4× | camada de temperatura | 136.1 | 7.3 | 33.4 | 283.4 |
| 683x384 | low | 1× | planeta inteiro | 16.9 | 59.0 | 16.7 | 16.8 |
| 683x384 | medium | 1× | planeta inteiro | 80.6 | 12.4 | 83.3 | 100.0 |
| 683x384 | high | 1× | planeta inteiro | 111.1 | 9.0 | 150.1 | 233.3 |
| 1366x768 | low | 1× | planeta inteiro, após 25 s | 30.1 | 33.2 | 33.3 | 49.9 |
| 1366x768 | low | 4× | planeta inteiro, após 25 s | 31.0 | 32.2 | 33.3 | 50.0 |
