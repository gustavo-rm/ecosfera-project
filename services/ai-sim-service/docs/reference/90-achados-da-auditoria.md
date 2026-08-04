# Achados durante a auditoria

> Espinha factual extraída do commit `7d80534`. **Nada aqui foi corrigido** — esta auditoria
> não altera código de produção. Cada item está registrado para que o arquiteto decida.
> Índice: [`README.md`](README.md)

Quatorze itens, agrupados em cinco famílias: parâmetros que são carregados e nunca consumidos
(1, 2, 3, 5), configuração declarada que não vigora (4), campos publicados sem leitor (7),
superfícies prometidas na documentação e ausentes no código (11, 12) e resíduos benignos
(8, 9, 10, 14). Um deles é decisão de modelagem em aberto (6) e um é ciência fora do YAML (13).

**O padrão que atravessa quase todos:** o serviço é rigoroso em separar ciência (YAML) de
código, e os desvios encontrados são quase todos do mesmo tipo — **um parâmetro existe no YAML,
é lido para dentro de uma dataclass tipada, e ali morre**. Como a dataclass é construída com
sucesso e o `mypy --strict` passa, nada acusa. Um teste que afirmasse "todo campo de
`*EngineParams` é referenciado em algum lugar do pacote do Engine" pegaria 1, 2, 3 e 5 de uma vez.

| # | Achado | Tipo |
|---|---|---|
| 1 | Parâmetro carregado e nunca consumido: `reproduction_threshold` | parâmetro morto |
| 2 | Tetos de custo declarados e não aplicados: `max_agents`, `max_steps` | parâmetro morto |
| 3 | Teto declarado e não aplicado: `max_active_events` | parâmetro morto |
| 4 | Orçamentos por Engine carregados e não vigentes | configuração inerte |
| 5 | `carbon_tolerance` sem consumidor | parâmetro morto |
| 6 | `resource.consumed` é publicado e não realimenta nada | modelagem |
| 7 | `EventSlice.dust_load` e `EventSlice.impact_energy` não têm leitor | campo sem leitor |
| 8 | `climate.insolation` é código morto em produção | código morto benigno |
| 9 | `CANONICAL_ORDER` diverge de `ENGINE_ORDER` | documentação divergente |
| 10 | `_limiting_cause` tem dois ramos finais idênticos | código redundante |
| 11 | A telegrafia (RF-019/020) não é exposta por rota alguma | superfície ausente |
| 12 | `PlanetStateOut` congelou no M1 | superfície ausente |
| 13 | `_founder` recebe `params` e o descarta | ciência hardcoded |
| 14 | `ConservedTotal` e `EventSlice` fora de `shared_kernel.__all__` | cosmético |

---

### 1. Parâmetro carregado e nunca consumido: `reproduction_threshold`

**Onde:** `engines/evolution/params.yaml` (0.25) → `EvolutionEngineParams.reproduction_threshold`

Nenhum código lê `params.reproduction_threshold`. O YAML o documenta como 'excedente local acima do qual a coorte gera descendência divergente', mas a reprodução divergente é decidida por `has_speciated` sobre a distância genética, sem consultar excedente. **Risco:** um calibrador razoável mexeria neste valor esperando mudar a taxa de reprodução e não veria efeito nenhum.

**Encaminhamento sugerido (não aplicado):** Remover do YAML e da dataclass, **ou** implementar o gate que o comentário promete.

---
### 2. Tetos de custo declarados e não aplicados: `max_agents`, `max_steps`

**Onde:** `engines/ecology/params.yaml` (24, 50) → `EcologyEngineParams`

Ambos são carregados; `engines/ecology/service.py` não os menciona. O Engine opera sobre três agregados, não sobre agentes, então `max_agents` não tem significado nesta implementação; `max_steps` foi substituído por `steps_per_tick`. São herança do caminho B (`simulation_engine/biology/ecology.py`), onde os mesmos nomes existem e valem. **Risco:** aparentam ser a contenção de custo RSK do Inc 3, e não são.

**Encaminhamento sugerido (não aplicado):** Remover do `params.yaml` do Engine (continuam válidos no bloco `ecology` de `configs/simulation_params.yaml`, que alimenta o caminho B).

---
### 3. Teto declarado e não aplicado: `max_active_events`

**Onde:** `engines/event/params.yaml` (2) → `EventEngineParams.max_active_events`

Carregado, nunca lido. A `EventSlice` comporta **um** evento ativo por construção (`active_kind` é escalar), e `_maybe_schedule` só agenda quando não há ativo nem anunciado. O valor 2 sugere concorrência que a estrutura não admite.

**Encaminhamento sugerido (não aplicado):** Remover, ou registrar no YAML que é reserva para um desenho futuro de eventos simultâneos.

---
### 4. Orçamentos por Engine carregados e não vigentes

**Onde:** Bloco `budget:` dos dez `params.yaml` → `max_duration_s`/`max_events` de cada `*EngineParams`

