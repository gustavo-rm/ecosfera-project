# ECOSFERA — Briefing do frontend

Extrato do Dossiê PD&I v3, da Especificação do Evolution Engine e do backlog, com só o que o frontend precisa. Salve em `docs/frontend/BRIEFING.md`.

## 0. Como usar este briefing

- **Leia este arquivo no lugar dos documentos completos.** O Dossiê tem cerca de 7 500 linhas e a Especificação tem 28 capítulos. A maior parte trata do motor, do backend, da pedagogia teórica e do edital, e não muda nada no frontend.
- **Quando faltar detalhe**, procure pelo identificador (`RF-056`, `§22.5`, `DEC-04`) com `grep` e leia só o trecho. Não leia os originais por inteiro.
- **Se este briefing divergir dos originais, os originais valem.** Registre a divergência em `docs/frontend/DIVERGENCIAS.md`.
- **Fica de fora de propósito:** fases internas do tick, meiose, mutação, calibração, parâmetros do Apêndice B, arquitetura de backend, segurança de servidor, custos, cronograma e edital. Nada disso altera o que a interface mostra.
- As citações `§` sem prefixo apontam para a Especificação do Evolution Engine. As marcadas "Dossiê" apontam para o Dossiê.

---

## 1. Jornada do aluno, eras e trilhas

**Jornada (Dossiê §5.1):** (1) Gênese: o aluno parametriza o mundo e a IA alerta para combinações inviáveis ("com essa massa e essa distância, a água ferve"). (2) Eras: o tempo avança em escalas ajustáveis; surgem oceanos, a atmosfera se estabiliza, a vida emerge, especia, se adapta ou se extingue. (3) Intervenções: ações limitadas por pontos, cada uma com trade-off. (4) Eventos: fenômenos aleatórios testam a resiliência. (5) Reflexão: ao fim de cada era, o tutor gera relatório de cadeias causais, propõe perguntas e registra evidências.

**As nove eras (Dossiê GDD §7).** A narrativa é emergente, escrita pelas decisões do aluno. Alterna eras contemplativas e eras tensas (pacing).

| # | Era | Conteúdo novo | Desafio central | Descoberta | Objetivo pedagógico |
|---|---|---|---|---|---|
| 1 | Formação Planetária | Criação, parâmetros, física e órbita | Estabelecer um mundo viável | Zona habitável | M1/M2 · EF06CI11/14, EF09CI16 |
| 2 | Surgimento da Água | Hidrologia, oceanos, ciclo da água | Formar oceanos estáveis | Marés, correntes | M3/M5 |
| 3 | Moléculas Orgânicas | Química prebiótica, ciclos | Criar condições para a vida | Química da vida | M3 · EM13CNT201 |
| 4 | Primeiras Formas de Vida | Vida microbiana, oxigenação | Iniciar e sustentar a biosfera | Fotossíntese, O₂ | M6/M7 |
| 5 | Diversificação Biológica | Motor evolutivo, Códex de espécies | Promover biodiversidade | Especiação, adaptação | M7 · EF09CI11 |
| 6 | Colonização Terrestre | Vida em terra, biomas, sucessão | Expandir a vida ao continente | Cadeias tróficas | M6 · EF07CI07/08 |
| 7 | Grandes Extinções | Eventos sistêmicos encadeados | Sobreviver e recuperar-se | Resiliência, pontos de inflexão | M4/M9 · EF08CI16 |
| 8 | Ecossistemas Complexos | Coevolução, simbiose, equilíbrio | Manter um sistema maduro | Redes ecológicas | M6 |
| 9 | Civilizações *(futuro, fora do MVP)* | Influência, trade-offs antrópicos | Prosperar sem destruir | Sustentabilidade | M8 · EM13CNT203/206/306 |

Cidades e civilizações são só um ponto de extensão. A modelagem completa fica em trabalhos futuros.

**Níveis de domínio do jogador** (avançam por competência demonstrada, nunca por tempo): **Aprendiz** (parâmetros guiados, muitas dicas, escopo reduzido) → **Explorador** (mais variáveis, dicas sob demanda, primeiros trade-offs) → **Investigador** (subsistemas acoplados, eventos, hipóteses) → **Guardião** (problemas abertos, otimização multiobjetivo, autoria de cenários).

**Trilhas.** Fundamental II, Médio e Técnico (RF-061).

| Ano (Fund. II) | Conteúdos desbloqueados | Missões | Objetivo (BNCC) |
|---|---|---|---|
| 6º | Criar planeta, estrutura, órbita e estações | "Um mundo habitável" (posicionar na zona certa) | Condições planetárias (EF06CI11/14) |
| 7º | Atmosfera, efeito estufa, ecossistemas, cadeias | "O ar que aquece"; "Teia da vida" | Efeito estufa e teias (EF07CI07/08/13) |
| 8º | Clima, oceanos, eventos climáticos | "Tempo instável" (seca ou enchente) | Clima e circulação (EF08CI14/15/16) |
| 9º | Evolução, biodiversidade, Sistema Solar, sustentabilidade | "A vida se transforma"; "Decisões do futuro" | Evolução e decisão (EF09CI11/14/16) |

