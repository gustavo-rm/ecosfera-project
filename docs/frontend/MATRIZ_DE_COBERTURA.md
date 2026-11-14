# Matriz de cobertura

Estados: **FV** = feito e verificado (executado e visto, ou coberto por teste); **FN** = feito e não verificado no critério de aceitação original; **P** = parcial; **NF** = não feito.

"Verificado" aqui quer dizer: em Chromium headless com WebGL por software, com dados sintéticos. Nada foi verificado em Chromebook real, com leitor de tela real, nem com usuários.

## Requisitos funcionais

| ID | Requisito | Estado | Como foi verificado, ou motivo |
|---|---|---|---|
| RF-051 | Planeta 3D interativo no navegador | FV | Catálogo 01 e 09; e2e. Fluidez no hardware-alvo não verificada. |
| RF-052 | Mudança dinâmica de atmosfera, oceanos, vegetação, espécies, relevo, clima, desastres | FV em parte | Os testes cobrem o mapeamento de estado para canais e uniformes, não a imagem final; a imagem foi conferida a olho no catálogo. Ver a seção "Cobertura da tabela" abaixo. Cidades: só ponto de extensão. |
| RF-053 | Câmera: orbitar, zoom, focar região | FV | e2e de teclado; gestos de toque implementados, **não testados em aparelho de toque**. |
| RF-054 | Camadas de visualização | FV | 18 camadas; catálogo 03 a 05; sonda e painel regional. |
| RF-055 | HUD com indicadores e painel de ações | FV | Catálogo 09; e2e. |
| RF-056 | Efeitos visuais de eventos | FV | Catálogo 06. Chuva em zoom e relâmpago visível em captura estática: não mostrados. |
| RF-057 | Desempenho adaptativo e fallback WebGL 2 | FV em software | Sempre WebGL 2 (ADR FE-0001); governador medido. |
| RF-058 | Modos de acessibilidade visual | FV | Três paletas, alto contraste; testes de contraste e daltonismo. |
| RF-059 | Linha do tempo navegável | FV | e2e (seta rola o passado); buffer testado. Interpolação: fusão na GPU entre instantâneos. |
| RF-061 | Gerir turmas, alunos e trilhas | P | Tela feita com dados simulados; edições só locais. Sem backend. |
| RF-062 | Criar e atribuir desafios BNCC | P | Formulário completo; o desafio não chega ao aluno (sem backend). |
| RF-063 | Acompanhar progresso individual e da turma | FV (dados simulados) | Catálogo 16. |
| RF-064 | Relatórios ligando evidências a competências | P | Evidências rastreáveis à ação na visão do aluno; a avaliação real não existe. |
| RF-065 | Comparar planetas e decisões | P | Miniaturas 2D e linhas do tempo; 3D só em "Abrir em 3D" (D-16). |
| RF-066 | Exportar PDF e CSV | FV | Teste unitário da estrutura do PDF e do CSV. **Não abri o PDF em um leitor.** |
| RF-067 | Enviar feedback ao aluno | P | Envio registrado localmente; o aluno não recebe. |
| RF-068 | Consentimento e privacidade | FV (dados simulados) | Alunos sem consentimento ficam fora das médias; tela do responsável. |
| RF-076 | Evidências → habilidades BNCC | P | Tela de cobertura com mapeamento provisório. |
| RF-077 | Alerta de aluno em dificuldade, limiar configurável | FV (dados simulados) | Controle de limiar muda a lista. |
| RF-017, 021, 037, 039, RP-010 | Intervenções, séries, sem conteúdo sensível, cadeia causal, erro seguro | FV | Diálogo de intervenção, dashboards, eventos biológicos abstratos, "Por quê?", recomeço pelo Gênese. |

## Requisitos não funcionais