Cada Engine declara o próprio orçamento, mas `PlanetEngine` aplica **um único `TickBudget`**, vindo de `configs/simulation_params.yaml → engines.budget` via `deps.get_orchestrator`. Nenhum Engine passa o próprio orçamento ao Planet. Consequência prática: os tetos por domínio (a Ecology pede 0,25 s e 100 eventos; a Astronomy, 0,05 s e 50) **não existem em runtime** — todos são medidos contra 0,25 s / 500 eventos / 50000 entidades.

**Encaminhamento sugerido (não aplicado):** Ou o Planet passa a consultar o orçamento declarado por Engine, ou os blocos `budget:` saem dos `params.yaml`. Manter os dois lados é convite a calibrar um teto que não vigora.

---
### 5. `carbon_tolerance` sem consumidor

**Onde:** `engines/chemistry/params.yaml` (1e-9) → `ChemistryEngineParams.carbon_tolerance`

Documentado como 'tolerância declarada da conservação de carbono (Spec §3)', mas nenhuma invariante o consome — `planet_invariants` instala `ConservedTotal` só para a água, e o `ADR 0012` explica por que não há invariante de carbono (a identidade atravessa duas fatias). O paralelo com `hydrology.conservation_tolerance`, que **é** injetado, torna a assimetria fácil de não notar.

**Encaminhamento sugerido (não aplicado):** Remover, ou anotar no YAML que a verificação vive em `test_carbon_is_not_double_counted` e a tolerância é do teste.

---
### 6. `resource.consumed` é publicado e não realimenta nada

**Onde:** `ResourceSlice.consumed`, `consumption_per_biomass`

O Resource calcula `consumed = consumption_per_biomass × biomassa` e o publica, mas nenhum Engine o lê e ele não é subtraído de `water_available`/`nutrients_available`/`energy_available` nem da capacidade. A biomassa consome recurso **contabilmente**, não fisicamente. Não é bug de conservação (o recurso é derivado do ambiente a cada tick, não é estoque), mas o nome sugere um dreno que não existe.

**Encaminhamento sugerido (não aplicado):** Decisão de modelagem, não de código: ou o consumo passa a reduzir a disponibilidade, ou o campo é renomeado para algo que declare ser diagnóstico.

---
### 7. `EventSlice.dust_load` e `EventSlice.impact_energy` não têm leitor

**Onde:** `shared_kernel/world_state.EventSlice`

O docstring de `dust_load` afirma que ela 'aumenta o albedo e reflete irradiância', mas nenhum Engine a lê: o Climate consome só `cooling_forcing`, e o albedo vem de `base_albedo + ice_albedo_coeff × ice_fraction`. O resfriamento por poeira do meteoro e do supervulcão chega **inteiramente** pelo coeficiente `cooling` do catálogo. `impact_energy`, descrita como alimentando 'a magnitude do MeteorImpact', também não é lida — o `cause_detail` do evento carrega `severity`, não `impact_energy`. Ambas atravessam a ponte e a persistência sem consumidor.

**Encaminhamento sugerido (não aplicado):** Ou o Climate passa a somar `dust_load` ao albedo (e o `cooling` do catálogo é recalibrado para não contar duas vezes), ou os campos e as suas colunas no catálogo saem. Hoje calibrar `catalog.meteor.dust` **não faz nada**.

---
### 8. `climate.insolation` é código morto em produção

**Onde:** `engines/climate/params.yaml` (1.0), `climate/domain.incident_flux`

O recuo `solar_flux if solar_flux > 0 else params.insolation` só dispara com irradiância nula. O Astronomy abre o tick e sempre publica `solar_flux > 0`; um snapshot recém-criado já traz `solar_flux` derivado do raio orbital. O parâmetro serve apenas a testes de unidade do Climate isolado.

**Encaminhamento sugerido (não aplicado):** Benigno. Vale anotar no YAML que é recuo de teste, para não parecer um botão de insolação.

---
### 9. `CANONICAL_ORDER` diverge de `ENGINE_ORDER`

**Onde:** `engines/planet/registry.py` vs. `engines/composition.py`

`CANONICAL_ORDER` lista `physics, chemistry, atmosphere, climate, geology, hydrology, resource, evolution, ecology, event` — com `physics` (nome aposentado, hoje `astronomy`) e `geology` **depois** do clima. A ordem em vigor é `astronomy, geology, chemistry, atmosphere, climate, ...`. O comentário diz que ela 'serve de referência para ordenar os que forem nascendo'; hoje ela referencia uma ordem que o tick não obedece.

**Encaminhamento sugerido (não aplicado):** Remover a constante, ou atualizá-la e anotar que é histórica. `composition.ENGINE_ORDER` já se declara 'a única fonte da ordem' — duas listas discordantes anulam esse ganho.

---
### 10. `_limiting_cause` tem dois ramos finais idênticos

**Onde:** `engines/evolution/service.py`, fim de `_limiting_cause`