- **Médio:** ciclos biogeoquímicos, modelos científicos, investigação formal (EM13CNT301), trade-offs multiobjetivo, estatística. Missões de projeto (várias eras) e de otimização. Exige argumentação com dados.
- **Técnico:** modelagem quantitativa, séries temporais, exportação de dados, hipóteses. Entrega típica: "relatório de missão" que defende decisões com evidência.

---

## 2. Parâmetros de criação do planeta (Gênese)

Cada parâmetro é uma "alavanca" com efeitos acoplados. Nenhum é cosmético. Dossiê §5.2.

| Dimensão | Parâmetros | Disciplinas |
|---|---|---|
| Astronômica | massa, tamanho, distância da estrela, tipo e idade da estrela, nº de luas, duração do dia, inclinação axial (estações), excentricidade orbital | Astronomia, Física |
| Física | gravidade (derivada de massa e raio), campo magnético, radiação incidente, energia recebida | Física, Matemática |
| Geológica | relevo, vulcanismo, atividade tectônica, composição da crosta, recursos minerais | Geografia, Geologia, Química |
| Química/atmosférica | composição da atmosfera, O₂ e CO₂, pressão, temperatura média | Química, Física |
| Hidrológica | água total, oceanos, salinidade, distribuição | Oceanografia, Química |
| Biológica/edáfica | fertilidade do solo, nutrientes, presença de vida inicial ("semente de vida") | Biologia, Ecologia |

**Extras sugeridos:** albedo, atividade da estrela (ciclos solares), ozônio, viscosidade e energia do manto, rotação diferencial (jatos), fósforo e nitrogênio fixável, pH oceânico, gases-estufa secundários (CH₄), semente de vida.

**Exemplos de acoplamento a mostrar ao aluno:** a gravidade limita o tamanho máximo dos organismos; a inclinação axial cria estações que dirigem migrações; o campo magnético protege (ou não) a atmosfera do vento estelar.

---

## 3. O que o motor produz e o que a interface pode observar

### 3.1 Malha geodésica (DEC-04, §6.2)

- Icosaedro subdividido. **Nível padrão 5 = 10 242 células** de cerca de 50 000 km² (planeta de raio terrestre). Doze são pentagonais (5 vizinhos) e as demais hexagonais (6). Nível 5 coincide com os vértices de uma icosfera de subdivisão 5 (10·4⁵+2).
- Campos da malha: `centers` (n,3) vetores unitários; `neighbors` (n,6) com `-1` nas pentagonais; `n_neighbors`; `area_km2`; `latitude`; `parent` (índice no nível anterior, para LOD).
- A malha mapeia direto para uma malha Three.js, sem reprojeção. Mudar o nível de subdivisão invalida saves.
- Nível máximo de referência do orçamento do servidor: 40 962 células (nível 6).

### 3.2 Variáveis abióticas por célula (§7.1, `ExternalForcing`)

| Variável | Unidade | Origem | Observação para a interface |
|---|---|---|---|
| `temperature` | °C | Clima | Camada de calor, gelo, savana versus neve |
| `humidity` | 0–1 | Clima | Nuvens |
| `precipitation` | mm/tick | Clima | Nuvens, chuva |
| `solar_flux` | W/m² | Astronomia e clima | Dia e noite, estações |
| `elevation` | m | Geologia | Relevo |
| `is_water` | booleano | Oceanografia | Máscara de oceano |
| `salinity` | ppt | Oceanografia | Camada de dados |
| `ph` | 0–14 | Química | Camada de dados |
| `o2_concentration` | % | Química | Cor do céu, HUD |
| `co2_concentration` | ppm | Química | Cor do céu, HUD |
| `soil_fertility` | 0–1 | Geologia e decomposição | Solo, verde |
| `disturbances` | lista de eventos | Eventos | Efeitos localizados |

A biosfera devolve ao planeta fluxos por célula: CO₂ consumido, O₂ liberado e consumido, carbono em biomassa, matéria orgânica liberada, nitrogênio fixado. São a base do diagrama de ciclos biogeoquímicos.

### 3.3 Recursos por célula (§8.1)

`LIGHT` (fluxo, não acumula), `WATER`, `CO2`, `O2`, `MINERAL`, `NITROGEN`, `ORGANIC_MATTER`, `LIVING_BIOMASS` (estoques com teto). **Matéria é conservada e energia é dissipativa**: a energia cai a cada transferência trófica (rendimento ≈ 0,1), por isso a cadeia tem só 3 a 4 níveis. Nitrogênio é o limitante mais consequente. **Sem decompositores** a matéria fica presa em cadáveres e a produtividade colapsa (lição pedagógica valiosa, não defeito).

### 3.4 Tempo (§6.3, §22.5)