| ID | Requisito | Estado | Como foi verificado, ou motivo |
|---|---|---|---|
| RNF-001 | 30 FPS em Chromebook, fallback automático | FN | 34,8 FPS em WebGL por software com qualidade automática; **Chromebook real não disponível**. |
| RNF-002 | Ação → feedback em até 1 s (p95) | FV em software | p95 de 268 ms (e2e). |
| RNF-014 | WCAG 2.1 AA | P | axe-core: 0 violações em 43 combinações; falta auditoria manual e leitor de tela. |
| RNF-015 | Daltonismo | P | Paletas sequenciais, divergentes e de séries testadas com simulação. Exceção: a camada de biomas depende de cor no globo e suas 13 cores não foram testadas. |
| RNF-016 | Baixa visão | FV | Escala de fonte, alto contraste. Zoom de 200% do navegador não testado. |
| RNF-017 | Teclado | FV | 14 fluxos e2e. |
| RNF-018 | Leitor de tela | P | Descrição gerada, regiões `aria-live`, modo texto; **não testado com leitor real**. |
| RNF-019 | Legendas e transcrições | N/A hoje | Não há áudio. |
| RNF-020 | Contraste | FV | Teste sobre os tokens nos 4 temas; axe-core. |
| RNF-021 | Offline parcial | P | Service worker, IndexedDB, retomada local (a revisão achou a semente errada na retomada fora do cenário Gênese; corrigido, sem teste automático). Sem sincronização. Instalação e uso offline **não testados**. |
| RNF-022 | Adequação a crianças | NF | Exige teste com a faixa etária. Diretrizes de linguagem e controles grandes foram seguidas. |
| RNF-023 | Portabilidade | P | Só Chromium exercitado. |
| RNF-026 | i18n, pt-BR | FV com ressalva | Teste: toda chave usada existe. A checagem de texto fixo só pega frases de três palavras ou mais em JSX. Restam símbolos de unidade no código (`mm/mês`, `°C`, `ppm`) e os rótulos do Apêndice A, por decisão (D-05). |

## Tarefas do backlog (épicos Frontend, Desenvolvimento Gráfico, Painel do Professor)

| ID | Título | Estado | Observação |
|---|---|---|---|
| TASK-0031 | Next.js + design system | FV | Tokens e componentes-base. Storybook (opcional) não feito. |
| TASK-0032 | Login e sessão | NF, fora do escopo | Auth.js e tRPC são login e contrato reais. Há sessão simulada com seletor de papel. |
| TASK-0033 | Estado global (Zustand) | P | Stores tipadas. "Deltas por WebSocket": fora do escopo; a porta de dados é o ponto de entrada. |
| TASK-0034 | Cena 3D (react-three-fiber) | FV em WebGL 2 | WebGPU não usado (ADR FE-0001). |
| TASK-0035 | HUD de indicadores | FV | Alimentado pela porta de dados. |
| TASK-0036 | Controles de tick e intervenção | FV | O estudante vê anos (a ficha mostrava "ticks" na idade de maturidade; corrigido após a revisão). Sem tRPC. |
| TASK-0037 | Painel de feedback causal | FV | Regras agora; a mesma forma serve ao LLM. |
| TASK-0038 | Auditoria de acessibilidade | P | Parte automática feita; parte manual pendente. |
| TASK-0039 | PWA e offline | P | Sem sincronização. |
| TASK-0063 | Dashboards de progresso por competência | P | Dados simulados; sem tRPC. |
| TASK-0064 | Criação de missões BNCC | P | Interface feita; sem servidor. |
| TASK-0065 | Relatórios e exportações | FV no cliente | PDF e CSV gerados no navegador. |
| TASK-0066 | Pipeline WebGPU + fallback | P | Pipeline WebGL 2 com orçamento medido; WebGPU adiado por ADR. |
| TASK-0067 | Shader de atmosfera | FV | Reage a pressão, O₂, CO₂, CH₄ e aerossóis. |
| TASK-0068 | Oceanos e biomas | FV | Transições suaves por fusão na GPU. |
| TASK-0069 | Espécies e partículas | P | Organismos instanciados e efeitos de evento; não há sistema de partículas geral. |
| TASK-0070 | Câmera e efeitos visuais | P | Câmera completa e acessível por teclado; sem pós-processamento (decisão de desempenho). |

