# Inventário de necessidades de dados da interface

**Isto não é um contrato.** Descreve o que a interface precisa receber para funcionar como está hoje. Não define formato de transporte, protocolo nem nomes de campo de rede. Os nomes são os do estado visual interno (`apps/web-client/src/core/state/types.ts`), que seguem a Especificação (§7.1, §8.1) e o Dossiê (§5.2) onde existem.

Tudo entra por uma única porta: `PlanetStateSource` (`core/source/port.ts`). Hoje quem a implementa é a fonte sintética.

Legenda. **Frequência:** *uma vez* (ao abrir), *lenta* (a cada era ou evento raro), *normal* (cerca de 3 a 8 vezes por segundo enquanto o tempo corre; menos no avanço rápido), *sob demanda*. **Crit.:** C = crítico (a tela não funciona sem), D = desejável.

## A. Identidade e parâmetros do planeta

| Item | Tipo | Unidade | Faixa usada | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|---|---|
| Semente | inteiro | — | 1–99 na interface | uma vez | Detalhe procedural, fundo de estrelas, luas; repetir um planeta | C |
| Massa, raio | real | M⊕, R⊕ | 0,1–8; 0,4–2,2 | uma vez | Gênese; gravidade derivada | D |
| Distância da estrela | real | UA | 0,1–5 (log) | uma vez | Gênese, diagrama de zona habitável, tamanho aparente da estrela | C |
| Tipo e idade da estrela | categoria; real | M, K, G, F, A; Ga | 0,5–10 | uma vez | Cor, intensidade e tamanho da estrela | C |
| Número de luas | inteiro | — | 0–4 | uma vez | Luas em órbita | D |
| Duração do dia | real | h | 6–96 | uma vez | Ritmo de rotação (estilizado) | D |
| Inclinação axial, excentricidade | real | °, — | 0–60; 0–0,6 | uma vez | Orientação das estações, variação anual da luz | C |
| Atividade da estrela, campo magnético | real | 0–1 | — | lenta | Auroras, erosão da atmosfera | D |
| Gravidade, energia recebida | real | g, W/m² | derivados | uma vez | Gênese (valores derivados) | D |
| Relevo, vulcanismo, tectônica, minerais | real | 0–1 | — | uma vez | Gênese; na fonte sintética geram o terreno | D |
| Composição da crosta | categoria | — | 4 classes | uma vez | Paleta de rochas e solos | C |
| Pressão, O₂, CO₂, CH₄, albedo, ozônio (iniciais) | real | bar, %, ppm | ver Gênese | uma vez | Gênese | D |
| Água total, distribuição das terras, salinidade, pH | real | 0–1, ppt, pH | — | uma vez | Gênese | D |
| Fertilidade, nutrientes, semente de vida | real; booleano | 0–1 | — | uma vez | Gênese | D |
| Alertas de combinações inviáveis | lista de códigos | — | 9 regras hoje | sob demanda | Gênese ("a água ferve") | D |
| Faixa de zona habitável | par de reais | UA | — | sob demanda | Diagrama orbital | D |

Observação: no Gênese a interface precisa de uma **prévia** do planeta para um conjunto de parâmetros, em dois momentos (início e futuro provável), com resposta em menos de 1 s.

## B. Campos por célula

Malha: nível (3 a 5 hoje; 5 no MVP), número de células (10·4^L+2) e **ordem das células**. A ordem precisa ser fixa e conhecida. A Especificação (§6.2) não a define; hoje vale a convenção de `core/mesh/cellOrder.ts`, travada por teste (D-29). O contrato precisa fixá-la, junto com a regra de `parent`. A interface também usa `parent` para LOD, mas consegue derivá-lo.

| Campo | Tipo | Unidade | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|---|
| `elevation` | real | m | lenta | Relevo, costa, profundidade do mar, camada | C |
| `is_water` | booleano | — | lenta | Máscara de oceano, onde há vida aquática | C |
| `temperature` | real | °C | normal | Camada, gelo, cor da vegetação, sonda | C |
| `humidity` | real | 0–1 | normal | Nuvens, aridez do solo | C |
| `precipitation` | real | mm/tick | normal | Camada, bioma | D |
| `solar_flux` | real | W/m² | normal | Hoje só disponível à sonda | D |
| `salinity`, `ph` | real | ppt, pH | lenta | Camadas | D |
| `o2_concentration`, `co2_concentration` | real | %, ppm | normal | Camadas | D |
| `soil_fertility` | real | 0–1 | lenta | Cor do solo, camada | D |
| Recursos `WATER`, `MINERAL`, `NITROGEN`, `ORGANIC_MATTER` | real | relativo | normal | Camadas, painel regional, manchas de matéria presa | D |
| Biomassa por grupo trófico (produtores, herbívoros, carnívoros) | real | relativo | normal | Verdor, florações, quantidade de organismos, camadas | C |
| Linhagem dominante por grupo | índice de linhagem | — | normal | Aparência dos organismos, variedade de matiz, painel regional | C |
| Riqueza de linhagens | inteiro | — | normal | Camada, variedade visual | D |
| Classe de bioma | categoria (13 hoje) | — | lenta | Camada, sonda, descrição textual. **Pode ser derivada no cliente** se a regra for definida pela autoridade de domínio. | D |
| Cobertura de gelo, cobertura de nuvens | real | 0–1 | normal | Calotas, nuvens. Podem ser derivadas no cliente. | C |
| Lava ou calor de superfície | real | 0–1 | lenta | Mundo incandescente, pontos quentes | D |
| Máscaras de distúrbio por tipo | real | 0–1 | normal durante eventos | Efeitos localizados, camada de distúrbios | C |
| Densidade de uma linhagem escolhida | real | relativo | sob demanda | Camada "distribuição", ficha da espécie | D |