- **1 tick ≈ 1 mês simulado.** 12 ticks = 1 ano (ciclo sazonal). Uma era dura 10³ a 10⁵ ticks (cerca de 83 a 8 300 anos, por cálculo). O estudante vê **eras e anos, nunca ticks.**
- Três níveis de detalhe: **Completo** (região em foco, observação a cada tick), **Reduzido** (resto do planeta, observação a cada 12 ticks), **Agregado** (avanço rápido de era; fases 2–6 substituídas por aproximação demográfica, resolução espacial fina perdida). Fenômenos raros (como mimetismo incipiente) evoluem mais devagar no agregado.
- Fenômenos mais rápidos que 1 mês não existem no motor. Ciclos predador-presa de período curto não aparecem.

### 3.5 O que o observador (M7) entrega à interface

Somente leitura. Nada do que a UI faz volta para as regras dos organismos (Regra de Ouro).

- Séries temporais: população por linhagem, biomassa, O₂, CO₂, temperatura, diversidade.
- Registro de espécies, com identidade estável, contagem, origem e extinção (causa provável inferida).
- Filogenia: linhagem-mãe, tick, localização geográfica e **modo de especiação**.
- Teia trófica reconstruída da matriz de fluxo de energia: níveis tróficos, produtores basais, predadores intermediários e de topo, relações cíclicas.
- Índices de diversidade, taxas de **origem** e de **extinção** (de fundo e em massa).
- Métricas de atividade evolutiva e de estrutura (seção 6) e as 5 métricas de regime.
- Sinalizações de **gargalo populacional** (queda abrupta de diversidade genética) e de **efeito fundador** (divergência rápida de populações recém-estabelecidas).

### 3.6 Regras que a interface precisa respeitar

1. **O estudante só age sobre o ambiente** (§20.5): altera clima, dispara ou suprime eventos, modifica recursos, cria barreiras, introduz uma linhagem inicial de um catálogo de ancestrais. **Não** edita genomas, não atribui aptidão, não escolhe sobreviventes. O Modo Relojoeiro (seleção artificial isolada) é só ponto de extensão.
2. **Sem morfologia 3D articulada** (NO-03, DEC-14). Os organismos são parâmetros escalares com alometria. A representação visual da fauna é abstrata.
3. **Métricas agregadas planas não indicam ausência de evolução** (§21.5). Mostre também estrutura (distância genética acumulada, diversidade de estratégias, complexidade da teia).
4. **Espécie é categoria do observador** (DEC-08). Para organismos assexuados só vale o critério de distância genética, e a interface deve **dizer isso** em vez de esconder a limitação (§19.2).
5. **Colapso é legítimo.** Planetas inviáveis existem (§26). Linhagens assexuadas podem dominar no curto prazo e isso não é defeito (§14.3). Explique a causa e ofereça recomeço seguro (RP-010).
6. **Causas de morte** que a interface pode explicar (§12.7): `STARVATION`, `SENESCENCE`, `PREDATION`, `ENVIRONMENTAL`. O spec não define rótulos em português para elas nem para os estágios de vida (`PROPAGULE`, `JUVENILE`, `ADULT`, `SENESCENT`, `DEAD`). Crie rótulos placeholder e marque-os para revisão.
7. **Extinção:** distingue-se **de fundo** (contínua, baixa) de **em massa** (pico acima da linha de base, ligado a evento). Depois de um evento grande o motor deve produzir: mortalidade seletiva, vácuo ecológico, radiação adaptativa e reestruturação da teia (§20.4).
8. **Extinção global é possível** mas rara. Banco de sementes e dormência (DEC-18) tornam extinções locais reversíveis.
9. **Determinismo.** Mesma semente e mesmas intervenções dão a mesma trajetória (P8). A interface deve poder repetir um planeta pela semente.

---

## 4. Catálogo de genes e rótulos (Códex, Apêndice A)

**Use os rótulos exatamente como estão.** O genoma tem **57 loci**, diploide, em 7 blocos. A ficha da espécie lê o fenótipo (valores efetivos), não os alelos.

**MET — Metabolismo (11 genes)**

| Gene | Tipo | Domínio | Rótulo exibido |
|---|---|---|---|
| `photosynthesis` | Bool | — | Fotossíntese |
| `chemosynthesis` | Bool | — | Quimiossíntese |
| `plant_digestion` | Bool | — | Digestão vegetal |
| `animal_digestion` | Bool | — | Digestão animal |
| `detritivory` | Bool | — | Consumo de detritos |
| `decomposition` | Bool | — | Decomposição |
| `nitrogen_fixation` | Bool | — | Fixação de nitrogênio |
| `aerobic_respiration` | Bool | — | Respiração aeróbia |
| `anaerobic_respiration` | Bool | — | Respiração anaeróbia |
| `metabolic_efficiency` | Real | 0,1–1,0 | Eficiência metabólica |
| `storage_capacity` | Real | 0,1–2,0 | Capacidade de reserva |

**MOR — Morfometria (7)**

| Gene | Tipo | Domínio | Rótulo |
|---|---|---|---|
| `adult_mass` | Real | 10⁻⁶–10⁴ kg | Massa adulta |
| `height` | Real | 0–100 m | Altura |
| `canopy_area` | Real | 0–10³ m² | Área de captação |
| `growth_rate` | Real | 0,01–0,5 | Taxa de crescimento |
| `structural_investment` | Real | 0–1 | Investimento estrutural |
| `offense_investment` | Real | 0–1 | Investimento em ataque |
| `mobility` | Real | 0–1 | Mobilidade (0 = séssil) |