## Itens da missão fora das listas acima

| Item | Estado | Observação |
|---|---|---|
| Cinco cenários canônicos | FV | Testes do motor sintético. |
| Painel das cinco métricas de regime | FV | Console de laboratório; teste unitário. |
| Console de laboratório | FV | Catálogo 17. |
| Barramento de evidências sem transporte | FV | 15 tipos de evento; visualizador no console. |
| Gênese com prévia ao vivo | FV | Catálogo 14. |
| Códex e ficha da espécie | FV | Catálogo 13 e 14. |
| Árvores científica e tecnológica | FV | Desbloqueio por domínio demonstrado. |
| Relatório de fim de era | FV | e2e. |
| Onboarding | FN | Seis dicas, uma por vez; não testado com crianças. |
| Modo Relojoeiro | NF, por escopo | Só a constante de extensão. |
| Imagens de referência com tolerância | NF | O catálogo é determinístico, mas a comparação automática não foi montada. |
| Correntes oceânicas, chuva em zoom | NF | Marcadas como opcionais ou de menor peso. |

## Cobertura da tabela "variável do estado → efeito no planeta"

Avaliação por linha depois da revisão independente. "Teste de mapeamento" quer dizer: o teste varia a variável e confere o canal ou uniforme que o shader lê. Nenhum teste automático confere pixels.

| Linha | Implementação | Teste |
|---|---|---|
| `elevation`, `is_water` | Sim | Mapeamento |
| Vulcanismo e tectônica | Sim | Mapeamento para lava; para tectônica, só o dado de elevação (com controle em tectônica 0) |
| Composição da crosta | Sim | Mapeamento |
| Água total, temperatura | Sim | Mapeamento |
| `salinity`, `ph` | Sim | Mapeamento |
| Pressão | Sim | Mapeamento (uniformes lidos pelo GLSL) |
| O₂, CO₂, CH₄, aerossóis | Sim | Mapeamento |
| `humidity`, `precipitation` | Sim | Umidade: mapeamento. Precipitação: só pelo evento de tempestade |
| Campo magnético, atividade da estrela | Sim | Mapeamento (uniformes) |
| `temperature` | Sim | Mapeamento |
| `solar_flux` | **Parcial**: o campo existe e aparece na sonda de dados do laboratório; não alimenta aparência nem camada | Sem teste |
| Inclinação axial | Sim | Orientação do eixo em relação à estrela (teste novo) e gelo sazonal |
| Excentricidade, duração do dia | Sim no render (intensidade da luz no ano; ritmo de rotação); não afetam nenhum dado | Só repasse do parâmetro |
| Tipo da estrela | Sim | Mapeamento de cor e intensidade |
| Idade da estrela | Sim (entra na luminosidade) | **Sem teste** |
| Tamanho aparente da estrela | Sim (a mesma fórmula no céu e no uniforme, após a revisão) | Uniforme; o céu em si não é testado |
| Número de luas | Sim | Só repasse do parâmetro |
| `soil_fertility` | Sim | Mapeamento |
| Biomassa fototrófica, bioma | Sim | Mapeamento |
| Biodiversidade, riqueza | Sim | Mapeamento |
| Coortes por linhagem | Sim | Só os campos de linhagem dominante e o habitat; **a instanciação não tem teste**, só captura |
| Matéria orgânica acumulada | Sim | Mapeamento |
| Extinção em massa | Sim | Dessaturação e retorno a zero; a "volta da variedade" só nos testes de riqueza do motor |
| Distúrbios | Sim | Mapeamento por tipo de evento |
| Temperatura muito alta, Era 1 | Sim | Mapeamento |