O frontend aproveita arrays que não mudaram **por referência**. Qualquer transporte que permita dizer "este campo não mudou" economiza envio à GPU.

## C. Quadro de observação da biosfera (somente leitura)

| Item | Tipo | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|
| Registro de linhagens: identificador estável, nome, linhagem-mãe, papel e nível trófico, ambiente, origem (momento, local, modo de especiação), extinção (momento, causa provável), se é assexuada, população atual | lista | normal (população); lenta (o resto) | Códex, ficha, árvore, teia, descrição | C |
| Fenótipo efetivo por gene (57 loci do Apêndice A) | mapa gene → valor | lenta | Ficha: capacidades, curvas de tolerância, radar de comportamento, marcadores, ciclo de vida | C |
| Presas de cada linhagem; relações cíclicas (intransitivas) | listas | lenta | Teia, ficha | C |
| Fluxo de energia por ligação | real | normal | Espessura das setas da teia | D |
| Energia por nível trófico | lista de reais | normal | Pirâmide | C |
| Índices: Shannon, equitabilidade, riqueza | reais | normal | Estrutura, HUD (biodiversidade) | C |
| Estrutura: distância genética acumulada, estratégias metabólicas, níveis, conectância, proporção intransitiva | reais | normal | Painel de estrutura | C |
| Taxas de origem e de extinção; sinal de extinção em massa | reais; booleano | normal | Estrutura, aviso, dessaturação do planeta | C |
| Sinalizações de gargalo e de efeito fundador | lista (tipo, linhagem, momento) | lenta | Estrutura, ficha, árvore | D |
| As cinco métricas de regime, ou as séries para calculá-las | reais | sob demanda | Console de laboratório (obrigatório em desenvolvimento) | D |
| Estoques e fluxos de carbono, nitrogênio, oxigênio e água | lista por elemento | normal | Diagrama de ciclos | C |
| **Histórico**: séries de O₂, CO₂, temperatura, biomassa, diversidade, estrutura, taxas e população por linhagem, para um intervalo e um número de amostras | séries | sob demanda | Todos os gráficos, minigráfico do HUD | C |
| Marcas no tempo: início de era, evento, extinção, especiação, intervenção | lista | sob demanda | Linha do tempo, gráficos, relatório de era | C |

## D. Eventos

| Item | Tipo | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|
| Identificador, tipo (catálogo §20.2), escala, origem (motor, estudante, fundo) | — | no início do evento | Efeitos, notificações, linha do tempo | C |
| Local (célula ou latitude e longitude) e raio | — | no início | Onde desenhar, foco da câmera | C |
| Intensidade atual e fase (aviso, em curso, depois) | real 0–1; categoria | normal | Força do efeito, texto | C |
| Momentos: início do aviso, início, fim | tempo | no início | Telegrafia, contagem "em N anos" | C |
| Instrumento que detecta o aviso | categoria | no início | Notificação de telegrafia | D |
| Cadeia causal (passos nomeados) e causa provável | lista de códigos | no início | "Por quê?", tutor, relatório | C |
| Se foi suprimido | booleano | quando ocorrer | Texto, intensidade | D |

## E. Estado de jogo

| Item | Tipo | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|
| Era atual (1 a 9), início e fim da era, tempo simulado | — | normal | HUD, linha do tempo, missões | C |
| Indicadores: temperatura média, O₂, pH, biodiversidade, prosperidade | reais | normal | HUD | C |
| Globais de aparência: CO₂, CH₄, pressão, aerossóis, nível do mar, fração de oceano e de gelo, calor de superfície, pulso de extinção, matéria presa | reais | normal | Céu, oceano, descrição | C |
| Modo de atualização (normal ou avanço rápido) e nível de detalhe disponível | categorias | quando mudar | Selo no HUD, ocultar fauna | C |
| Recursos da economia de ações (6) | reais | quando mudar | HUD, cartões | C |
| Catálogo de intervenções: custo, recarga, ganho, custo colateral, pré-requisito, opções, alvo | lista | uma vez | Painel de ações, diálogo | C |
| Árvores científica e tecnológica: nós, pré-requisitos, custo, domínio demonstrado | lista | lenta | Pesquisa, bloqueios explicados | C |
| Missões, objetivos de era, conquistas, com progresso | listas | normal | Missões, barra inferior | D |
| Entradas do Códex e do Diário | listas | quando mudar | Códex | D |
| Nível do estudante | categoria (4) | lenta | Exibição; revela alavancas do Gênese | D |
| Regiões e camadas já reveladas | conjunto | quando mudar | Hachura das camadas | D |