A massa varia dez ordens de grandeza: use **escala logarítmica** em eixos e controles.

**TOL — Tolerância (9)**

| Gene | Domínio | Rótulo |
|---|---|---|
| `temp_optimum` | −40–60 °C | Temperatura ideal |
| `temp_breadth` | 1–40 °C | Amplitude térmica |
| `humidity_optimum` | 0–1 | Umidade ideal |
| `humidity_breadth` | 0,05–1 | Amplitude de umidade |
| `ph_optimum` | 3–11 | pH ideal |
| `ph_breadth` | 0,5–6 | Amplitude de pH |
| `salinity_tolerance` | 0–45 ppt | Tolerância à salinidade |
| `water_retention` | 0–1 | Retenção de água |
| `thermal_insulation` | 0–1 | Isolamento térmico |

Cada tolerância é uma **curva** (ótimo e largura), não um limite rígido. A área sob a curva é conservada, então **ampliar a faixa custa desempenho no ótimo**: é o trade-off especialista versus generalista que a ficha deve mostrar.

**LIF — Ciclo de vida (8)**

| Gene | Tipo | Domínio | Rótulo |
|---|---|---|---|
| `maturity_age` | Inteiro | 1–500 ticks | Idade de maturidade |
| `lifespan_modifier` | Real | 0,5–2,0 | Modificador de longevidade |
| `reproduction_threshold` | Real | 0,3–0,95 | Limiar de reprodução |
| `offspring_count` | Inteiro | 1–1000 | Número de descendentes |
| `offspring_investment` | Real | 0,01–0,5 | Investimento por descendente |
| `reproductive_mode` | Cat(3) | assexuado \| sexuado \| facultativo | Modo de reprodução |
| `dormancy_capable` | Bool | — | Capacidade de dormência |
| `dispersal_distance` | Inteiro | 0–10 células | Distância de dispersão |

`offspring_count` × `offspring_investment` é o trade-off r–K (muitos descendentes baratos versus poucos caros), um dos conceitos mais transferíveis. Exponha-o na interface.

**BEH — Comportamento (11)**

| Gene | Domínio | Rótulo |
|---|---|---|
| `w_forage` | 0–1 | Prioridade de alimentação |
| `w_drink` | 0–1 | Prioridade de hidratação |
| `w_move` | 0–1 | Prioridade de deslocamento |
| `w_reproduce` | 0–1 | Prioridade de reprodução |
| `w_flee` | 0–1 | Prioridade de fuga |
| `w_attack` | 0–1 | Prioridade de ataque |
| `w_rest` | 0–1 | Prioridade de repouso |
| `w_aggregate` | 0–1 | Tendência a agrupar-se |
| `perception_radius` | 1–5 células | Raio de percepção |
| `risk_aversion` | 0–1 | Aversão ao risco |
| `philopatry` | 0–1 | Apego ao local de origem |

Os pesos `w_*` formam o gráfico radar da "personalidade genética". A explicação do comportamento é do tipo "foi beber porque a urgência de água chegou a 0,8 e o peso de hidratação é alto".

**TAG — Marcadores e condições (7)**

| Gene | Tipo | Rótulo |
|---|---|---|
| `appearance_tag` | Sym(6), alfabeto de 8 | Aparência |
| `defense_tag` | Sym(6) | Marcador de defesa |
| `offense_tag` | Sym(6) | Marcador de ataque |
| `mating_tag` | Sym(6) | Marcador reprodutivo |
| `combat_condition` | Sym(6) + coringa `#` | Regra de ataque |
| `trade_condition` | Sym(6) + coringa | Regra de troca |
| `mating_condition` | Sym(6) + coringa | Regra de acasalamento |

Marcadores são geneticamente independentes da capacidade real: daí vêm camuflagem, mimetismo e a corrida armamentista entre falsificação e discriminação. A aparência da fauna no globo vem do `appearance_tag` (vetor de 6 símbolos).

**REG — Reguladores (4)**

| Gene | Domínio | Rótulo |
|---|---|---|
| `mutation_rate_modifier` | 0,1–10,0 | Modificador de mutação |
| `recombination_rate_modifier` | 0,1–10,0 | Modificador de recombinação |
| `plasticity` | 0–0,3 | Plasticidade fenotípica |
| `neutral_marker` | Sym(4) | Marcador neutro (linha de base) |

**Vias metabólicas** (para ícones das capacidades): fototrofia, quimiossíntese, herbivoria, carnivoria, detritivoria, decomposição, fixação de nitrogênio. Um organismo pode carregar várias (mixotrofia), mas cada uma tem custo de manutenção. Uma capacidade com eficiência quase nula é "vestígio" que pode reativar.

**Necessidades fisiológicas** (§13.3): energia, hidratação, matéria estrutural, respiração, integridade térmica. A urgência de cada uma cresce de forma convexa à medida que o nível se aproxima do mínimo.

---

## 5. Eventos e intervenções

**Catálogo de eventos (§20.2).**

