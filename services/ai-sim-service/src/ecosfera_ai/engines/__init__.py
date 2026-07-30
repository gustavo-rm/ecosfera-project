"""Camada de Simulação: um pacote por Engine (ADR-ARCH-0001, Spec §1).

`planet` orquestra; os demais modelam um domínio científico cada. Nenhum Engine
importa outro — a comunicação é por world-state/deltas (Canal A) e por domain
events (Canal B). A regra é verificada por `import-linter`.
"""
