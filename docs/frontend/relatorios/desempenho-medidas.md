# Medidas de tempo de quadro

Geradas por `scripts/perf.mjs` em 2026-11-14. Renderizador: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver). Máquina: 4 núcleos, sem GPU.

| Janela | Qualidade | Limitação de CPU | Vista | Quadro médio (ms) | FPS médio | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|
| 1366x768 | low | 1× | planeta inteiro | 68.7 | 14.5 | 66.7 | 100.0 |
| 1366x768 | low | 1× | zoom com organismos | 126.2 | 7.9 | 16.7 | 400.0 |
| 1366x768 | low | 1× | camada de temperatura | 51.6 | 19.4 | 50.0 | 83.4 |
| 1366x768 | low | 4× | planeta inteiro | 83.1 | 12.0 | 83.3 | 100.0 |
| 1366x768 | low | 4× | zoom com organismos | 139.6 | 7.2 | 33.4 | 316.7 |
| 1366x768 | low | 4× | camada de temperatura | 65.7 | 15.2 | 66.6 | 100.0 |
| 1366x768 | medium | 1× | planeta inteiro | 118.6 | 8.4 | 83.4 | 383.2 |
| 1366x768 | medium | 1× | zoom com organismos | 157.5 | 6.3 | 16.7 | 783.3 |
| 1366x768 | medium | 1× | camada de temperatura | 86.9 | 11.5 | 116.6 | 233.4 |
| 1366x768 | medium | 4× | planeta inteiro | 125.8 | 7.9 | 83.4 | 266.7 |
| 1366x768 | medium | 4× | zoom com organismos | 191.7 | 5.2 | 33.3 | 633.3 |
| 1366x768 | medium | 4× | camada de temperatura | 167.6 | 6.0 | 150.0 | 300.1 |
| 1366x768 | high | 1× | planeta inteiro | 147.6 | 6.8 | 16.7 | 666.7 |
| 1366x768 | high | 1× | zoom com organismos | 188.0 | 5.3 | 16.7 | 1316.6 |
| 1366x768 | high | 1× | camada de temperatura | 157.9 | 6.3 | 216.5 | 433.2 |
| 1366x768 | high | 4× | planeta inteiro | 160.1 | 6.2 | 16.7 | 499.9 |
| 1366x768 | high | 4× | zoom com organismos | 194.4 | 5.1 | 16.7 | 949.9 |
| 1366x768 | high | 4× | camada de temperatura | 134.1 | 7.5 | 16.7 | 549.9 |
| 683x384 | low | 1× | planeta inteiro | 22.8 | 43.9 | 16.7 | 33.4 |
| 683x384 | medium | 1× | planeta inteiro | 92.2 | 10.8 | 83.4 | 116.7 |
| 683x384 | high | 1× | planeta inteiro | 122.2 | 8.2 | 16.7 | 416.7 |
| 1366x768 | low | 1× | planeta inteiro, após 25 s | 28.7 | 34.8 | 33.3 | 33.4 |
| 1366x768 | low | 4× | planeta inteiro, após 25 s | 35.5 | 28.2 | 33.3 | 50.0 |