| Evento | Escala | Efeito primário | Efeito evolutivo |
|---|---|---|---|
| Incêndio | Local, poucas células | Remove biomassa viva; libera minerais | Seleciona rebrota, dormência, colonização rápida |
| Seca | Regional, prolongada | Reduz `WATER` | Seleciona retenção hídrica e dormência |
| Tempestade | Local | Remove biomassa; redistribui matéria orgânica | Seleciona estrutura e ancoragem |
| Glaciação | Global, muito prolongada | Desloca faixas térmicas viáveis | Seleciona tolerância ao frio; revela reservatório recessivo |
| Vulcanismo | Regional | Destrói localmente; enriquece minerais depois | Vácuo seguido de radiação |
| Impacto de meteoro | Global | Mortalidade massiva; alteração climática prolongada | Extinção em massa e radiação adaptativa |
| Eutrofização | Regional | Excesso de nutrientes; queda de `O2` | Seleciona anaerobiose e tolerância |

**Distúrbios de fundo (DEC-15).** O motor gera continuamente distúrbios locais pequenos e médios, com cauda pesada: muitos pequenos e poucos grandes. Há um mosaico permanente de manchas em estágios diferentes de sucessão. Os eventos grandes vêm do motor de eventos externos.

**Feedback causal de exemplo (Dossiê §10):** "Vulcão → aerossóis → resfriamento → estresse nos produtores → queda de população."

**Eventos do Dossiê que o motor não cobre.** O Dossiê cita meteoros, **pandemias** e **tempestades solares**. O catálogo do motor não tem pandemia, e §26 diz que epidemias não são representáveis. Trate pandemia e espécie invasora como representação abstrata de interface, sem imagens perturbadoras (RF-037), e registre a divergência.

---

## 6. Métricas, regimes e cenários (para dashboards e dados sintéticos)

**Métricas de regime (§24.4)**, painel obrigatório em modo de desenvolvimento:

| Métrica | Ordem congelada | **Homeocaos (alvo)** | Caos destrutivo |
|---|---|---|---|
| Dominância da linhagem mais abundante | > 0,8 | **0,15–0,45** | Alterna violentamente |
| Coeficiente de variação populacional | < 0,05 | **0,2–0,6** | > 1,0 |
| Extinções por 1 000 ticks | ≈ 0 | **Baixa e contínua** | Picos frequentes |
| Linhagens coexistentes | Poucas e estáveis | **Muitas, com renovação** | Colapsa periodicamente |
| Autocorrelação populacional | ≈ 1 | **Decai lentamente** | Decai abruptamente |

Teste de viabilidade do motor: em 10 000 ticks sem intervenção, a biosfera persiste e nenhuma linhagem passa de 80% da biomassa. Os dados sintéticos não devem violar isso no regime saudável.

**Métricas de atividade evolutiva (§24.3)**, para o painel de estrutura: atividade evolutiva acima da neutralidade (central), deslocamento fenotípico direcional, taxa de fixação e de origem, **complexidade da teia trófica** (níveis, conectância, proporção de relações intransitivas), **diversidade de estratégias metabólicas** (combinações distintas de capacidades com abundância não desprezível). Distância genética acumulada desde o ancestral é a leitura de estrutura mais simples.

**Modos de especiação (§19.4):** alopátrica (barreira geográfica, dominante), parapátrica (ao longo de gradiente), simpátrica (partição de nicho, rara e a mais interessante). Critérios do observador (valores iniciais do Apêndice B, sujeitos a calibração): distância genética acima de 0,35, fluxo gênico abaixo de 0,01, confirmados por 120 ticks seguidos (10 anos).

**Cinco cenários canônicos (§24.5)** que a fonte sintética deve reproduzir em forma:

| Cenário | Forma esperada |
|---|---|
| **Gênese** | Um fototrófico ancestral; depois herbívoros; depois carnívoros; pelo menos 3 níveis tróficos |
| **Gradiente** | Gradiente térmico forte sem barreiras; clina e depois especiação parapátrica |
| **Arquipélago** | Oceanos fragmentam; especiação alopátrica; divergência entre ilhas |
| **Catástrofe** | Impacto em ecossistema maduro; extinção seletiva, vácuo ecológico, radiação adaptativa |
| **Sem Decompositores** | Capacidade de decomposição suprimida; colapso da produtividade por nutrientes presos |

O sexto cenário ("Coerência de LOD") testa o motor e não se aplica ao frontend.

**Fenômenos que devem ser visíveis nos dados (§21.1):** ciclos predador-presa defasados (amplitude moderada), sucessão ecológica, estratificação vertical, camuflagem e mimetismo, corrida armamentista, partição de nicho, simbiose. Capacidade de suporte **nunca é parâmetro**: resulta de produção versus demanda e muda quando a população evolui.

---

## 7. Requisitos que o frontend cobre

Prioridade: **M** = deve, **S** = deveria, **C** = pode.

**Visualização 3D e HUD (Dossiê ERS §4.4)**