Hoje economia, pesquisa, missões e nível são calculados no cliente com regras provisórias. É decisão de contrato o que passa ao servidor.

**Comandos que a interface emite** (só ações sobre o ambiente, §20.5): varredura, pesquisar, irrigar, reflorestar, fertilizar, resfriar, aquecer, criar barreira, introduzir linhagem do catálogo, provocar evento, suprimir evento. Cada um leva: tipo, célula alvo quando houver, opção escolhida, momento. Mais os comandos de relógio: pausar, continuar, velocidade, ir a um instante, avançar até o fim da era.

## F. Tutor e feedback

| Item | Tipo | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|
| Resposta do tutor: dado concreto citado (texto com valores), pergunta que induz raciocínio, cadeia causal, próximo passo, origem (regras ou LLM) | estruturado | sob demanda | Painel do tutor | C |
| Texto em fluxo contínuo | pedaços de texto | sob demanda | Painel do tutor (a interface já exibe por partes) | D |
| Relatório de fim de era: cadeias causais da era, perguntas de reflexão, números de início e fim | estruturado | fim de era | Relatório | C |
| Feedback do professor ao aluno | texto | quando houver | (a tela do aluno ainda não exibe mensagens recebidas) | D |

## G. Professor, coordenação e responsável

| Item | Tipo | Freq. | Onde é usado | Crit. |
|---|---|---|---|---|
| Turmas (nome, trilha) e alunos pseudonimizados (código, apelido) | listas | ao abrir | Todas as telas | C |
| Status de consentimento e restrições por aluno | categoria; lista | ao abrir | Privacidade; filtra todas as médias | C |
| Matriz de 10 competências por aluno; médias por turma | reais 0–1 | ao abrir | Mapa de calor, visão do aluno, coordenação | C |
| Evolução temporal por aluno e por turma | série semanal | ao abrir | Evolução recente | D |
| Evidências: competência, tipo, **ação que a gerou** (qual, era, momento) | lista | ao abrir | Visão do aluno | C |
| Alertas de dificuldade: aluno, tópico, competência; limiar configurável | lista | ao abrir | Visão de turma | C |
| Cobertura por habilidade BNCC (parte da turma, número de evidências) | lista | ao abrir | BNCC, coordenação | C |
| Recomendações da IA: alvo, tópico, texto, estado | lista | ao abrir | Turma, aluno. O professor edita, aceita ou descarta: a interface devolve o texto editado e o estado. | C |
| Planeta de cada aluno (o suficiente para reconstruir a imagem) e linha do tempo de decisões | — | sob demanda | Comparar | D |
| Séries numéricas de um planeta | séries | sob demanda | Exportação para Matemática | D |
| Desafios: habilidade, cenário ou parâmetros, restrições, critério, turma | estruturado | a interface cria | Criador de desafios | C |
| Engajamento | real | ao abrir | Visão do aluno | D |

## H. Eventos de evidência gerados pela interface

Saem do cliente. **Sem dados pessoais:** não levam nome, conta nem texto digitado. Todo evento leva também um número de sequência local, o momento simulado e a era. Definição em `core/evidence/bus.ts`. Hoje ficam só em memória e aparecem no console de laboratório.

| Evento | Campos | Evidência de |
|---|---|---|
| `prediction_declared` | intervenção, variável, direção esperada | Raciocínio científico |
| `prediction_compared` | intervenção, variável, previsto, obtido, se coincidiu | Raciocínio científico |
| `chart_opened` | gráfico, tempo simulado desde a última ação | Letramento de dados |
| `layer_viewed` | camada | Letramento de dados |
| `panel_opened` | painel (tutor, painel regional), tempo desde a última ação | Uso de dados |
| `decision_time` | intervenção, segundos entre abrir e confirmar, o que foi consultado nesse intervalo | Tomada de decisão |
| `intervention_applied` | intervenção, se havia previsão | Planejamento |
| `param_explored` | parâmetro, número de mudanças | Experimentação |
| `collapse_recovered` | cenário, número de tentativas | Persistência |
| `reflection_answered` | pergunta, **tamanho** da resposta | Argumentação |
| `mission_goal_met` | missão | Progresso |
| `species_inspected` | linhagem | Curiosidade, evolução |
| `tutor_question` | pergunta | Busca de explicação |
| `timeline_scrubbed` | de, para | Análise de consequências |
| `scan_done` | número de regiões | Exploração |

## O que o backend precisa fornecer para substituir a fonte sintética

1. Tudo que está marcado como crítico em B, C, D e E, traduzido para `PlanetFrame` por uma implementação de `PlanetStateSource`.
2. A ordem das células e o nível da malha.
3. Um meio de pedir histórico (séries e marcas) por intervalo.
4. Um meio de pedir um instante passado (rolagem do tempo) ou instantâneos suficientes para o buffer do cliente.
5. A prévia do Gênese.
6. Aceitar os comandos da seção E e devolver o efeito no estado.
7. Dizer o modo (normal ou avanço rápido) e o nível de detalhe de cada atualização.
