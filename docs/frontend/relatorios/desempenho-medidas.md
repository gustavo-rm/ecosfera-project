# Medidas de tempo de quadro

Geradas por `scripts/perf.mjs` em 2026-11-16. Renderizador: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver). Máquina: 4 núcleos, sem GPU.

| Janela | Qualidade | Limitação de CPU | Vista | Quadro médio (ms) | FPS médio | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|---|---|---|
| 1366x768 | low | 1× | planeta inteiro | 54.7 | 18.3 | 50.0 | 83.4 |
| 1366x768 | low | 1× | zoom com organismos | 111.4 | 9.0 | 16.8 | 400.0 |
| 1366x768 | low | 1× | camada de temperatura | 34.5 | 29.0 | 33.3 | 50.0 |
| 1366x768 | low | 4× | planeta inteiro | 64.2 | 15.6 | 66.6 | 116.7 |
| 1366x768 | low | 4× | zoom com organismos | 121.7 | 8.2 | 49.9 | 250.1 |
| 1366x768 | low | 4× | camada de temperatura | 44.0 | 22.7 | 49.9 | 50.1 |
| 1366x768 | medium | 1× | planeta inteiro | 96.6 | 10.4 | 16.7 | 333.4 |
| 1366x768 | medium | 1× | zoom com organismos | 158.1 | 6.3 | 16.7 | 766.7 |
| 1366x768 | medium | 1× | camada de temperatura | 76.4 | 13.1 | 100.0 | 183.3 |
| 1366x768 | medium | 4× | planeta inteiro | 116.3 | 8.6 | 66.8 | 233.4 |
| 1366x768 | medium | 4× | zoom com organismos | 173.6 | 5.8 | 16.7 | 500.1 |
| 1366x768 | medium | 4× | camada de temperatura | 89.5 | 11.2 | 133.3 | 150.1 |
| 1366x768 | high | 1× | planeta inteiro | 136.6 | 7.3 | 16.7 | 433.3 |
| 1366x768 | high | 1× | zoom com organismos | 190.2 | 5.3 | 16.7 | 766.6 |
| 1366x768 | high | 1× | camada de temperatura | 214.3 | 4.7 | 216.6 | 383.3 |
| 1366x768 | high | 4× | planeta inteiro | 149.6 | 6.7 | 16.7 | 399.9 |
| 1366x768 | high | 4× | zoom com organismos | 203.5 | 4.9 | 33.2 | 799.9 |
| 1366x768 | high | 4× | camada de temperatura | 131.2 | 7.6 | 49.9 | 300.0 |
| 683x384 | low | 1× | planeta inteiro | 18.7 | 53.3 | 16.7 | 33.3 |
| 683x384 | medium | 1× | planeta inteiro | 79.4 | 12.6 | 83.3 | 150.0 |
| 683x384 | high | 1× | planeta inteiro | 105.3 | 9.5 | 133.3 | 216.6 |
| 1366x768 | low | 1× | planeta inteiro, após 25 s | 29.9 | 33.4 | 33.3 | 33.5 |
| 1366x768 | low | 4× | planeta inteiro, após 25 s | 31.6 | 31.7 | 33.3 | 50.0 |