| ID | Descrição | Pri. | Critério de aceitação |
|---|---|---|---|
| RF-051 | Renderizar planeta 3D interativo no navegador | M | Planeta exibido; interação fluida no hardware-alvo |
| RF-052 | Alterar dinamicamente atmosfera, oceanos, vegetação, espécies, cidades, relevo, clima e desastres | M | Mudança de estado reflete visualmente em tempo hábil |
| RF-053 | Câmera: orbitar, zoom, focar região | M | Controles responsivos; foco em ponto de interesse |
| RF-054 | Camadas de visualização (temperatura, biomas, população, recursos) | S | Alternar camadas sobrepõe dados ao globo |
| RF-055 | HUD com indicadores e painel de ações/intervenções | M | HUD mostra estado e permite acionar |
| RF-056 | Efeitos visuais de eventos (erupção, meteoro, seca) | S | Evento tem representação visual clara |
| RF-057 | Desempenho adaptativo e **fallback WebGL 2** | M | Sem WebGPU, cai para WebGL 2 sem quebrar |
| RF-058 | Modos de acessibilidade visual (daltonismo, alto contraste) | M | Paletas alternativas e contraste conforme WCAG |
| RF-059 | Linha do tempo navegável (*scrubbing*) | C | Arrastar a linha mostra o planeta na era |

**Painel do professor (ERS §4.5)**

| ID | Descrição | Pri. |
|---|---|---|
| RF-061 | Gerir turmas, alunos e trilhas (Fundamental/Médio/Técnico) | M |
| RF-062 | Criar e atribuir desafios ancorados a objetivo BNCC e a parâmetros | M |
| RF-063 | Acompanhar progresso individual e da turma (avanço, dificuldades, engajamento) | M |
| RF-064 | Relatórios de aprendizagem (stealth assessment) ligando evidências a competências | M |
| RF-065 | Comparar planetas e decisões entre alunos | C |
| RF-066 | Exportar relatórios em PDF e CSV, íntegros e legíveis | S |
| RF-067 | Enviar feedback e mensagens ao aluno | S |
| RF-068 | Gerir consentimento e privacidade da turma (status; respeita restrições) | M |

**Avaliação (ERS §4.6), só o que toca a interface:** RF-071 (analytics pedagógico das ações, M), RF-072 (stealth assessment, M), RF-075 (rubricas, S), **RF-076** (mapear evidências → habilidades BNCC, M), **RF-077** (alertar o professor sobre aluno em dificuldade por limiar configurável, S). Outros: RF-017 (intervenções), RF-021 (séries temporais e gráficos), RF-037 (sem conteúdo sensível), RF-039 (explicação por cadeia causal), RP-010 (erro seguro).

**Requisitos não funcionais**

| ID | Requisito | Meta | Pri. |
|---|---|---|---|
| RNF-001 | Render 3D fluido | ≥ 30 FPS em Chromebook típico; fallback automático | M |
| RNF-002 | Latência ação → feedback visual | ≤ 1 s (p95) para efeitos locais | M |
| RNF-003 | Tutor (LLM) | ≤ 5 s (p95); texto em streaming | S |
| RNF-009 | Consentimento do responsável | Sem consentimento, dados não são coletados ou o uso é restrito | M |
| RNF-010 | Minimização de dados | Coletar só o necessário | M |
| RNF-014 | WCAG 2.1 AA | Auditoria por página e fluxo crítico | M |
| RNF-015 | Daltonismo | Paletas seguras; informação redundante (forma e rótulo) | M |
| RNF-016 | Baixa visão | Escala de fonte, zoom, alto contraste | M |
| RNF-017 | Teclado | Todos os fluxos operáveis sem mouse | M |
| RNF-018 | Leitor de tela (ARIA) | Elementos rotulados; descrição textual do estado do planeta | S |
| RNF-019 | Legendas e transcrições | Todo áudio com legenda ou transcrição | S |
| RNF-020 | Contraste | Texto ≥ 4,5:1; elementos ≥ 3:1 | M |
| RNF-021 | Offline parcial | Criar e continuar planeta local; sincronizar depois | S |
| RNF-022 | Adequação a crianças do EF | Testes de usabilidade com a faixa etária | M |
| RNF-023 | Portabilidade | Chrome, Edge, Firefox e Safari recentes; Chromebooks | M |
| RNF-024 | Manutenibilidade | Código modular, testado, documentado; ADR | S |
| RNF-026 | i18n (pt-BR base) | Strings externalizadas | C |

**Usabilidade para crianças (Dossiê §8.3):** linguagem simples e ícones; poucos passos por objetivo; onboarding guiado; feedback imediato e positivo; tolerância a erro; metas curtas e progresso visível; sem texto denso; controles grandes para toque; **sem mecânicas de pressão ou tempo estressante**; sem conteúdo sensível.

**Offline (§8.2).** Deve funcionar sem conexão: continuar um planeta já carregado, ajustar parâmetros, avançar a simulação local (render e autômatos), registrar ações localmente (PWA com IndexedDB). Exige conexão: tutor generativo pleno, avaliação no servidor, painel do professor, sincronização. Neste trabalho **não se implementa sincronização**.

---

## 8. Experiência: HUD, ações, feedback, avaliação e painel pedagógico

