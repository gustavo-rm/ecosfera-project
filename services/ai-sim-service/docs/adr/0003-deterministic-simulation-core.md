# ADR 0003 — Núcleo de simulação determinístico

## Status
Aceito.

## Contexto
Até aqui `/ai/explain` recebia observações prontas; faltava o motor que as PRODUZ.
O core loop do MVP (RF-011/012 criar planeta, RF-013/014 tick + subsistemas
acoplados) exige um motor que gere o estado do planeta a cada tick e emita as
observações consumidas pelo motor de feedback causal já existente. A fronteira
determinístico × IA (Dossiê §8, GDD §10) impõe que esta camada seja 100%
determinística: nada de LLM/AG/ABM aqui — a ciência que o aluno precisa entender
não pode ser falsificada nem embaralhada por estocasticidade não reprodutível.

## Decisão
Criamos o pacote `simulation_engine` (puro, sem FastAPI), com três decisões:

1. **Subsistemas como estratégias plugáveis (padrão Strategy — Dossiê §15).** Cada
   processo planetário (`climate`, `chemistry`, `life`) implementa o Protocol
   `Subsystem.step(state, rng) -> StateDelta`. O `TickOrchestrator` os compõe na
   ordem de acoplamento clima → química → vida sem conhecer seus detalhes,
   aplicando cada delta ao estado de trabalho para realizar as retroalimentações
   dentro do mesmo tick. Adicionar ecologia (ABM) ou evolução (AG) nos Inc 3/4 é
   plugar novas estratégias, sem tocar nas camadas superiores (ADR 0001).

2. **Determinismo por semente (RF-023).** O RNG é o `numpy.random.Generator`
   semeado por `SeedSequence([seed, tick])`: a mesma semente reproduz exatamente
   a trajetória (base de replay/RF-016), enquanto cada tick recebe ruído distinto
   porém reprodutível. O estado inicial vem dos parâmetros versionados, não da
   semente — a semente controla apenas a estocasticidade dos ticks.

3. **Parâmetros como dados versionados.** Todos os coeficientes científicos vivem
   em `configs/simulation_params.yaml` (com campo `version`), nunca hardcoded,
   espelhando `causal_rules.yaml`. Especialistas ajustam o modelo sem redeploy.

O estado (`PlanetState`) é uma dataclass imutável; cada tick produz um novo estado
(append-only por era — Dossiê §9), persistido pela porta `PlanetRepository`
(adaptador in-memory no MVP, substituível por Mongo/Postgres). O `RunTickUseCase`
REUTILIZA o `ExplainCausalUseCase` existente para narrar o delta: o motor de
simulação produz observações e o motor de regras produz a cadeia causal — sem
duplicar lógica.

## Consequências
+ Core loop fechado: criar planeta → tick → explicação causal do delta, tudo
  determinístico e testável (determinismo + sanidade científica em `tests/unit`).
+ Extensível por incremento: novos subsistemas entram como estratégias; a
  persistência real troca só o adaptador da porta.
+ A física é simplificada de propósito (balanço de energia de caixa única,
  crescimento logístico) — coerente e explicável, mas não um GCM. Refinamentos
  científicos são evolução de dados/estratégias, não de arquitetura.
− Acoplamento sequencial dentro do tick introduz dependência de ordem entre
  subsistemas; documentada e fixada no orquestrador (clima → química → vida).