```python
if resource_gap > 0.0 or conditions.carrying_capacity <= 0.0:
    return EvolutionCauseCode.RESOURCE_SCARCITY
return EvolutionCauseCode.RESOURCE_SCARCITY
```
O `if` não altera o resultado. Também `resource_gap` é calculado e usado só nesse teste inócuo. Não há defeito de comportamento — mas a estrutura sugere que um quarto código de causa (ou um `else` distinto) era pretendido e não chegou.

**Encaminhamento sugerido (não aplicado):** Simplificar para um `return` único, **ou** implementar a causa que faltava. Como é código de ATRIBUIÇÃO DE CAUSA, o que o Tutor narra depende disto.

---
### 11. A telegrafia (RF-019/020) não é exposta por rota alguma

**Onde:** `EventSlice.forecast_kind/forecast_ticks_ahead/forecast_severity`

O docstring afirma que 'estes campos são o que a API expõe ao frontend'. Uma varredura em `interfaces/` não encontra nenhuma ocorrência de `forecast`. O evento `EventForecast` chega ao Canal B e ao Event Store, mas o `PlanetStateOut` não traz os campos, e não há rota de eventos ativos. Sem eles o aluno não tem como **agir antes** — que é o ponto do desenho ('um evento que chega sem aviso não ensina antecipação, ensina azar').

**Encaminhamento sugerido (não aplicado):** Expor os três campos no `PlanetStateOut` (ou numa rota `/events/upcoming`) quando o frontend for construído. Registrar aqui evita que o M6 assuma que a superfície já existe.

---
### 12. `PlanetStateOut` congelou no M1

**Onde:** `interfaces/http/schemas/simulation.py`

Expõe treze campos: `temperature`, `co2`, `water`, `ice_cover`, `biomass`, `energy`, `solar_flux`, `relief`, `volcanism`, `salinity`, `ocean_circulation` (+ `planet_id`, `seed`, `tick`). Fora do contrato ficam a `carrying_capacity` (o único acoplamento física↔biologia), `ph`, nutrientes, N/P/S, `species_richness`, a pirâmide trófica inteira e o estado de evento — toda a ciência do M2/M3/M4. Não é bug: o contrato é intencionalmente estável. Mas significa que **um cliente HTTP não consegue observar quase nada do que os últimos três marcos entregaram**.

**Encaminhamento sugerido (não aplicado):** Decisão de produto. Registrado para que a ausência seja escolha e não descoberta.

---
### 13. `_founder` recebe `params` e o descarta

**Onde:** `engines/evolution/service.py`

`def _founder(params, temperature)` começa com `del params` e devolve um `Genome` com literais (`temp_tolerance=15.0`, `water_need=0.2`, `size=1.0`, `metabolism=1.0`, `trophic_level=1.0`). O genoma do primeiro colonizador — que decide as condições de partida de toda a biosfera — é **hardcoded**, enquanto todo o resto da ciência é dado versionado (Spec §5.1).

**Encaminhamento sugerido (não aplicado):** Mover os cinco literais para `evolution/params.yaml` (bloco `founder_genome`), o que os tornaria calibráveis por um especialista sem tocar em Python. Hoje eles são invisíveis à Mesa de Calibração.

---
### 14. `ConservedTotal` e `EventSlice` fora de `shared_kernel.__all__`

**Onde:** `shared_kernel/__init__.py`

`__all__` exporta `NonNegativeStocks` e `BoundedFraction`, mas **não** `ConservedTotal` — a terceira invariante, e a única que não repara. Do mesmo modo, exporta `SliceRef`, `StateDelta` e `WorldStateSnapshot`, mas nenhuma das dez fatias. Quem precisa delas (`engines/composition.py`, `engines/event/service.py`, `engines/bridge.py`) importa do módulo direto. A superfície pública declarada é, portanto, menor do que a efetivamente usada, e a assimetria entre as três invariantes irmãs é o caso mais fácil de tropeçar.

**Encaminhamento sugerido (não aplicado):** Cosmético. Vale decidir se `__all__` é contrato ou conveniência, e ser consistente.

---

## O que esta auditoria NÃO procurou

- **Correção numérica da ciência.** As fórmulas foram lidas contra as referências que os
  próprios docstrings citam (Myhre 1998, Walker/Hays/Kasting 1981, Sabine 2004, Liebig 1840,
  Budyko/Sellers 1969, Elton 1927, Toon 1997, Robock 2000) e são coerentes com elas. Verificar
  se os **valores** calibrados produzem um planeta cientificamente plausível é trabalho de
  medição, não de leitura de código — e o instrumento para isso é `shared_kernel/timeseries`.
- **Testes.** Fora de escopo por instrução. As referências a testes neste guia vêm de nomes
  citados nos docstrings e ADRs do código de produção.
- **A dívida de carbono (ADR 0020).** Já está mapeada e diagnosticada como aberta; não é achado
  desta auditoria. Ver [Mesa → Dívidas conhecidas](00-mesa-de-calibracao.md#dívidas-conhecidas-não-calibre-contra-elas).