**HUD (GDD §13).** Barra superior com o nome da era e os indicadores-chave (exemplo: 24 °C, O₂ 19%, pH 8,1, Biodiversidade ▓▓▓▓▁, Prosperidade ▓▓▓▁▁). Planeta central, com órbita, zoom e foco. Ações à esquerda com pontos restantes (ex.: "Ações 3/5": Reflorestar, Industrializar, Pesquisar, Observar). Camadas à direita (Temperatura, Biomas, População, Recursos). Gráfico recolhível (O₂ ao longo das eras). Barra inferior com tempo, missão atual e tutor ("por que caiu o O₂?"). Notificações curtas e acionáveis ("Alga floresceu! Investigar").

Diretrizes: poucos indicadores sempre visíveis, com ícone, cor e valor (redundância para daltonismo); mudanças refletem imediatamente; dados sob demanda (progressive disclosure); onboarding embutido, dicas na hora certa; o tutor aparece sem bloquear o fluxo; **um conceito ou painel novo por vez.**

**Economia de ações (GDD §5).** Escassez transforma "clicar" em "decidir". É dispositivo pedagógico.

| Recurso | Obtido por | Consumido por | Efeito |
|---|---|---|---|
| Tempo / Pontos de Ação | Renovam por turno ou era | Cada intervenção | Limita mudanças por período |
| Energia | Recursos naturais, usinas | Terraformação, indústria, pesquisa | Restringe grandes intervenções |
| Orçamento | Prosperidade econômica | Obras, políticas, tecnologia | Liga economia e capacidade de ação |
| Pontos de Pesquisa | Observação, descobertas, missões | Desbloqueia a árvore científica | Progressão por conhecimento |
| Influência | Estabilidade social, feitos | Políticas ambientais, decisões antrópicas | Governa a era das civilizações (futuro) |
| Recursos Naturais | Existem no planeta (finitos) | Mineração, indústria, expansão | Ensina finitude |
| Capacidade Tecnológica | Árvore científica | Habilita intervenções avançadas | Define o que é possível |

Regras: recursos finitos por era e alguns não renováveis; toda intervenção tem custo e tempo de recarga (cooldown); há sinergias (pesquisa barateia tecnologia) e conflitos (competem pelo mesmo recurso); o balanceamento é parametrizável por trilha e nível.

**Tipos de feedback (Dossiê §10)**, sempre ancorados em dado concreto do planeta do aluno:

| Tipo | Exemplo |
|---|---|
| Imediato | "A temperatura subiu 3 °C assim que você dobrou a indústria." |
| Contextual | "Seus oceanos perderam O₂ porque as algas floresceram após o excesso de nutrientes." |
| Motivacional (esforço e estratégia) | "Boa: você testou antes de decidir — é assim que cientistas trabalham." |
| Corretivo | "A extinção não foi 'azar': faltou presa para o predador — reveja a cadeia." |
| Explicativo (cadeia causal) | "Vulcão → aerossóis → resfriamento → estresse nos produtores → queda de população." |
| Baseado em evidências | "Nas últimas 3 eras você ignorou o gráfico de CO₂; que tal consultá-lo antes de agir?" |

Regras anti-genérico: proibido "Muito bem!" isolado; todo feedback cita **um dado concreto**, aponta **um próximo passo**, respeita a faixa etária e **prefere perguntas** que induzam o raciocínio ("por que você acha que a população caiu?") antes da resposta.

**Comportamentos monitorados (stealth, §7.2) → competência.** Sequências de ação → planejamento. Previsão versus resultado (declara hipótese antes de agir?) → raciocínio científico. Uso de dados (consulta gráficos antes de decidir?) → letramento de dados. Reação a trade-offs → tomada de decisão. Resposta a eventos (recupera-se de um colapso?) → persistência. Exploração (varia parâmetros) → experimentação. Originalidade → criatividade. Encadeamento causal → pensamento sistêmico. O aluno **não vê nota**.

**Matriz de competências (10)**, com a evidência que a interface deve gerar:

| Competência | Evidência coletada |
|---|---|
| Pensamento científico (CG2) | Nº de hipóteses testadas; acerto de previsão |
| Causa-efeito (CG2) | Sequência ação → observação → explicação |
| Pensamento sistêmico | Previsão de efeitos secundários |
| Tomada de decisão (CG7) | Escolhas e justificativas |
| Análise de consequências | Revisão de estratégia |
| Letramento de dados (CG5) | Uso de dados antes de agir |
| Evolução (Biologia) | Explicações corretas |
| Persistência | Nº de tentativas e recuperação |
| Criatividade | Diversidade e originalidade de soluções |
| Argumentação (CG7) | Qualidade da justificativa (EM13CNT302) |

**Painel pedagógico (Dossiê §11).** Princípios: acionável (cada indicador sugere uma ação), compreensível num relance, respeitoso à privacidade, e **a IA informa e o professor decide**. Visões: turma (mapa de calor competência × aluno, alertas), aluno, competência/BNCC. Componentes obrigatórios: progresso por competência; habilidades desenvolvidas; dificuldades (com aluno e tópico); indicadores do stealth; evolução temporal; evidências rastreáveis à ação; recomendações da IA **sempre editáveis**.

