# FE-0005 — Fonte de dados sintética, determinística e roteirizada

- Status: Aceito para desenvolvimento. Deixa de existir em produção quando houver `BackendSource`.
- Data: 2026-11-14

## Contexto

Não há backend nem contrato. O planeta, o HUD e os dashboards precisam de dados com a forma que a Especificação descreve (§24.5, §24.4) para serem construídos e verificados.

## Decisão

1. **Uma única porta de dados**, `PlanetStateSource` (`core/source/port.ts`), marcada com `TODO(contract)`. Implementações: `SyntheticSource`, `FixtureSource` e o esboço não implementado `BackendSource`.
2. **`frameAt(tick)` é função pura** de cenário, semente, parâmetros, variáveis forçadas e intervenções. Isso dá determinismo visual, rolagem do tempo exata e testes simples.
3. **Roteiros, não simulação.** Linhagens têm origem, extinção, capacidade e ritmo escritos em `scenarios.ts`. As populações seguem curva logística, oscilação com defasagem de um quarto de ciclo em relação à presa e ruído errático de amplitude moderada. Clima e atmosfera usam fórmulas simples.
4. **Tudo é placeholder científico.** Balanço de energia, classificação de biomas, zona habitável, luminosidade das estrelas e fluxos dos ciclos são aproximações marcadas no código. A autoridade de domínio decide o que vale.
5. **Selo visível.** Toda tela mostra "Dados sintéticos". A fonte informa `meta.synthetic`.
6. **Worker.** O cálculo roda em Web Worker; o relógio fica na thread principal. Há fallback sem worker (testes e navegadores sem suporte).

## Consequências

- Os cinco cenários canônicos existem em forma. O sexto (coerência de LOD) é teste do motor e ficou de fora.
- A fonte não valida ciência. Nenhum número dela deve ser usado como referência.
- `NECESSIDADES_DE_DADOS.md` lista o que a interface consome; é o insumo para o contrato.