Exemplo de conteúdo do mockup do Dossiê (use como forma dos dados simulados): "Turma 7ºB — progresso por competência 72%; Raciocínio científico 78%, Pensamento sistêmico 55%, Tomada de decisão 64%, Letramento de dados 60%. Dificuldades: 5 alunos travados em 'feedback climático' (M4). Evolução: +12% em causa-efeito nas últimas 2 semanas. Recomendação da IA: revisar 'efeito estufa' com a turma; sugerir missão de reforço a Ana, Beto e Caio." Nomes de alunos são fictícios.

---

## 9. Stack, restrições e backlog do frontend

- **Decidido (Dossiê §12):** React, Next.js (App Router), TypeScript, Zustand, TailwindCSS, Recharts ou visx para gráficos, PWA (Service Worker e IndexedDB). 3D: **Three.js + react-three-fiber + drei, WebGPU com fallback WebGL 2** (decisão RT-003; compute shaders para simulação leve). Babylon.js é a alternativa principal; CesiumJS está descartado como núcleo. Monorepo com pnpm workspaces e Turborepo.
- **Design system:** ainda não há documento. O projeto usa o prefixo `.ec-*` para tokens CSS e as fontes Space Grotesk, Inter e JetBrains Mono. Verifique o que já existe no repositório e estenda. Cores, espaçamento, raios, sombras e tema escuro são definidos na fase de fundação (ver `DESIGN_TOKENS.md`).
- **Git:** repositório `gustavo-rm/ecosfera-project`; a branch do frontend sai da `develop`.
- **Pacote do cliente:** o Dossiê o chama de `web-client`; o backlog usa `apps/web`. Descubra o real no repositório.
- **Tarefas do backlog que o frontend cobre** (use na matriz de cobertura; **filtre o CSV com script ou `grep` e não o leia inteiro**): TASK-0031 (Next.js + design system), TASK-0033 (store Zustand), TASK-0034 (cena 3D em R3F), TASK-0035 (HUD), TASK-0066 (pipeline WebGPU com fallback), TASK-0067 (shader de atmosfera), TASK-0068 (oceanos e biomas), mais as dos épicos "Frontend", "Desenvolvimento Gráfico" e "Painel do Professor". As tarefas descrevem integração por WebSocket, Auth.js e tRPC: **isso é contrato e login reais, fora do escopo agora.**
- **Atenção a uma tensão:** o Dossiê e as tarefas 0034/0066 falam em WebGPU com fallback WebGL 2, mas a tarefa 0067 fala em shader GLSL. A decisão entre TSL e GLSL fica para o ADR descrito no prompt.
- **Decisões travadas do projeto relevantes ao frontend:** os motores trocam dados por dois canais lógicos: **Canal A** (campos contínuos do estado do mundo, em ponto flutuante) e **Canal B** (eventos discretos de domínio). A identidade do planeta fica na persistência, não no envelope de evento. Decisões de arquitetura viram **ADR**. Decisões científicas e biológicas cabem à autoridade de domínio da equipe (Tássia). Use a distinção A/B só como pista para organizar a porta de dados: campos por célula de um lado, eventos do outro. **Não defina contrato.**

---

## 10. Glossário normativo (um conceito, um nome)

Use estes termos na interface e no código. Os sinônimos entre parênteses **não devem ser usados**.

**Aptidão endógena** (aptidão intrínseca) · **Coorte** (super-indivíduo) · **Linhagem** · **Marcador** (tag, na interface) · **Imposto metabólico** (custo de manutenção) · **Capacidade de suporte** (nunca um parâmetro) · **Homeocaos** · **Intransitividade** (relações do tipo pedra-papel-tesoura entre linhagens) · **Nicho** · **Evolvabilidade** · **Plasticidade fenotípica** (nunca herdada) · **Propágulo** · **Rainha Vermelha** · **Regra de Ouro** · **Tick** (só no modo de desenvolvimento; o estudante vê eras e anos).

Não existe "função de aptidão", "melhor organismo" nem "evolução dirigida" no mundo do jogo. A adaptação é o resíduo observável de sobreviver e reproduzir-se, não um objetivo.

---

## 11. Divergências e lacunas já conhecidas

Registre em `DIVERGENCIAS.md` o que o repositório confirmar. Já encontrei:

1. **Pandemia e tempestade solar** (Dossiê) não estão no catálogo de eventos do motor (§20.2). Seção 5.
2. **Rótulos em português** para causas de morte e estágios de vida não existem na Especificação. Placeholders.
3. **TSL versus GLSL** (seção 9).
4. **Nome do pacote** (`web-client` versus `apps/web`).
5. **Prioridades:** o Dossiê marca RF-054 (camadas), RF-056 (efeitos de evento) e RF-059 (linha do tempo) como S ou C. O prompt os pede completos de propósito, porque são a prova visual de que o planeta reage às variáveis.
6. **Nível de malha:** a Especificação fixa o nível 5 (10 242 células) no MVP e lista o nível 6 (40 962) como limite. Mudar o nível invalida saves.
