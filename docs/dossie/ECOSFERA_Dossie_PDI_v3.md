---
title: "ECOSFERA — Dossiê Técnico-Científico de PD&I"
subtitle: "Jogo Educacional Multidisciplinar baseado em Inteligência Artificial e Simulação de Sistemas Planetários"
author: "Equipe ECOSFERA"
date: "Versão 3.0 — 2026"
lang: pt-BR
toc: true
toc-title: "Sumário"
toc-depth: 3
numbersections: false
---

**Documentação oficial · Especificação técnica · Base para implementação · Referência acadêmica**

Controle de Versões

  -------------------------------------------------------------------------
  **Versão**        **Data**          **Descrição**       **Responsável**
  ----------------- ----------------- ------------------- -----------------
  0.1               2026              Proposta            Equipe
                                      técnico-acadêmica e 
                                      resumo executivo    

  0.2               2026              Levantamento de     Equipe
                                      requisitos (ERS)    

  0.3               2026              Modelagem           Equipe
                                      pedagógica          

  0.4               2026              Game Design         Equipe
                                      Document (GDD)      

  0.5               2026              Arquitetura de      Equipe
                                      software            

  0.6               2026              Plano de            Equipe
                                      desenvolvimento     
                                      incremental         

  1.0               2026              Consolidação PD&I   Equipe
                                      (este documento)    
  -------------------------------------------------------------------------

Nota de Consolidação e Organização

Este documento consolida os artefatos produzidos ao longo do projeto e
incorpora, na versão 3.0, todas as decisões arquiteturais e tecnológicas
posteriores — incluindo a Arquitetura de Engines, a Observabilidade por
Design e a evolução emergente —, além das decisões da versão 2.0 --- notadamente a migração da plataforma para
Node.js/NestJS, a adoção de TypeORM, a separação do PostgreSQL em
schemas platform e rag, e o barramento de eventos escalonado (Redis
Streams → NATS). Onde versões divergiam, prevalece o estado real da
implementação. O Histórico de Atualizações (seção final) detalha cada
mudança e sua motivação.

Para evitar redundância, seções da proposta original superadas por
documentos posteriores (arquitetura da solução, comparativo de
arquiteturas, tecnologias e cronograma detalhado) não são repetidas: seu
conteúdo definitivo encontra-se nas Partes de Arquitetura e de Plano de
Execução.

Observação de rastreabilidade: o inventário do projeto menciona um Plano
de Implementação da IA e um Plano de Desenvolvimento Gráfico como
documentos autônomos. Esses documentos não foram produzidos como
artefatos independentes; seu conteúdo está coberto e consolidado nos
capítulos de Arquitetura da Inteligência Artificial e de Desenvolvimento
Gráfico e Interface (integrados à Arquitetura e ao GDD).

# PARTE I — Concepção, Fundamentos e Objetivos


## 1 Resumo Executivo

A oportunidade

O ensino de ciências ainda é fragmentado: o aluno estuda Física,
Química, Biologia e Geografia em caixas separadas e raramente entende
como tudo se conecta no mundo real. O resultado é desmotivação e
conhecimento que não \"gruda\". Ao mesmo tempo, escolas buscam
ativamente ferramentas digitais que engajem a geração que cresceu com
jogos --- e a IA tornou possível criar experiências educacionais que
antes eram inviáveis.

Há aqui um encontro raro entre **necessidade clara do mercado**,
**maturidade tecnológica** e **timing**.

A solução, em uma frase

**ECOSFERA** é um jogo educacional onde cada estudante **cria e evolui
seu próprio planeta**. Ao ajustar elementos como clima, oceanos, vida e
recursos, o aluno vê --- em um mundo 3D vivo --- as consequências de
cada decisão. Aprende ciências *fazendo*, não decorando. Uma
inteligência artificial acompanha o aluno, explica o que aconteceu e por
quê, e gera relatórios de aprendizagem para o professor.

Por que tem valor

-   **Engaja de verdade.** Transforma conteúdo abstrato em um mundo que
    o aluno constrói e cuida --- como um jogo, mas com propósito
    educacional.

-   **Ensina o que o mercado pede.** Pensamento crítico, tomada de
    decisão, sustentabilidade e a visão de \"tudo está conectado\" ---
    exatamente as competências valorizadas hoje e previstas na BNCC.

-   **Dá superpoderes ao professor.** Um painel mostra, de forma
    automática, o que cada aluno aprendeu --- sem prova extra, sem
    trabalho manual.

-   **Diferencia a marca.** É inovador, visualmente impressionante e
    alinhado às pautas de educação, sustentabilidade e IA --- forte
    apelo institucional e de comunicação.

Potencial de crescimento

Começa como um produto para ciências no Ensino Fundamental, Médio e
Técnico, e pode se expandir para:

-   **Novas disciplinas e níveis** (do fundamental à universidade).

-   **Modo colaborativo** --- turmas inteiras compartilhando uma galáxia
    de planetas.

-   **Realidade virtual e aumentada** --- \"entrar\" no próprio planeta.

-   **Mercado amplo** --- escolas públicas e privadas, redes de ensino,
    editoras, programas governamentais e licenciamento internacional (o
    conceito é universal e traduzível).

Por que é viável

-   **Baixo custo de tecnologia:** construído sobre ferramentas abertas
    e gratuitas, sem licenças caras --- roda direto no navegador, sem
    instalação.

-   **Entrega em etapas:** um protótipo funcional pode ser demonstrado
    cedo, validando valor antes de grandes investimentos.

-   **Competência já existe na casa:** aproveita diretamente a
    experiência da equipe em software e inteligência artificial.

-   **Base para pesquisa e captação:** o formato tem perfil de **projeto
    financiável** (editais de inovação, P&D, fomento educacional),
    abrindo fontes de recurso além da receita comercial.

O impacto

Melhores resultados de aprendizagem, alunos mais motivados e professores
com mais tempo e informação --- enquanto a empresa se posiciona na
vanguarda de **educação + IA**, um dos setores de maior crescimento e
visibilidade.

O pedido

Autorização para desenvolver um **protótipo demonstrável** (planeta +
primeiras dinâmicas + tutor de IA) que comprove o conceito e permita
apresentá-lo a escolas parceiras e potenciais financiadores.

> *ECOSFERA não é só um jogo. É uma nova forma de ensinar ciências --- e
> uma vitrine do que a empresa pode fazer com inovação e IA.*

## 2 Introdução, Motivação e Problema

### 3.1 O problema da fragmentação disciplinar

O ensino tradicional de ciências, na maioria das redes, organiza o
conhecimento em disciplinas estanques, com pouca comunicação entre si. O
estudante estuda **Matemática** (funções, proporção, estatística),
**Física** (gravidade, energia, órbitas), **Química** (ciclos,
compostos, atmosfera), **Biologia** (evolução, ecologia, reprodução),
**Geografia** (relevo, clima, tectônica), **Ciências**, **Ecologia** e
**Astronomia** como blocos isolados, avaliados separadamente e raramente
reconectados. O resultado é bem documentado na literatura: conhecimento
**inerte** --- que o aluno \"sabe\" para a prova, mas não mobiliza para
interpretar fenômenos reais --- e dificuldade de **transferência** entre
contextos.

Fenômenos naturais, porém, são **intrinsecamente sistêmicos**. A
temperatura de um planeta depende da distância à estrela
(Astronomia/Física), do efeito estufa (Química), do albedo do gelo
(Física/Geografia), da cobertura vegetal (Biologia) e das correntes
oceânicas (Oceanografia); uma extinção altera cadeias tróficas
(Ecologia), que alteram ciclos de carbono (Química), que realimentam o
clima. Ensinar essas conexões com quadro e giz é difícil justamente
porque **o meio estático não expressa dinâmica, retroalimentação nem
emergência**.

### 3.2 O que um ambiente de simulação inteligente promove

Uma simulação interativa e inteligente é um **micromundo** (no sentido
de Papert): um sistema formal, manipulável e transparente, onde ideias
abstratas ganham corpo e podem ser exploradas. Especificamente, ECOSFERA
foi concebido para promover:

-   **Aprendizagem ativa e por descoberta** --- o aluno não recebe o
    conceito pronto; formula hipóteses (\"se eu aumentar o CO2\...\") e
    testa.

-   **Pensamento científico** --- o ciclo *hipótese → experimento →
    observação → revisão* é a própria mecânica do jogo.

-   **Resolução de problemas e tomada de decisão** sob incerteza e
    recursos limitados.

-   **Interdisciplinaridade e pensamento sistêmico** --- a integração
    não é temática, é **estrutural**: as variáveis de diferentes
    disciplinas estão acopladas no modelo.

-   *Análise de* trade-offs --- toda ação tem custo e benefício; não há
    \"botão de vencer\".

-   **Criatividade** --- não há um único planeta \"correto\"; há
    infinitos mundos viáveis a descobrir.

### 3.3 Por que *Serious Games* e IA

*Serious games* --- jogos cujo propósito primário não é o
entretenimento, mas a aprendizagem (ABT, 1970; MICHAEL; CHEN, 2006) ---
são particularmente eficazes para conteúdos **procedimentais, sistêmicos
e de tomada de decisão**, exatamente o perfil aqui. Meta-análises
(WOUTERS et al., 2013; CLARK; TANNER-SMITH; KILLINGSWORTH, 2016) indicam
ganhos de aprendizagem e retenção superiores frente à instrução
convencional, sobretudo quando o jogo incorpora *feedback*, desafio
calibrado e reflexão.

A **IA** entra por três razões técnicas que nenhuma outra abordagem
satisfaz simultaneamente:

1.  **Emergência realista com custo computacional viável** ---
    algoritmos evolucionários e modelagem baseada em agentes geram
    comportamentos complexos e não roteirizados a partir de regras
    simples, algo impossível de \"pré-scriptar\".

2.  **Personalização e mediação** --- LLMs e modelos de conhecimento do
    estudante adaptam desafios, explicações e ritmo ao nível de cada
    aluno (LUCKIN et al., 2016).

3.  **Avaliação contínua e não intrusiva** --- modelos probabilísticos
    inferem competências a partir das ações no jogo (*stealth
    assessment*, SHUTE, 2011), gerando evidências ricas para o
    professor.

Crucialmente, adota-se o princípio da **IA explicável**: como o objetivo
é *ensinar causalidade*, privilegiam-se técnicas interpretáveis (regras,
evolução, agentes, redes bayesianas) no núcleo da simulação, usando
modelos \"caixa-preta\" apenas em papéis auxiliares e sempre com uma
camada de explicação.

## 3 Objetivos

### 2.1 Objetivo geral

Desenvolver e validar um jogo educacional multidisciplinar, baseado em
Inteligência Artificial e simulação científica, no qual cada aluno cria
um planeta e acompanha sua evolução em ambiente tridimensional,
ensinando conceitos de múltiplas disciplinas de forma **integrada,
investigativa e sistêmica**, por meio da experimentação, da observação,
da tomada de decisão e da análise das consequências das escolhas.

### 2.2 Objetivos específicos

4.  **Modelar** um sistema de simulação de planetas que acople, de modo
    cientificamente plausível (ainda que didaticamente simplificado),
    subsistemas físicos, químicos, geológicos, climáticos,
    oceanográficos, ecológicos e evolutivos.

5.  **Projetar** uma arquitetura de IA modular e explicável,
    selecionando, para cada fenômeno, a técnica mais adequada
    (algoritmos evolucionários, agentes, modelos probabilísticos,
    regras, aprendizado por reforço, IA generativa).

6.  **Implementar** mecânicas de intervenção do jogador centradas em
    *trade-offs*, com consequências dinâmicas de curto, médio e longo
    prazo.

7.  **Construir** um motor de visualização 3D interativo em tecnologias
    web abertas, permitindo alterar dinamicamente atmosfera, oceanos,
    vegetação, espécies, relevo, clima, cidades e desastres.

8.  **Alinhar** os conteúdos e mecânicas às competências da BNCC
    (Ciências da Natureza, Matemática, e pensamento computacional), com
    trilhas para Fundamental II, Médio e Técnico.

9.  **Desenvolver** um painel do professor e um sistema de avaliação
    embutida (*stealth assessment*) que gere evidências de aprendizagem
    sem interromper o jogo.

10. **Validar** o artefato com estudantes reais, medindo aprendizagem,
    engajamento, retenção, motivação e desenvolvimento do pensamento
    científico e interdisciplinar.

11. **Publicar** o software como projeto aberto, reutilizável e
    extensível, com documentação técnica e pedagógica.

## 4 Fundamentação Teórica

O projeto articula teorias da aprendizagem, do design de jogos e da
computação. O quadro abaixo relaciona cada teoria a uma decisão concreta
de projeto.

### 4.1 Construtivismo, construcionismo e micromundos

-   **Piaget** (epistemologia genética) fundamenta a ideia de que o
    conhecimento é *construído* pela ação do sujeito sobre o objeto, por
    assimilação e acomodação. No jogo, o desequilíbrio cognitivo é
    provocado por resultados inesperados da simulação.

-   **Vygotsky** (sociointeracionismo) sustenta a **zona de
    desenvolvimento proximal (ZDP)**: o tutor de IA e os
    \"conselheiros\" (agentes) funcionam como *scaffolding* que opera
    acima do que o aluno faria sozinho, com apoio calibrado e removível.

-   **Papert** (construcionismo; *Mindstorms*, 1980;
    *Constructionism*, 1991) é a base filosófica central: aprende-se
    melhor construindo artefatos públicos e significativos. O planeta é
    o artefato do aluno --- um **micromundo** manipulável onde ideias
    científicas se tornam objetos de pensamento.

-   **Dewey** e **Bruner** aportam o *learning by doing* e a
    **aprendizagem por descoberta**.

### 4.2 Aprendizagem experiencial e baseada em problemas

-   **Kolb** (*Experiential Learning*, 1984) --- o ciclo *experiência
    concreta → observação reflexiva → conceituação abstrata →
    experimentação ativa* é literalmente o *loop* de jogo de ECOSFERA.

-   **Barrows / PBL** --- cada era do planeta apresenta um problema
    aberto (uma extinção iminente, um colapso climático) que estrutura a
    investigação.

### 4.3 Aprendizagem baseada em jogos e motivação

-   **Malone** (1981, \"What makes things fun to learn\") --- desafio,
    curiosidade, controle e fantasia como fontes de motivação
    intrínseca.

-   **Csikszentmihalyi** (1990) --- teoria do **fluxo**: o balanceamento
    dinâmico dificuldade × habilidade (via IA Director) mantém o aluno
    na \"zona de fluxo\".

-   **Prensky** (2001), **Gee** (2003) e **Squire** (2011) ---
    princípios de aprendizagem em videogames (identidade, agência,
    exploração segura do erro, *just-in-time information*).

-   **Plass, Homer & Kinzer** (2015) --- fundamentos cognitivos,
    motivacionais e socioculturais do GBL.

-   **Keller (ARCS)** --- Atenção, Relevância, Confiança, Satisfação,
    usado no design motivacional e na avaliação.

### 4.4 Sistemas complexos e modelagem computacional

-   **Bertalanffy** (Teoria Geral dos Sistemas, 1968) e **Meadows**
    (*Thinking in Systems*, 2008) --- estoques, fluxos e
    retroalimentação, base do modelo de ciclos (carbono, nutrientes,
    população).

-   **Holland** (*Emergence*, 1998; *Adaptation in Natural and
    Artificial Systems*, 1975/1992) --- emergência e **algoritmos
    genéticos**.

-   **Mitchell** (*Complexity*, 2009) --- panorama de sistemas
    adaptativos complexos.

-   **Epstein & Axtell** (*Growing Artificial Societies*, 1996) e
    **Wilensky & Rand** (2015) --- **modelagem baseada em agentes
    (ABM)** como método para gerar fenômenos sociais e ecológicos
    emergentes.

-   **Reynolds** (1987, *Boids*) --- regras locais produzem
    comportamento coletivo (cardumes, revoadas, manadas).

### 4.5 Ciências naturais de referência

-   **Darwin** (*A Origem das Espécies*, 1859) --- seleção natural, o
    núcleo do módulo evolutivo.

-   **Lovelock** (hipótese Gaia, 1979) --- o planeta como sistema
    autorregulado acoplando biota e ambiente; inspiração conceitual
    direta do nome e da mecânica.

-   **Odum** --- fundamentos de ecologia de ecossistemas (fluxo de
    energia, cadeias tróficas).

-   **Lotka--Volterra** --- modelos predador-presa que ancoram a
    dinâmica populacional.

### 4.6 IA na Educação (AIED) e avaliação

-   **Russell & Norvig** (*AIMA*) --- agentes inteligentes como
    paradigma organizador.

-   **Sutton & Barto** (2018) --- aprendizado por reforço.

-   **Woolf** (2009) e **VanLehn** (2011) --- sistemas tutores
    inteligentes e sua eficácia; **Anderson/Koedinger** (Cognitive
    Tutors, ACT-R).

-   **Luckin et al.** (2016, *Intelligence Unleashed*) --- argumento
    para IA na educação.

-   **Shute** (2011) --- ***stealth assessment***: inferência de
    competências a partir de evidências comportamentais no jogo, via
    modelos probabilísticos --- ponte direta com **modelagem
    psicométrica** (TRI/IRT) e redes bayesianas.

-   **Bogost** (2007, *Persuasive Games*) --- **retórica procedural**: o
    argumento do jogo está nas *regras*, não no texto; é a simulação que
    \"ensina\".

### 4.7 Currículo brasileiro (BNCC) e frameworks de design

-   **BNCC** --- Competências Gerais (pensamento científico, crítico e
    criativo; cultura digital) e a área de **Ciências da Natureza**; o
    **Complemento de Computação da BNCC (2022)** (pensamento
    computacional, cultura e mundo digital) fundamenta a componente de
    modelagem e algoritmos.

-   **Taxonomia de Bloom revisada** (Anderson & Krathwohl, 2001) ---
    para desenho de objetivos e avaliação (de *lembrar* a *criar*).

-   **TPACK** (Mishra & Koehler, 2006) e **Design Universal para
    Aprendizagem (DUA/UDL)** --- para integração pedagógica-tecnológica
    e acessibilidade.

> ***Síntese:** ECOSFERA é um micromundo construcionista (Papert) que
> opera o ciclo experiencial de Kolb, movido por retórica procedural
> (Bogost) sobre um modelo de sistemas complexos (Holland/Meadows), com
> IA como mediadora (Luckin) e avaliadora invisível (Shute), alinhado à
> BNCC.*

## 5 Descrição Geral do Sistema

### 5.1 A jornada do aluno

12. **Gênese (criação do planeta).** O aluno parametriza um mundo. A IA
    sugere valores plausíveis e alerta para combinações inviáveis
    (p.ex., \"com essa massa e essa distância da estrela, a água ferve
    --- deseja continuar?\"), ensinando **causalidade já na criação**.

13. **Eras (simulação evolutiva).** O tempo avança em escalas ajustáveis
    (do geológico ao ecológico). Surgem oceanos, atmosfera se
    estabiliza, vida emerge, especia, se adapta ou se extingue.

14. **Intervenções.** O aluno realiza ações limitadas por \"pontos de
    intervenção\", cada uma com *trade-offs*.

15. **Eventos.** Fenômenos aleatórios (meteoros, pandemias, tempestades
    solares) testam a resiliência do sistema.

16. **Reflexão.** Ao fim de cada era, o tutor de IA gera um relatório
    explicativo das cadeias causais, propõe questões e registra
    evidências de aprendizagem.

### 5.2 Parâmetros de criação do planeta

Organizados por dimensão científica (cada um vira uma \"alavanca\" com
efeitos acoplados):

  -------------------------------------------------------------------------
  **Dimensão**              **Parâmetros**          **Disciplinas
                                                    mobilizadas**
  ------------------------- ----------------------- -----------------------
  **Astronômica**           massa, tamanho,         Astronomia, Física
                            distância da estrela,   
                            tipo/idade da estrela,  
                            nº de luas, duração do  
                            dia, inclinação axial   
                            (estações),             
                            excentricidade orbital  

  **Física**                gravidade (derivada de  Física, Matemática
                            massa/raio), campo      
                            magnético, radiação     
                            incidente, energia      
                            recebida                

  **Geológica**             relevo, vulcanismo,     Geografia, Geologia,
                            atividade tectônica,    Química
                            composição da crosta,   
                            recursos minerais       

  **Química/atmosférica**   composição da           Química, Física
                            atmosfera, concentração 
                            de O2/CO2, pressão,     
                            temperatura média       

  **Hidrológica**           água total, oceanos,    Oceanografia, Química
                            salinidade,             
                            distribuição            

  **Biológica/edáfica**     fertilidade do solo,    Biologia, Ecologia
                            disponibilidade de      
                            nutrientes, presença de 
                            vida inicial            
  -------------------------------------------------------------------------

**Variáveis adicionais sugeridas pela IA** (ampliando a proposta
original): albedo planetário, atividade da estrela (ciclos solares),
densidade da camada de ozônio, viscosidade/energia do manto, taxa de
rotação diferencial (jatos atmosféricos), disponibilidade de fósforo e
nitrogênio fixável (limitantes reais da biosfera), pH oceânico, presença
de gases-estufa secundários (CH4), e \"semente de vida\" (química
prebiótica inicial).

Todas as escolhas **realimentam continuamente** a simulação: não são
cosméticas. A gravidade afeta o tamanho máximo dos organismos; a
inclinação axial cria estações que dirigem migrações; o campo magnético
protege (ou não) a atmosfera do vento estelar.

# PARTE II — Modelagem Pedagógica


## 6 Modelo Pedagógico, Avaliação e Stealth Assessment

### 1. Modelo Pedagógico Geral

### 1.1 Filosofia pedagógica

ECOSFERA adota uma filosofia **construcionista e investigativa**:
aprende-se **construindo um artefato significativo** (o planeta) e
**investigando** as consequências das próprias decisões. O conteúdo
científico não é \"transmitido\"; ele está **codificado nas regras da
simulação** --- o que Bogost (2007) chama de *retórica procedural*. O
aluno não lê sobre efeito estufa: ele o provoca, observa e é levado a
explicá-lo. Essa filosofia responde diretamente ao problema declarado na
proposta (§3.1): a fragmentação disciplinar e o conhecimento inerte.

### 1.2 Teorias de aprendizagem e justificativa

  ------------------------------------------------------------------------
  **Abordagem**           **Como ECOSFERA a        **Por que foi escolhida
                          incorpora**              (justificativa)**
  ----------------------- ------------------------ -----------------------
  **Construtivismo**      Resultados inesperados   Conhecimento científico
  (Piaget)                da simulação geram       é reconstruído pela
                          desequilíbrio cognitivo  ação, não decorado
                          → assimilação/acomodação 

  **Construcionismo**     O planeta é um           Aprendizagem profunda
  (Papert)                **micromundo** e um      emerge de construir
                          artefato público que o   algo pessoalmente
                          aluno cria e compartilha significativo

  **Aprendizagem          *Loop*: experiência      O ciclo de Kolb É o
  Experiencial** (Kolb)   (agir no planeta) →      *core loop* do jogo
                          observação (ver efeitos) (RF-011→014→017→033)
                          → conceituação (tutor    
                          explica) →               
                          experimentação (nova     
                          ação)                    

  **Inquiry-Based         Aluno formula hipóteses  Desenvolve raciocínio
  Learning (IBL)**        (\"se eu aumentar o      científico
                          CO2...\"), testa e       (CG2/EM13CNT301)
                          revisa                   

  **Problem-Based         Cada era propõe um       Contextualiza o
  Learning (PBL)**        problema aberto (colapso conteúdo e mobiliza
                          climático, extinção      resolução de problemas
                          iminente)                

  **Game-Based Learning   Mecânicas, metas,        Meta-análises (Wouters
  (GBL)**                 progressão e *feedback*  2013; Clark 2016)
                          como veículos de         mostram ganho de
                          aprendizagem             aprendizagem/retenção

  **Serious Games**       Propósito primário é     Adequado a conteúdos
                          aprender; entretenimento sistêmicos e de tomada
                          a serviço da educação    de decisão

  **Aprendizagem          IA ajusta desafio, dicas Mantém o aluno na ZDP
  Adaptativa**            e trilha ao desempenho   (Vygotsky) e na zona de
                          (RF-020/035)             fluxo
                                                   (Csikszentmihalyi)

  **AIED**                Tutor (LLM+RAG),         Personalização e
                          avaliação embutida e     avaliação contínua
                          progressão adaptativa    inviáveis por meios
                                                   tradicionais
  ------------------------------------------------------------------------

### 1.3 Papéis no processo

-   **Papel do aluno --- protagonista, autor e cientista.** Exerce
    **agência** (decide), **autoria** (seu mundo é único) e
    **investigação** (hipótese→teste→revisão). Alinha-se à Teoria da
    Autodeterminação (Deci & Ryan): autonomia, competência e
    pertencimento --- os três nutrientes da motivação intrínseca.

-   **Papel da IA --- mediadora, avaliadora invisível e
    adaptadora.** (i) *Mediação:* o tutor generativo explica a
    causalidade (RF-033/039) como *scaffolding* (Wood, Bruner & Ross,
    1976), removível conforme o aluno avança; (ii) *avaliação
    invisível:* o *stealth assessment* infere competências das ações
    (RF-072); (iii) *adaptação:* ajusta a experiência (RF-020/035). **A
    IA nunca decide a ciência do mundo** (isso é da simulação,
    explicável) nem substitui o professor (RP-007).

-   **Papel do professor --- designer, mediador e autoridade
    pedagógica.** Ancora atividades à BNCC (RF-062), define a trilha
    (RF-061), interpreta evidências (RF-063/064) e intervém. A IA
    **amplia** o professor; a decisão pedagógica final é dele.

-   **Papel do jogo --- ambiente de aprendizagem experiencial e espaço
    seguro para o erro.** O jogo é o micromundo onde ideias abstratas
    viram objetos manipuláveis; o erro é **reversível e analisável**
    (RP-010), condição para a experimentação científica sem medo de
    punição.

> ***Coerência com requisitos:** este modelo materializa RP-003
> (feedback formativo), RP-007 (mediação docente), RP-009
> (interdisciplinaridade), RP-010 (erro seguro) e sustenta os módulos de
> IA (RF-031--040) e de avaliação (RF-071--078).*

### 2. Objetivos de Aprendizagem (por módulo)

Para cada módulo: **conhecimento esperado**, **habilidade
desenvolvida**, **competência envolvida**, **aplicação prática**,
**nível de Bloom revisado** e **contribuição da mecânica**. (Aprofunda o
ERS §6, sem repeti-lo.)

M1 --- Criação do Planeta

-   **Conhecimento:** variáveis planetárias; noção de zona habitável;
    interdependência de parâmetros.

-   **Habilidade:** configurar um conjunto coerente de condições; prever
    viabilidade.

-   **Competência:** pensamento científico e modelagem (CG2, CG5).

-   **Aplicação prática:** justificar por que um planeta é (in)viável
    para a vida.

-   **Bloom:** **Criar** (e Avaliar, ao ponderar combinações).

-   **Contribuição da mecânica:** a validação da IA (RF-012) transforma
    cada escolha em uma microlição de causalidade já na gênese.

M2 --- Física e Astronomia

-   **Conhecimento:** gravidade, órbitas, energia estelar, radiação,
    marés.

-   **Habilidade:** relacionar massa/distância a gravidade, temperatura
    e energia recebida.

-   **Competência:** CG2.

-   **Aplicação prática:** explicar por que a distância à estrela define
    a faixa de temperatura.

-   **Bloom:** **Compreender/Aplicar**.

-   **Contribuição da mecânica:** parâmetros astronômicos (RF-011)
    alimentam determinísticamente o resto --- o aluno vê relações
    físicas exatas.

M3 --- Química Atmosférica e Ciclos

-   **Conhecimento:** composição da atmosfera, efeito estufa, ciclos do
    carbono/oxigênio/nitrogênio.

-   **Habilidade:** relacionar composição, energia e temperatura;
    interpretar ciclos como estoques e fluxos.

-   **Competência:** CG2, CG10.

-   **Aplicação prática:** prever o efeito de elevar CO2 ou desmatar.

-   **Bloom:** **Analisar**.

-   **Contribuição da mecânica:** a simulação de ciclos (RF-014) torna
    visível o invisível (fluxo de matéria).

M4 --- Clima

-   **Conhecimento:** zonas climáticas, feedbacks gelo-albedo e estufa,
    eras glaciais, desertificação.

-   **Habilidade:** identificar retroalimentações e pontos de inflexão.

-   **Competência:** CG2, CG10.

-   **Aplicação prática:** explicar uma transição climática abrupta
    observada no planeta.

-   **Bloom:** **Analisar/Avaliar**.

-   **Contribuição da mecânica:** autômatos climáticos + eventos
    (RF-014/019) evidenciam não-linearidade e atraso (*lag*).

M5 --- Geologia e Oceanografia

-   **Conhecimento:** tectônica, vulcanismo, erosão; correntes, marés,
    salinidade.

-   **Habilidade:** relacionar processos internos/externos ao relevo e
    ao clima.

-   **Competência:** CG2.

-   **Aplicação prática:** interpretar a formação de uma cadeia de
    montanhas ou de uma corrente.

-   **Bloom:** **Compreender/Aplicar**.

-   **Contribuição da mecânica:** relevo procedural + acoplamento
    oceano-clima (RF-014) conectam Geografia e Física.

M6 --- Ecologia e Cadeias Tróficas

-   **Conhecimento:** fluxo de energia, capacidade de suporte,
    predador-presa, biodiversidade, espécies invasoras.

-   **Habilidade:** analisar equilíbrio; prever efeitos em cascata.

-   **Competência:** CG2, CG10.

-   **Aplicação prática:** antecipar o impacto de remover/introduzir uma
    espécie.

-   **Bloom:** **Analisar**.

-   **Contribuição da mecânica:** ABM ecológico (RF-032) gera oscilações
    emergentes que o aluno observa e explica.

M7 --- Evolução Biológica

-   **Conhecimento:** variação, seleção natural, adaptação, especiação,
    extinção.

-   **Habilidade:** relacionar pressão ambiental e aptidão; interpretar
    mudanças no genoma.

-   **Competência:** CG2.

-   **Aplicação prática:** explicar por que certas características se
    tornaram comuns.

-   **Bloom:** **Compreender/Analisar**.

-   **Contribuição da mecânica:** o motor evolutivo (RF-031) exibe
    seleção natural \"acontecendo\", com genoma inspecionável.

M8 --- Intervenções e Trade-offs (Sustentabilidade)

-   **Conhecimento:** custo-benefício socioambiental, sustentabilidade,
    ODS/Agenda 2030.

-   **Habilidade:** decidir sob restrição; argumentar com dados;
    analisar consequências.

-   **Competência:** CG7, CG10.

-   **Aplicação prática:** justificar uma política ambiental ponderando
    ganhos e perdas.

-   **Bloom:** **Avaliar/Criar**.

-   **Contribuição da mecânica:** *trade-offs* materializados
    (RF-017/018) tornam impossível \"vencer sem escolher\" --- núcleo do
    pensamento crítico.

M9 --- Dados e Estatística

-   **Conhecimento:** gráficos, proporção, probabilidade, correlação vs.
    causa.

-   **Habilidade:** ler séries temporais e fundamentar decisões em
    evidência.

-   **Competência:** CG2, CG5.

-   **Aplicação prática:** usar os indicadores do planeta para decidir a
    próxima ação.

-   **Bloom:** **Aplicar/Analisar**.

-   **Contribuição da mecânica:** painéis e séries (RF-021) transformam
    o jogo em fonte de dados reais para análise.

M10 --- Tutoria e Reflexão (Metacognição)

-   **Conhecimento:** conexão entre experiência e conceito; vocabulário
    científico.

-   **Habilidade:** metacognição; verbalizar o aprendido; formular
    hipóteses.

-   **Competência:** CG2, CG4, CG7.

-   **Aplicação prática:** responder \"por que isso aconteceu?\" com
    base em evidências.

-   **Bloom:** **Compreender/Avaliar**.

-   **Contribuição da mecânica:** o tutor LLM+RAG (RF-033/034/039) fecha
    o ciclo de Kolb, convertendo experiência em conceito explícito.

### 3. Alinhamento com a BNCC

### 3.1 Competências Gerais mobilizadas

**CG2** (pensamento científico, crítico e criativo), **CG5** (cultura
digital), **CG7** (argumentação com base em dados), **CG10**
(responsabilidade e cidadania socioambiental) como núcleo; **CG1**
(conhecimento), **CG4** (comunicação) e **CG9** (empatia/cooperação, no
modo colaborativo futuro) como apoio.

### 3.2 Competências específicas

-   **Ciências da Natureza (EF):** 8 competências específicas da área,
    com ênfase em análise, investigação e intervenção responsável.

-   **Ciências da Natureza e suas Tecnologias (EM):** **Competência 1**
    (matéria, energia, transformações), **Competência 2** (Vida, Terra e
    Universo; evolução), **Competência 3** (investigação e prática
    científica).

-   **Matemática:** letramento estatístico, proporcionalidade e funções.

-   **Computação (Complemento 2022):** eixos **Pensamento
    Computacional**, **Mundo Digital** e **Cultura Digital**.

### 3.3 Unidades temáticas e objetos de conhecimento (Ciências EF)

-   **Matéria e energia:** composição do ar; transformações; ciclos.

-   **Vida e evolução:** ecossistemas; cadeias alimentares;
    biodiversidade; hereditariedade; ideias evolucionistas;
    sustentabilidade.

-   **Terra e Universo:** estrutura da Terra; movimentos; clima; Sistema
    Solar; condições para a vida.

### 3.4 Matriz de alinhamento (Mecânica ↔ BNCC)

> *Códigos conforme BNCC 2018; itens com (conferir) pedem validação do
> número exato (o objeto de conhecimento está correto).*

  ----------------------------------------------------------------------------------------------------
  **Mecânica do Jogo**       **Disciplina**       **Competência   **Habilidade     **Objetivo de
                                                  BNCC**          BNCC (código)**  Aprendizagem**
  -------------------------- -------------------- --------------- ---------------- -------------------
  Criar planeta / zona       Ciências             CG2; EM Comp. 2 EF09CI16;        Avaliar condições
  habitável                  (Astronomia)                         EF09CI14;        de habitabilidade
                                                                  EM13CNT201/202   planetária

  Estrutura da Terra e       Ciências             CG2             EF06CI11         Compreender a
  camadas                                                                          estrutura interna e
                                                                                   a atmosfera

  Órbita, estações,          Ciências             CG2             EF06CI14;        Relacionar
  dia/noite                                                       EF09CI17         movimentos e
                                                                                   energia estelar

  Atmosfera e efeito estufa  Ciências             CG2, CG10       EF07CI13;        Explicar o efeito
                             (Química/Física)                     EF07CI12         estufa e sua
                                                                  *(conferir)*     alteração antrópica

  Camada de ozônio /         Ciências             CG2             EF07CI14         Relacionar proteção
  radiação                                                        *(conferir)*     atmosférica e vida

  Clima e circulação         Ciências/Geografia   CG2             EF08CI14         Relacionar clima à
  oceano-atmosfera                                                                 circulação e ao
                                                                                   aquecimento
                                                                                   desigual

  Eventos climáticos /       Ciências             CG2             EF08CI15         Identificar
  previsão                                                                         variáveis do clima
                                                                                   e prever tendências

  Alterações climáticas e    Ciências             CG10            EF08CI16         Discutir
  equilíbrio                                                                       intervenções para o
                                                                                   equilíbrio
                                                                                   ambiental

  Ciclos do                  Ciências (Química)   CG2             EM13CNT101;      Modelar ciclos como
  carbono/água/nitrogênio                                         EM13CNT203       estoques e fluxos

  Ecossistemas e cadeias     Ciências (Ecologia)  CG2             EF07CI07;        Analisar fluxo de
  tróficas                                                        EF07CI08         energia e impactos

  Biodiversidade e espécies  Ciências             CG10            EF09CI12         Avaliar
  invasoras                                                       *(conferir)*;    biodiversidade e
                                                                  EM13CNT206       conservação

  Evolução e seleção natural Ciências (Biologia)  CG2             EF09CI11;        Compreender seleção
                                                                  EF09CI09         natural e adaptação
                                                                  *(conferir)*     

  Geologia: relevo, vulcões, Geografia/Ciências   CG2             Dinâmica da      Entender processos
  erosão                                                          natureza (Geo    que moldam o relevo
                                                                  EF) *(conferir   
                                                                  código)*         

  Séries temporais e         Matemática           CG2, CG5        EF07MA17;        Ler dados e
  gráficos                                                        estatística      proporcionalidade
                                                                  EF07MA35--37     para decidir
                                                                  *(conferir)*     

  Probabilidade de eventos   Matemática           CG2             Probabilidade    Estimar risco e
                                                                  EF08MA           incerteza
                                                                  *(conferir)*     

  Trade-offs e decisão       Sustentabilidade     CG7, CG10       EM13CNT203;      Argumentar e
  socioambiental                                                  EM13CNT206;      decidir sob
                                                                  EM13CNT306       trade-offs

  Investigar                 Transversal          CG2, CG7        EM13CNT301;      Praticar o método
  (hipótese→teste→revisão)                                        EM13CNT302       científico

  Modelar parâmetros         Computação           CG5             Pensamento       Abstrair e modelar
  (abstração)                                                     Computacional    sistemas
                                                                  (Compl. 2022)    
  ----------------------------------------------------------------------------------------------------

### 3.5 Como cada funcionalidade desenvolve a competência

A lógica é a **retórica procedural** (Bogost, 2007): a competência não é
\"informada\", é **exercitada na regra**. Exemplos:

-   **EF07CI13 (efeito estufa)** --- o aluno eleva CO2 e *observa* a
    temperatura subir; o tutor formaliza o conceito (Kolb). Desenvolve
    CG2 (explicar com base em evidência).

-   **EF09CI11 (seleção natural)** --- sob pressão ambiental, o motor
    evolutivo (RF-031) faz variantes prevalecerem; o aluno *vê* a
    seleção operar sobre o genoma.

-   **EM13CNT301 (investigação)** --- todo *core loop* é
    hipótese→experimento→observação→revisão; o *stealth assessment* (§7)
    mede exatamente essa prática.

-   **EM13CNT203 (efeitos de intervenções)** --- os *trade-offs*
    (RF-018) são a encarnação lúdica da habilidade de prever efeitos de
    intervenções em ecossistemas.

### 4. Trilhas de Aprendizagem

Três trilhas coerentes com as trilhas do ERS (RF-061/RP-002):
**Fundamental II**, **Médio** e **Técnico**. Dentro de cada uma, a
**evolução do jogador** avança por quatro níveis de domínio (não por
tempo, mas por competência demonstrada --- progressão baseada em
competências):

**Níveis de domínio (evolução do jogador):**

17. **Aprendiz** (Lembrar/Compreender) --- parâmetros guiados, muitas
    dicas, escopo reduzido.

18. **Explorador** (Aplicar) --- mais variáveis, dicas sob demanda,
    primeiros *trade-offs*.

19. **Investigador** (Analisar) --- subsistemas acoplados completos,
    eventos, hipóteses.

20. **Guardião** (Avaliar/Criar) --- problemas abertos, otimização
    multiobjetivo, autoria de cenários.

### 4.1 Trilha Fundamental II (6º--9º)

  ---------------------------------------------------------------------------------------------------------
  **Ano**     **Conhecimentos   **Conteúdos        **Missões/Desafios**   **Objetivo**       **Critério de
              prévios**         desbloqueados**                                              progressão**
  ----------- ----------------- ------------------ ---------------------- ------------------ --------------
  **6º**      Noções de Terra e Criar planeta;     \"Um mundo             Compreender        Domínio ≥
              Sol               estrutura;         habitável\":           condições          limiar em
                                órbita/estações    posicionar o planeta   planetárias        M1/M2 + missão
                                                   na zona certa          (EF06CI11/14)      concluída

  **7º**      Planeta criado    Atmosfera, efeito  \"O ar que aquece\";   Explicar efeito    Evidências de
                                estufa;            \"Teia da vida\"       estufa e teias     causa-efeito
                                ecossistemas e                            (EF07CI07/08/13)   em M3/M6
                                cadeias                                                      

  **8º**      Atmosfera e vida  Clima, oceanos,    \"Tempo instável\":    Relacionar clima e Análise
                                eventos climáticos enfrentar              circulação         correta de
                                                   seca/enchente          (EF08CI14/15/16)   feedbacks em
                                                                                             M4/M5

  **9º**      Ecossistemas e    Evolução,          \"A vida se            Compreender        Trade-offs
              clima             biodiversidade,    transforma\";          evolução e decidir justificados
                                Sistema Solar,     \"Decisões do futuro\" (EF09CI11/14/16)   em M7/M8
                                sustentabilidade                                             
  ---------------------------------------------------------------------------------------------------------

### 4.2 Trilha Ensino Médio

Integra as disciplinas: ciclos biogeoquímicos, modelos científicos,
investigação formal (EM13CNT301), *trade-offs* multiobjetivo e
estatística/probabilidade. Missões de **projeto** (várias eras) e
**otimização** (equilibrar desenvolvimento e sustentabilidade ---
EM13CNT203/206/306). Progressão exige **argumentação com dados** (CG7) e
domínio no nível *Investigador/Guardião*.

### 4.3 Trilha Técnica

Ênfase em **modelagem quantitativa, dados e projeto aplicado** (ex.:
cenários de meio ambiente, agro, energia). Uso intensivo de séries
temporais (RF-021), exportação de dados (RF-066) e formulação/validação
de hipóteses. Entregável típico: um \"relatório de missão\" defendendo
decisões com evidência --- avaliado por rubrica (RP-005).

### 4.4 Adaptação automática da trilha pela IA

O **modelo do aluno** (RF-072/073; BKT + IRT) estima o domínio por
competência. A IA então:

-   **Desbloqueia** o próximo conteúdo quando o domínio ultrapassa o
    limiar (progressão por competência, não por tempo).

-   **Remedia:** se o aluno emperra, injeta missões de reforço, aumenta
    o *scaffolding* (dicas/conselheiros) e reduz a carga (Teoria da
    Carga Cognitiva, Sweller).

-   **Acelera:** se demonstra domínio, salta pré-requisitos e oferece
    desafios de nível superior (mantendo o fluxo).

-   **Rebalanceia** eventos e dificuldade via **Diretor** (RF-020),
    sempre subordinado ao **objetivo pedagógico** da missão (a adaptação
    nunca dilui a competência-alvo).

> ***Justificativa:** progressão por domínio (mastery learning, Bloom)
> evita lacunas cumulativas; a adaptação mantém a ZDP (Vygotsky) e o
> fluxo (Csikszentmihalyi), sustentada tecnicamente por RF-035/073.*

### 5. Matriz de Competências

Esta matriz é o **contrato entre pedagogia e engenharia**: liga cada
competência a uma mecânica, a uma atividade, às evidências e à forma de
avaliação. (Colunas conforme solicitado.)

  --------------------------------------------------------------------------------------------------------------------------------------
  **Competência**   **Habilidade**       **Conhecimento     **Mecânica do     **Atividade   **Evidências coletadas**     **Forma de
                                         relacionado**      jogo**            prática**                                  avaliação**
  ----------------- -------------------- ------------------ ----------------- ------------- ---------------------------- ---------------
  Pensamento        Formular/testar      Método científico  *Core loop*       Prever antes  Nº de hipóteses testadas;    Stealth
  científico (CG2)  hipóteses                               investigar        de agir e     acerto de previsão           (bayesiano) +
                                                                              verificar                                  rubrica

  Causa-efeito      Relacionar variáveis Efeito estufa,     Ajustar           Provocar e    Sequência                    Stealth + tutor
  (CG2)                                  ciclos             CO2/atmosfera     explicar      ação→observação→explicação   (RF-039)
                                                                              aquecimento                                

  Pensamento        Analisar feedbacks   Clima/ecologia     Intervir e        Antecipar     Previsão de efeitos          Rubrica de
  sistêmico                              acoplados          observar cascata  efeitos em    secundários                  sistemas
                                                                              cadeia                                     

  Tomada de decisão Decidir sob          Sustentabilidade   Trade-offs        Justificar    Escolhas + justificativas    Rubrica de
  (CG7)             restrição                               (RF-018)          uma política                               argumentação

  Análise de        Avaliar resultados   Impactos           Eventos e         Analisar o    Revisão de estratégia        Stealth +
  consequências                          ambientais         intervenções      pós-decisão                                dashboard

  Letramento de     Ler                  Estatística        Painéis/séries    Decidir com   Uso de dados antes de agir   Análise de logs
  dados (CG5)       gráficos/proporção                      (RF-021)          base em dados                              

  Evolução          Explicar adaptação   Seleção natural    Motor evolutivo   Interpretar   Explicações corretas         Stealth + tutor
  (Biologia)                                                (RF-031)          mudanças do                                
                                                                              genoma                                     

  Persistência      Perseverar após      Metacognição       Erro seguro       Retomar após  Nº de tentativas/recuperação Learning
                    falha                                   (RP-010)          colapso                                    analytics

  Criatividade      Gerar soluções       Modelagem          Autoria de        Criar mundo   Diversidade/originalidade de Rubrica +
                    originais                               planeta/cenário   viável        soluções                     análise
                                                                              não-óbvio                                  

  Argumentação      Justificar com       Comunicação        Relatórios de     Defender      Qualidade da justificativa   Rubrica
  (CG7)             evidência            científica         missão            decisões                                   (EM13CNT302)
  --------------------------------------------------------------------------------------------------------------------------------------

### 5.1 Como a matriz é usada no desenvolvimento

-   **Design de tarefas (task model):** cada mecânica é projetada para
    eliciar as evidências da linha correspondente --- garante que o jogo
    *gere* dado avaliável.

-   **Modelo de evidências (evidence model):** as colunas \"evidências\"
    e \"método\" alimentam diretamente o *stealth assessment* (§7/§8) e
    o modelo do aluno (RF-072).

-   **Dashboard (RF-063/064):** a coluna \"competência\" define os eixos
    do painel do professor.

-   **Rastreabilidade:** conecta-se à matriz
    Requisito→Competência→Evidência→Teste recomendada no ERS (§16.2),
    fechando o elo pedagogia↔código.

### 6. Modelo de Avaliação

Sistema **contínuo, baseado em competências e centrado em evidências**,
articulando quatro funções avaliativas e a autorregulação. Coerente com
RF-071--078 e RP-004.

  -----------------------------------------------------------------------
  **Tipo**                **Quando/Como**         **Papel da IA**
  ----------------------- ----------------------- -----------------------
  **Diagnóstica**         No início (escolhas na  Infere ponto de partida
                          criação do planeta +    e define
                          pré-teste opcional      trilha/dificuldade
                          RF-074) para estimar    inicial
                          conhecimento prévio     

  **Formativa**           Contínua, durante o     *Stealth assessment*
                          jogo (núcleo do modelo) (RF-072) atualiza o
                                                  domínio; tutor dá
                                                  feedback (Etapa 10)

  **Somativa**            Ao fim de               Agrega estimativas por
                          unidades/missões:       competência; gera
                          \"relatório de missão\" relatório (RF-064/066)
                          e certificação de       
                          competência a partir de 
                          evidências acumuladas   

  **Feedback contínuo**   A cada ação/era         Tutor LLM+RAG gera
                                                  feedback contextual e
                                                  explicativo
                                                  (RF-033/039)

  **Autorregulação**      Aluno acompanha metas e Painel do aluno +
                          progresso; *prompts*    perguntas
                          reflexivos              metacognitivas (\"o que
                                                  você mudaria?\")

  **Baseada em            Progresso por domínio   Modelo do aluno
  competências**          demonstrado, não por    (RF-073) estima domínio
                          pontos/tempo            por competência
  -----------------------------------------------------------------------

**Justificativa científica.** A ênfase na **avaliação formativa**
apoia-se em Black & Wiliam (1998): *feedback* durante a aprendizagem
produz ganhos substanciais. A **autorregulação** segue Zimmerman
(planejar→monitorar→refletir), o que o jogo torna natural (metas de
missão, indicadores, reflexão pós-era). A **avaliação por competências**
substitui a lógica de \"nota por prova\" por **domínio demonstrado**,
coerente com a BNCC (competências e habilidades) e com *mastery
learning* (Bloom).

**Como a IA apoia cada tipo (resumo):** diagnóstica → inferência
inicial; formativa → atualização bayesiana + *feedback* inteligente;
somativa → agregação de evidências e mapeamento à BNCC (RF-076);
autorregulação → visualização e provocações metacognitivas. A IA
**informa**, o professor **decide** (RP-007).

### 7. Stealth Assessment

### 7.1 Fundamento: Evidence-Centered Design (ECD)

A estratégia segue o **Evidence-Centered Design** (Mislevy, Steinberg &
Almond, 2003) operacionalizado como *stealth assessment* por Shute
(2011) e Shute & Ventura (2013). Três modelos articulados:

-   **Modelo de Competência** (*o que* medir): as competências da matriz
    (§5) --- ex.: pensamento científico, sistêmico, tomada de decisão.

-   **Modelo de Evidências** (*como* inferir): regras que ligam ações
    observáveis a atualizações do domínio, via **rede bayesiana**
    (pgmpy) e **TRI/IRT** para calibrar dificuldade das \"tarefas\"
    (RF-072).

-   **Modelo de Tarefas** (*onde* eliciar): as mecânicas e missões são
    projetadas para provocar as ações-evidência (§5.1).

> ***Por que ECD/stealth (justificativa):** avalia **sem interromper** o
> jogo (RP-004), preserva o fluxo e mede competências complexas
> (sistêmico, decisão) que provas tradicionais capturam mal ---
> exatamente o argumento de Shute & Ventura (2013) em jogos como Physics
> Playground.*

### 7.2 Comportamentos monitorados e evidências

-   **Sequências de ação** (o que faz, em que ordem) → planejamento,
    estratégia.

-   **Previsões vs. resultados** (declara hipótese antes de agir?) →
    raciocínio científico, formulação de hipóteses.

-   **Uso de dados** (consulta gráficos antes de decidir?) → letramento
    de dados.

-   *Reação a* trade-offs (pondera prós/contras? revê após
    consequência?) → tomada de decisão, análise de consequências.

-   **Resposta a eventos** (recupera-se de um colapso?) → persistência,
    resolução de problemas.

-   **Exploração** (varia parâmetros para descobrir efeitos?) →
    experimentação, curiosidade.

-   **Originalidade** (soluções não-óbvias, mundos incomuns viáveis) →
    criatividade.

-   **Encadeamento causal** (conecta intervenção a efeito distante?) →
    pensamento sistêmico, causa-efeito.

-   *(Futuro)* **Interações no modo colaborativo** → colaboração.

### 7.3 Métricas inferíveis e competências estimadas

A partir dessas evidências, infere-se automaticamente: índice de
raciocínio científico, índice de pensamento sistêmico, qualidade de
decisão sob *trade-off*, persistência, grau de experimentação,
originalidade, e domínio conceitual por tópico (efeito estufa, seleção
natural, cadeias tróficas...). Cada evidência **atualiza a
probabilidade** de domínio no modelo bayesiano; ao longo do tempo, as
estimativas convergem --- dispensando provas frequentes.

### 7.4 Estimar progresso sem provas tradicionais

O domínio é acumulado por **atualização contínua** (cada ação é um
\"item\" de baixa aposta). Isso gera uma medida **longitudinal e
robusta** (muitos pontos de evidência) em vez de um retrato pontual (uma
prova). Recomenda-se **validar** as inferências contra medidas externas
ocasionais (pré/pós-teste RF-074; ganho de Hake) para calibrar o modelo
--- abordagem de validação padrão em *stealth assessment*. As
estimativas alimentam a progressão adaptativa (§9) e o painel do
professor (§11), com dados **anonimizados** para pesquisa
(RF-078/RNF-011).

### 8. Matriz de Evidências de Aprendizagem

Catálogo de evidências observáveis (base para o *evidence model* e para
os *dashboards*). **Métodos de inferência:** BN = rede bayesiana; IRT =
teoria de resposta ao item; SEQ = análise de sequência/*process mining*;
REG = regra/heurística; ML = classificador; LLM = avaliador por rubrica;
LA = *learning analytics* agregado.

  ---------------------------------------------------------------------------------------------
  **Competência**    **Evidência           **Evento do jogo**   **Indicador**    **Método**
                     observável**                                                
  ------------------ --------------------- -------------------- ---------------- --------------
  Raciocínio         Declara hipótese      Painel de previsão   Taxa de          BN, SEQ
  científico         antes de agir         preenchido           hipóteses/ação   

  Raciocínio         Previsão coincide com Comparar             Acurácia de      IRT, BN
  científico         resultado             previsto×obtido      previsão         

  Causa-efeito       Conecta intervenção a Explicação no tutor  Precisão causal  LLM, BN
                     efeito correto                                              

  Pensamento         Antecipa efeito       Ação seguida de      Índice de        SEQ, BN
  sistêmico          secundário/cascata    mitigação prévia     antecipação      

  Pensamento         Reconhece feedback    Explicação/escolha   Reconhecimento   LLM, REG
  sistêmico          (gelo-albedo)         coerente             de feedback      

  Tomada de decisão  Pondera prós/contras  Tempo/consulta antes Qualidade de     SEQ, BN
                     do trade-off          de decidir           decisão          

  Análise de         Revê estratégia após  Mudança de plano     Taxa de revisão  SEQ
  consequências      efeito negativo       pós-evento           adaptativa       

  Planejamento       Sequência coerente    Ordem das ações na   Coerência de     SEQ, ML
                     rumo à meta           missão               plano            

  Letramento de      Consulta gráficos     Abertura de          Uso de evidência LA, REG
  dados              antes de agir         painel/série                          

  Letramento de      Interpreta            Decisão coerente com Acerto           IRT
  dados              proporção/tendência   o gráfico            interpretativo   

  Resolução de       Recupera planeta de   Retomada após crise  Taxa de          SEQ, BN
  problemas          um colapso                                 recuperação      

  Persistência       Retenta após falha    Nº de tentativas em  Índice de        LA
                     sem desistir          desafio difícil      persistência     

  Experimentação     Varia parâmetros para Alterações           Amplitude de     SEQ, LA
                     testar efeito         exploratórias        exploração       

  Criatividade       Cria mundo viável     Configuração incomum Originalidade    ML, LLM
                     não-óbvio             bem-sucedida         viável           

  Efeito estufa      Relaciona CO2↑ a      Ação + explicação    Domínio do       BN, LLM
  (conceito)         temperatura↑                               conceito         

  Seleção natural    Explica prevalência   Interpretação do     Domínio do       BN, LLM
  (conceito)         de traço              genoma               conceito         

  Cadeias tróficas   Prevê efeito de       Ação ecológica +     Domínio do       BN, IRT
  (conceito)         remover espécie       previsão             conceito         

  Ciclos             Explica fluxo de      Missão de ciclo do   Domínio do       LLM, BN
  biogeoquímicos     matéria               carbono              conceito         

  Habitabilidade     Justifica zona        Criação bem          Domínio do       BN
                     habitável             posicionada          conceito         

  Sustentabilidade   Escolhe política de   Decisão              Orientação       BN, LLM
  (CG10)             longo prazo           socioambiental       sustentável      

  Argumentação (CG7) Justifica decisão com Relatório de missão  Qualidade        LLM (rubrica)
                     dados                                      argumentativa    

  Metacognição       Responde reflexão     *Prompt* reflexivo   Profundidade     LLM
                     pós-era               respondido           reflexiva        

  Autorregulação     Define e persegue     Metas de missão      Autorregulação   LA, SEQ
                     metas                 cumpridas                             

  Colaboração        Divide tarefas na     Ação conjunta        Contribuição     SEQ, LA
  *(futuro)*         galáxia               multiplayer          colaborativa     
  ---------------------------------------------------------------------------------------------

*(Lista extensível --- cada nova mecânica registra suas evidências pelo
mesmo padrão.)*

### 8.1 Como as evidências alimentam IA e dashboards

-   **IA (modelo do aluno):** cada evidência é um \"item\" que
    **atualiza a rede bayesiana** (RF-072) e recalibra a estimativa por
    competência (IRT), guiando a progressão adaptativa (§9).

-   **Dashboards (professor):** evidências agregadas viram os
    indicadores do painel (§11) --- progresso por competência,
    dificuldades e evolução temporal (RF-063/064).

-   **Rastreabilidade BNCC:** cada evidência mapeia-se à habilidade
    correspondente (RF-076), permitindo relatórios por competência da
    BNCC.

### 9. Progressão Adaptativa (baseada em IA)

O motor adaptativo mantém o aluno na **ZDP** (Vygotsky) e na **zona de
fluxo** (Csikszentmihalyi), sempre subordinado ao **objetivo
pedagógico** da missão. Ciclo: *estimar domínio → decidir ajuste →
aplicar → reavaliar*.

-   **Desafios ajustados:** dificuldade da missão calibrada ao domínio
    estimado (IRT); abaixo do limiar → reforço; acima → desafio
    superior. *(RF-035/073)*

-   **Eventos adaptados:** o **Diretor** (RF-020) modula
    frequência/severidade --- reduz pressão para quem emperra; aumenta
    para quem domina (sem nunca \"trapacear\" a ciência: eventos
    permanecem plausíveis).

-   **Dicas personalizadas:** *scaffolding* graduado (Wood/Bruner/Ross)
    --- de dicas conceituais leves a conselheiros-agentes (RF-036);
    **fade-out** conforme o domínio cresce.

-   **Conteúdos desbloqueados:** por **domínio demonstrado** (mastery),
    não por tempo; pré-requisitos podem ser saltados por quem já domina.

-   **Dificuldade balanceada:** carga cognitiva controlada (Sweller) ---
    número de variáveis ativas e complexidade crescem com o nível
    (Aprendiz→Guardião).

> ***Salvaguarda pedagógica:** a adaptação ajusta o caminho, nunca a
> competência-alvo. Facilitar não pode significar remover o conceito que
> a missão deve ensinar --- princípio explícito para o time de IA/game
> design.*

### 10. Feedback Inteligente

Fundamenta-se em **Hattie & Timperley (2007)** --- todo feedback
responde a *Onde vou?* (Feed Up), *Como estou indo?* (Feed Back), *Para
onde agora?* (Feed Forward), atuando nos níveis **tarefa, processo e
autorregulação** (evitando feedback de \"self\"/elogio vazio) --- e em
**Shute (2008)**: específico, oportuno, gerenciável e elaborado.
Operacionalizado pelo tutor LLM+RAG (RF-033/034), com filtros de
segurança (RF-037).

  -----------------------------------------------------------------------
  **Tipo**                **Característica**      **Exemplo (não
                                                  genérico)**
  ----------------------- ----------------------- -----------------------
  **Imediato**            Logo após a ação        \"A temperatura subiu 3
                                                  °C **assim que** você
                                                  dobrou a indústria.\"

  **Contextual**          Ancorado ao estado real \"Seus oceanos perderam
                          (RAG)                   O2 **porque** as algas
                                                  floresceram após o
                                                  excesso de
                                                  nutrientes.\"

  **Motivacional**        Reforça                 \"Boa: você **testou**
                          esforço/estratégia (não antes de decidir --- é
                          a pessoa)               assim que cientistas
                                                  trabalham.\"

  **Corretivo**           Aponta o equívoco e o   \"A extinção não foi
                          caminho                 \'azar\': faltou presa
                                                  para o predador ---
                                                  reveja a cadeia.\"

  **Explicativo**         Expõe a cadeia causal   \"Vulcão → aerossóis →
                          (RF-039)                resfriamento → estresse
                                                  nos produtores → queda
                                                  de população.\"

  **Baseado em            Usa dados do aluno      \"Nas últimas 3 eras
  evidências**                                    você ignorou o gráfico
                                                  de CO2; que tal
                                                  consultá-lo antes de
                                                  agir?\"
  -----------------------------------------------------------------------

**Diretrizes anti-genérico (para o time):** proibir respostas como
\"Muito bem!\" isoladas; todo feedback cita **um dado concreto** do
planeta do aluno, aponta **um próximo passo** e respeita a **faixa
etária** (RP-003/006). O tutor prioriza **perguntas** que induzam o
raciocínio (\"por que você acha que a população caiu?\") antes de
entregar a resposta --- coerente com IBL.

### 11. Painel Pedagógico (professor)

Coerente com RF-063/064/077 e RP-007 (a IA informa; o professor decide).
Princípios de design: **acionável** (cada indicador sugere uma ação),
**compreensível num relance**, **respeitoso à privacidade** (LGPD; dados
pessoais só com consentimento --- RF-068).

**Visões:**

-   **Visão de turma** --- mapa de calor competência × aluno; alertas de
    dificuldade (RF-077).

-   **Visão do aluno** --- progresso por competência, habilidades
    desenvolvidas, evolução temporal, evidências recentes, recomendações
    da IA.

-   **Visão de competência/BNCC** --- cobertura por habilidade (RF-076),
    útil à coordenação.

┌──────────────── PAINEL PEDAGÓGICO --- Turma 7ºB ────────────────┐

│ Progresso por competência (turma) ▮▮▮▮▮▯ 72% │

│ Raciocínio científico ██████▁ 78% Pensamento sistêmico ███▁ 55% │

│ Tomada de decisão █████▁▁ 64% Letramento de dados ████▁ 60% │

├───────────────────────────────────────────────────────────────┤

│ Dificuldades: 5 alunos travados em \"feedback climático\" (M4) │

│ Evolução: +12% em causa-efeito nas últimas 2 semanas │

│ Evidências recentes: 3 hipóteses testadas (Lucas), \... │

│ Recomendação da IA: revisar \"efeito estufa\" com a turma; │

│ sugerir missão de reforço a Ana, Beto, Caio │

└───────────────────────────────────────────────────────────────┘

**Componentes obrigatórios:** progresso por competência; habilidades
desenvolvidas; dificuldades (com aluno e tópico); indicadores de
aprendizagem (do *stealth*); evolução temporal; evidências coletadas
(rastreáveis à ação); **recomendações da IA** (próximos passos
sugeridos, sempre editáveis pelo professor).

### 12. Fundamentação Científica

Cada decisão pedagógica ancora-se em literatura. (Referências técnicas
completas estão na proposta §20; aqui, o núcleo pedagógico-avaliativo.)

  -----------------------------------------------------------------------------------------
  **Decisão do projeto**  **Base científica**     **Como influencia**
  ----------------------- ----------------------- -----------------------------------------
  Micromundo/artefato     **Papert** (1980);      Construção + ZDP definem o *core loop* e
  (planeta)               Piaget; Vygotsky        o *scaffolding*

  *Core loop*             **Kolb** (1984)         Estrutura
  experiencial                                    ação→observação→conceito→experimentação

  Conteúdo nas regras     **Bogost** (2007,       Mecânicas *são* o currículo
                          retórica procedural)    

  GBL eficaz              **Wouters** (2013);     Justifica o formato jogo para
                          **Clark** (2016); Gee;  aprendizagem/retenção
                          Plass (2015)            

  Objetivos e níveis      **Anderson &            Classifica objetivos e progressão por
                          Krathwohl** (2001,      domínio
                          Bloom revisada)         

  Currículo               **BNCC** (2018) +       Alinhamento de competências/habilidades
                          Complemento Computação  
                          (2022)                  

  Stealth assessment      **Mislevy et al.**      Arquitetura da avaliação embutida
                          (2003, ECD); **Shute**  
                          (2011); **Shute &       
                          Ventura** (2013)        

  Modelo do aluno         **Corbett & Anderson**  Estimativa contínua de domínio
                          (1995, BKT); IRT        (RF-072/073)

  Avaliação formativa     **Black & Wiliam**      Ênfase no feedback durante a aprendizagem
                          (1998)                  

  Feedback inteligente    **Hattie & Timperley**  Modelo e diretrizes do tutor (Etapa 10)
                          (2007); **Shute**       
                          (2008)                  

  Autorregulação          **Zimmerman** (2002)    Metas, monitoramento e reflexão no jogo

  Motivação               **Deci & Ryan** (2000,  Autonomia/competência/pertencimento;
                          SDT); Malone;           fluxo
                          Csikszentmihalyi        

  Carga cognitiva         **Sweller** (1988)      Controla complexidade por nível (UI
                                                  infantil)

  Aprendizagem            **VanLehn** (2011);     Personalização e tutoria
  adaptativa/ITS          **Woolf** (2009);       
                          **Luckin et al.**       
                          (2016)                  

  Learning Analytics      **Siemens & Long**      Telemetria pedagógica e dashboards
                          (2011); **Baker &       
                          Inventado** (2014)      

  AIED contemporâneo      **Holmes, Bialik &      Ética e papéis da IA na educação
                          Fadel** (2019)          
  -----------------------------------------------------------------------------------------

**Referências pedagógicas adicionais (além da proposta §20):**

-   BLACK, P.; WILIAM, D. Assessment and classroom learning. *Assessment
    in Education*, 1998.

-   CORBETT, A.; ANDERSON, J. Knowledge tracing. *User Modeling and
    User-Adapted Interaction*, 1995.

-   DECI, E.; RYAN, R. Self-determination theory. *Psychological
    Inquiry*, 2000.

-   de FREITAS, S. Are games effective learning tools? *Educational
    Technology & Society*, 2018.

-   HATTIE, J.; TIMPERLEY, H. The power of feedback. *Review of
    Educational Research*, 2007.

-   HOLMES, W.; BIALIK, M.; FADEL, C. *Artificial Intelligence in
    Education*. CCR, 2019.

-   MISLEVY, R.; STEINBERG, L.; ALMOND, R. On the structure of
    educational assessments. *Measurement*, 2003.

-   SHUTE, V. Focus on formative feedback. *Review of Educational
    Research*, 2008.

-   SHUTE, V.; VENTURA, M. *Stealth Assessment*. MIT Press, 2013.

-   SIEMENS, G.; LONG, P. Penetrating the fog: analytics in learning and
    education. *EDUCAUSE Review*, 2011.

-   SWELLER, J. Cognitive load during problem solving. *Cognitive
    Science*, 1988.

-   ZIMMERMAN, B. Becoming a self-regulated learner. *Theory Into
    Practice*, 2002.

### 13. Validação Pedagógica

Estratégia para validar o modelo **antes e durante** o desenvolvimento
(coerente com proposta §14/§17 e ERS §9), combinando validação por
especialistas e estudo em campo (Design-Based Research).

  ------------------------------------------------------------------------------
  **Público**           **Instrumento**      **Objetivo**      **Métrica**
  --------------------- -------------------- ----------------- -----------------
  **Professores**       Questionário         Usabilidade       Concordância;
                        (Likert) +           pedagógica,       temas
                        entrevista           alinhamento à     
                                             prática           

  **Coordenadores**     Grupo focal          Cobertura BNCC,   Consenso; lacunas
                                             relatórios,       
                                             adoção            

  **Especialistas em    **Validação por      Validade da       **IVC ≥ 0,80**;
  Educação/Ciências**   especialistas**      matriz BNCC e das convergência
                        (painel              rubricas          Delphi
                        **Delphi**) +                          
                        **IVC** (Índice de                     
                        Validade de                            
                        Conteúdo)                              

  **Pesquisadores**     Estudo               Eficácia de       Ganho de **Hake
                        quase-experimental   aprendizagem      ⟨g⟩**; comparação
                                                               com controle

  **Alunos** (indireto) Observação +         Engajamento,      SUS; IMI;
                        *playtesting* +      compreensão,      conclusão
                        escala de motivação  motivação         
                        (IMI)                                  
  ------------------------------------------------------------------------------

**Rubricas** serão validadas por especialistas (IVC) e testadas quanto à
**confiabilidade entre avaliadores** (concordância). O ciclo **DBR**
refina o modelo a cada iteração em sala. **Ética:** consentimento dos
responsáveis e assentimento dos alunos; dados anonimizados
(RNF-009/011).

### 14. Entregáveis e Recomendações

### 14.1 Entregáveis desta etapa (contidos no documento)

21. **Modelo pedagógico completo** (§1) · 2. **Objetivos de
    aprendizagem** (§2) · 3. **Matriz BNCC** (§3) · 4. **Objetivos por
    Bloom revisada** (§2) · 5. **Trilhas por nível** (§4) · 6. **Matriz
    de competências** (§5) · 7. **Modelo de avaliação** (§6) · 8.
    **Estratégia de Stealth Assessment** (§7) · 9. **Matriz de
    evidências** (§8) · 10. **Estratégia de adaptação por IA** (§9)
    · 11. **Modelo de feedback inteligente** (§10) · 12. **Painel
    pedagógico** (§11) · 13. **Fundamentação científica** (§12) · 14.
    **Recomendações para a próxima etapa** (abaixo).

### 14.2 Recomendações para a próxima etapa (arquitetura, IA e mecânicas)

-   *Especificar o* Competency Model *como esquema formal* (grafo de
    competências × relações) para instanciar a rede bayesiana (pgmpy)
    --- insumo direto do modelo de dados.

-   **Traduzir a Matriz de Evidências (§8) em regras de evidência** por
    mecânica (contrato entre game design e o serviço de avaliação
    Python).

-   *Definir o* Task Model*:* para cada missão, quais ações-evidência
    ela deve eliciar (garante que o jogo gere dado avaliável).

-   *Projetar os* endpoints *de avaliação (RF-071/072) e o modelo de
    dados de telemetria* (evento→evidência→atualização), respeitando
    anonimização.

-   **Prototipar o tutor de feedback** com as diretrizes anti-genérico
    (§10) e testar ancoragem RAG (mitiga RSK-03).

-   **Wireframar o painel** (§11) com professores reais antes de
    implementar (RF-063/064).

-   **Validar a matriz BNCC** (IVC/Delphi) --- pré-condição para
    materiais oficiais (RSK-06).

-   **Planejar a calibração** do *stealth assessment* contra
    pré/pós-teste (RF-074) desde o piloto.

> ***Rastreabilidade fim-a-fim:** Competência → Habilidade BNCC →
> Objetivo (Bloom) → Mecânica → Evidência → Método de inferência →
> Indicador do painel. Manter essa cadeia é o que garante que
> **pedagogia, IA e código permaneçam alinhados** nas próximas fases.*

*Fim da Modelagem Pedagógica. Documento pronto para orientar diretamente
a modelagem da arquitetura de software, o sistema de IA (modelo de
competência, evidências e adaptação) e o design das mecânicas do jogo.
Coerência preservada com a proposta, o resumo executivo e o ERS;
decisões pedagógicas justificadas e ancoradas em literatura.*

# PARTE III — Game Design


## 7 Game Design Document

### 1. Visão geral do gameplay

### 1.1 Objetivo principal

O jogador **cria um planeta e o conduz através de eras**, tomando
decisões que moldam clima, geologia, vida e --- nas eras finais ---
civilização. Não há \"vencer\" no sentido tradicional: o objetivo é
**manter um mundo vivo e próspero**, descobrindo como seus sistemas se
conectam e enfrentando as consequências das próprias escolhas. O sucesso
é medido por **biodiversidade, estabilidade e prosperidade** do mundo
que o aluno construiu --- um objetivo aberto que premia compreensão, não
memorização.

### 1.2 Sentimento-alvo (a fantasia)

A fantasia central é a de **guardião/criador de um mundo vivo**:
assombro diante da complexidade, orgulho de autoria, curiosidade de \"e
se...?\", e a tensão boa de decisões difíceis. O jogo deve provocar
**maravilhamento** (um planeta belo e reativo), **agência** (minhas
decisões importam) e **descoberta** (eu *entendi* por que isso
aconteceu). Coerente com a fantasia definida na Modelagem Pedagógica
(§1.3: aluno como protagonista-autor-cientista).

### 1.3 Habilidades cognitivas constantemente estimuladas

Experimentação, formulação de hipóteses, pensamento sistêmico, tomada de
decisão baseada em evidências, análise de consequências e criatividade
--- exatamente as competências da **Matriz de Competências** (§5 da
Modelagem) e as evidências do **stealth assessment** (§7--8). O *design*
garante que essas habilidades sejam **a forma de jogar**, não um
apêndice.

### 1.4 O que torna o jogo divertido (além do propósito)

-   **Sandbox expressivo:** cada planeta é único e \"meu\" (autoria).

-   **Emergência:** sistemas simples geram histórias surpreendentes (uma
    extinção que vira renascimento).

-   **Beleza reativa:** ver oceanos surgirem, florestas se espalharem,
    cidades acenderem à noite.

-   **Suspense de eventos:** meteoros, pandemias, eras glaciais que
    testam o mundo.

-   **Domínio progressivo:** a satisfação de, aos poucos, \"sacar\" o
    sistema (o *fun* de Koster).

-   **Narrativa emergente:** a saga do planeta é contada pelas escolhas
    do jogador.

### 1.5 Gênero predominante (e justificativa)

**Simulação de sistemas / \"god-game\" sandbox**, com forte camada de
**gerenciamento de recursos e estratégia** e um eixo de
**evolução/ecologia emergente**.

  -----------------------------------------------------------------------
  **Gênero**              **Peso**                **Por quê**
  ----------------------- ----------------------- -----------------------
  Simulação de sistemas                           O coração é um mundo
  (Gaia-like)                                     vivo e acoplado
                                                  (proposta §6);
                                                  ancestrais diretos:
                                                  *SimEarth* (Gaia) e
                                                  *Spore* (evolução)

  Sandbox / construção de                         Autoria e expressão
  mundos                                          (construcionismo,
                                                  Papert)

  Gerenciamento de                                *Trade-offs* e economia
  recursos / estratégia                           de ações forçam
                                                  priorização (M8,
                                                  RF-017/018)

  Simulação ecológica /                           Seleção natural e
  evolução                                        cadeias emergem
                                                  (RF-031/032)
  -----------------------------------------------------------------------

**Justificativa:** o gênero *simulação sandbox* é o único que faz o
conteúdo **emergir** (não perguntar). É também o que melhor sustenta
IBL/PBL e a retórica procedural da Modelagem Pedagógica. A camada de
estratégia/recursos entra para **impedir a onipotência** (sem ela, não
há decisão real nem trade-off --- logo, sem pensamento crítico).

### 2. Core Loop

### 2.1 O ciclo (é o ciclo de Kolb, jogável)

O *core loop* **é** o ciclo experiencial de Kolb da Modelagem
Pedagógica, transformado em jogabilidade:

┌───────────────────────────────────────────────────────────┐

│ │

▼ │

\(1\) OBSERVAR ──► (2) ANALISAR ──► (3) DECIDIR ──► (4) INTERVIR ──► (5)
SIMULAR

estado do gráficos e escolher a gastar ação o planeta

planeta 3D indicadores intervenção (trade-off) evolui/reage

▲ │

│ ▼

\(8\) PLANEJAR ◄── (7) APRENDER ◄────────────────────── (6) RECEBER
FEEDBACK

próxima tutor formaliza ver consequências

hipótese o conceito (Kolb) + explicação causal

### 2.2 Ações contínuas do jogador

Observar o mundo 3D e os painéis (RF-021/051); levantar uma hipótese;
escolher e aplicar uma intervenção limitada por recursos (RF-017);
avançar o tempo e assistir à reação (RF-013/014); ler o feedback do
tutor (RF-033/039); ajustar a estratégia.

### 2.3 Decisões mais importantes

As de **trade-off socioambiental** (Etapa 4) e as de **alocação de
recursos escassos** (Etapa 5) --- são elas que exigem ponderação, geram
consequências duradouras e produzem as evidências mais ricas para o
*stealth assessment* (decisão, análise de consequências, pensamento
sistêmico).

### 2.4 Como o aprendizado ocorre no loop

Cada volta do ciclo é um **experimento**: o aluno prevê (hipótese), age
(intervém), observa (simulação) e concilia previsão×resultado
(conceito). O tutor fecha a volta convertendo experiência em conceito
explícito. Aprender **não interrompe** o jogo --- é o próprio ato de
jogar (coerência com RP-004, stealth).

### 2.5 Influência da IA em cada etapa

-   **Observar/Analisar:** IA destaca padrões e sugere o que olhar
    (identifica oportunidade de aprendizagem).

-   **Decidir:** conselheiros-agentes (RF-036) oferecem *scaffolding*
    sob demanda.

-   **Simular:** motores de IA governam evolução (AG, RF-031) e ecologia
    (ABM, RF-032); física permanece determinística.

-   **Feedback/Aprender:** tutor LLM+RAG explica a cadeia causal
    (RF-033/034/039); *stealth* atualiza o modelo do aluno (RF-072).

-   **Planejar:** progressão adaptativa calibra o próximo desafio
    (RF-020/035).

EOF echo \"Etapas 1-2 anexadas.\"

### 3. Mecânicas principais

> *Para cada mecânica: **como funciona** e **dupla contribuição**
> (diversão + objetivo pedagógico, com rastreio a módulo/RF).*

**3.1 Construção do planeta (RF-011 · M1).** O jogador \"esculpe\" um
mundo escolhendo dimensões (astronômica, física, geológica, química,
hidrológica, biológica). É a tela-manifesto da autoria. *Diversão:*
criar algo único e vê-lo ganhar forma 3D. *Pedagogia:* compreender
interdependência de variáveis e habitabilidade (EF09CI16).

**3.2 Configuração inicial guiada (RF-012).** A IA sugere valores
plausíveis e **alerta combinações inviáveis** com explicação (\"com essa
distância, a água ferve\"). *Diversão:* remove a paralisia da tela em
branco; vira um diálogo. *Pedagogia:* causalidade já na gênese; reduz
carga cognitiva (Sweller) para iniciantes.

**3.3 Evolução automática (RF-013/014 · M2--M7).** O tempo avança em
escalas ajustáveis; subsistemas acoplados evoluem sozinhos. *Diversão:*
assistir ao mundo \"viver\" (oceanos surgindo, vida se espalhando).
*Pedagogia:* observa dinâmica, emergência e retroalimentação sem
intervir.

**3.4 Intervenções do jogador (RF-017/018 · M8).** Ações limitadas por
recursos (Etapa 5) que alteram o planeta, sempre com trade-off.
*Diversão:* poder de moldar o destino do mundo. *Pedagogia:* tomada de
decisão e análise de consequências --- as evidências mais ricas do
stealth.

**3.5 Pesquisa científica (árvore científica · Etapa 8).** Gastando
**Pontos de Pesquisa**, o jogador \"desbloqueia entendimento\": novos
instrumentos, camadas de dados e intervenções. *Diversão:* sensação de
crescimento e novas ferramentas. *Pedagogia:* progressão por
**conhecimento**, não por grind; conecta conceitos.

**3.6 Descoberta de espécies (Códex · M7).** Quando o motor evolutivo
(RF-031) gera uma nova espécie, ela é **catalogada** num códex com seus
traços e relações tróficas. *Diversão:* colecionar/nomear criaturas
únicas (autoria + coleção). *Pedagogia:* seleção natural, adaptação e
cadeias tróficas tornam-se observáveis e nomeáveis.

**3.7 Eventos naturais (RF-019 · Etapa 9).** Perturbações estocásticas
(meteoros, erupções, pandemias) condicionadas ao estado do planeta.
*Diversão:* suspense e reviravoltas --- a fonte da narrativa emergente.
*Pedagogia:* testa resiliência; demonstra causa-efeito, atraso e
não-linearidade.

**3.8 Evolução climática (M4).** Autômatos climáticos com feedbacks
(gelo-albedo, estufa) produzem zonas, monções e transições. *Diversão:*
ver o planeta mudar de cara (verde→gelo→deserto). *Pedagogia:* clima
como sistema (EF08CI14/16), feedbacks e pontos de inflexão.

**3.9 Desenvolvimento ecológico (M6).** ABM (RF-032) gera sucessão,
biodiversidade e relações (predador-presa, simbiose). *Diversão:* um
ecossistema que \"acontece\" e reage. *Pedagogia:* equilíbrio,
capacidade de suporte e efeitos em cascata.

**3.10 Exploração científica (sondas/varreduras).** O jogador aciona
\"varreduras\" que revelam dados ocultos de uma região (solo, água,
população). *Diversão:* descobrir o desconhecido; recompensa a
curiosidade. *Pedagogia:* observação e coleta de dados como prática
científica (EM13CNT301).

**3.11 Missões (RF-062 · Trilhas).** Objetivos estruturados ancorados a
habilidades da BNCC, definidos pelo professor ou pela progressão.
*Diversão:* metas curtas e claras (ARCS/fluxo). *Pedagogia:* direcionam
a competência-alvo sem engessar a exploração.

**3.12 Objetivos (metas de era/missão).** Cada era propõe metas abertas
(\"estabilize o clima\", \"atinja 3 biomas\"). *Diversão:* senso de
propósito e progresso. *Pedagogia:* transformam conteúdo em desafio
investigativo (PBL).

**3.13 Sistema de conquistas (baseado em descoberta).** Conquistas
premiam **compreensão e feitos científicos** (\"provocou e reverteu uma
era glacial\"), não repetição. *Diversão:* reconhecimento significativo.
*Pedagogia:* reforça estratégia/insight, não grind (evita recompensa
vazia --- Etapa 11).

**3.14 Desafios (cenários).** Situações-problema prontas (\"planeta à
beira do colapso --- salve-o\"). *Diversão:* variedade e rejogabilidade.
*Pedagogia:* PBL puro; ótimos para avaliação de transferência.

**3.15 Sistema de descoberta (Códex/Diário do Mundo).** Um diário que
**se preenche** conforme o aluno experimenta --- conceitos, espécies,
eventos e \"lições\" que ele destravou. *Diversão:* progresso tangível e
colecionável. *Pedagogia:* torna visível o aprendizado; base de
metacognição e autorregulação (§6 Modelagem).

**3.16 Observação científica (instrumentos e camadas · RF-054).**
Camadas de visualização (temperatura, biomas, população, recursos) e
medições. *Diversão:* \"raio-X\" satisfatório do mundo. *Pedagogia:*
letramento de dados; ler o planeta como um cientista.

### 4. Mecânicas de trade-off (núcleo do jogo)

Toda intervenção significativa tem **ganho e custo**. Não existe escolha
\"grátis\" --- é isso que gera decisão real e, portanto, pensamento
crítico. (Coerência: M8, RF-018, competência \"tomada de decisão\".)

  -----------------------------------------------------------------------------------------------------------------
  **\#**      **Decisão**      **Ganho**        **Custo /              **Conceito/Disciplina**   **Evidência
                                                consequência**                                   (stealth)**
  ----------- ---------------- ---------------- ---------------------- ------------------------- ------------------
  1           Intensificar     \+ alimento, +   − biodiversidade,      Ecologia/Química          análise de
              agricultura      população        erosão, eutrofização                             consequências

  2           Industrializar   \+ tecnologia, + \+ CO2, poluição,      Química/Física            decisão sob
                               recursos         aquecimento                                      trade-off

  3           Minerar recursos \+ minerais, +   degradação,            Geologia                  planejamento
                               energia          instabilidade                                    
                                                geológica                                        

  4           Expandir cidades \+ prosperidade  perda de habitat,      Ecologia/Geo              pensamento
                                                fragmentação                                     sistêmico

  5           Reflorestar      \+ O2, +         − terra econômica,     Química/Ecologia          visão de longo
                               sequestro C, +   lento                                            prazo
                               habitat                                                           

  6           Preservar        \+               − crescimento          Sustentabilidade          valor de longo
              reservas         resiliência, +   econômico                                        prazo
                               biodiversidade                                                    

  7           Queimar          \+ energia       \+ estufa,             Química                   causa-efeito
              combustível      barata           acidificação                                     
              fóssil                                                                             

  8           Construir usina  energia sem CO2  alto custo, tempo      Física/Sustentab.         trade-off
              limpa                                                                              custo×impacto

  9           Irrigar em massa \+ safra         rebaixa lençol,        Hidrologia                consequência
                                                saliniza solo                                    tardia

  10          Represar rios    \+ água/energia  altera ecossistema     Ecologia/Geo              sistemas
                                                aquático                                         

  11          Introduzir       controla praga   risco de invasora      Ecologia                  análise de risco
              espécie útil                                                                       

  12          Erradicar        protege rebanho  explosão de presas →   Cadeias tróficas          efeito em cascata
              predador                          colapso                                          

  13          Pescar           \+ alimento      colapso de estoque     Ecologia                  capacidade de
              intensivamente                    pesqueiro                                        suporte

  14          Elevar           derrete gelo, +  eleva mar, perde costa Clima                     feedback
              temperatura      terra                                                             gelo-albedo
              (aquecer)                                                                          

  15          Semear nuvens    alivia seca      enchentes,             Clima                     não-linearidade
              (chuva)                           desequilíbrio                                    

  16          Acelerar tempo   avança eras      perde controle fino de Meta/estratégia           planejamento
                               rápido           eventos                                          

  17          Concentrar em    ganho local      negligencia o resto do Estratégia                priorização
              uma região       rápido           globo                                            

  18          Política         estabiliza       − influência/econômico Sustentabilidade          argumentação
              ambiental rígida sistema          curto prazo                                      

  19          Subsidiar        acelera pesquisa consome orçamento      Economia/Tec              alocação de
              tecnologia                                                                         recurso

  20          Explorar cometa  \+ água/voláteis risco de impacto       Astronomia                risco×recompensa
              (água)                                                                             

  21          Aumentar campo   protege          alto custo energético  Física                    trade-off técnico
              magnético        atmosfera                                                         
              (terraform)                                                                        

  22          Espalhar         \+ O2 veloz      monocultura frágil     Ecologia                  biodiversidade
              vegetação rápida                                                                   

  23          Drenar pântano   \+ terra urbana  perde filtro/berçário  Ecologia                  serviço
              p/ cidade                         natural                                          ecossistêmico

  24          Caçar espécie    recupera         pode atingir espécie   Ecologia                  efeito colateral
              invasora         equilíbrio       nativa                                           

  25          Estocar carbono  − estufa         limita agricultura     Química/Clima             trade-off
              no solo                                                                            climático

  26          Migrar população evita desastre   tensão de recursos no  Geo/Social                consequência
                               local            destino                                          sistêmica

  27          Priorizar        \+ prosperidade  dívida ambiental       Sustentabilidade          curto×longo prazo
              economia                          acumulada                                        

  28          Priorizar        \+ saúde do      crescimento humano     Sustentabilidade          valores/decisão
              natureza         sistema          mais lento                                       

  29          Geoengenharia    resfria rápido   efeitos colaterais     Clima                     incerteza
              (aerossóis)                       imprevistos                                      científica

  30          Não intervir     preserva estado  pode não evitar        Meta                      juízo de
              (deixar correr)  natural          colapso                                          necessidade
  -----------------------------------------------------------------------------------------------------------------

**Como os trade-offs favorecem a aprendizagem:**

-   **Pensamento crítico:** obrigam a comparar alternativas e antecipar
    efeitos indesejados --- não há \"resposta certa\" universal.

-   **Raciocínio científico:** cada decisão é uma hipótese sobre o
    sistema; a simulação é o experimento que a confirma ou refuta.

-   **Tomada de decisão baseada em evidências:** o jogador consulta
    dados (RF-021) antes de escolher.

-   **Sistemas complexos:** os efeitos em cascata ensinam que \"puxar
    uma alavanca\" mexe em todo o sistema (retroalimentação, atraso,
    não-linearidade).

### 5. Economia de ações

O jogador **nunca** pode resolver tudo ao mesmo tempo: recursos escassos
forçam **planejamento estratégico** (e criam o trade-off). Cada era tem
seu orçamento; sobrar poder trivializa a decisão e mata o aprendizado.

  ------------------------------------------------------------------------
  **Recurso**       **Como é obtido** **Como é          **Efeito na
                                      consumido**       evolução**
  ----------------- ----------------- ----------------- ------------------
  **Tempo / Pontos  Renovam por       Cada intervenção  Limita nº de
  de Ação**         turno/era         custa ação        mudanças por
                                                        período →
                                                        priorização

  **Energia**       Recursos          Terraformação,    Restringe grandes
                    naturais, usinas  indústria,        intervenções
                                      pesquisa          

  **Orçamento**     Prosperidade      Obras, políticas, Liga economia a
                    econômica         tecnologia        capacidade de ação

  **Pontos de       Observação,       Desbloqueia       Progressão por
  Pesquisa**        descobertas,      árvore científica conhecimento (§8)
                    missões                             

  **Influência**    Estabilidade      Políticas         Governa a era das
                    social, feitos    ambientais,       civilizações
                                      decisões          
                                      antrópicas        

  **Recursos        Existem no        Mineração,        Ensina finitude e
  Naturais**        planeta (finitos) indústria,        sustentabilidade
                                      expansão          

  **Capacidade      Árvore científica Habilita          Define o que é
  Tecnológica**                       intervenções      possível fazer
                                      avançadas         
  ------------------------------------------------------------------------

**Regras de design (para impedir onipotência):**

-   Recursos são **finitos por era** e alguns **não renováveis**
    (recursos naturais) --- reforçando sustentabilidade (CG10).

-   Intervenções têm **custo + tempo (cooldown)**: não dá para
    \"spammar\" soluções.

-   **Sinergias e conflitos:** algumas ações barateiam outras (pesquisa
    reduz custo de tecnologia), outras competem pelo mesmo recurso --- o
    que exige sequenciamento (planejamento, evidência do stealth).

-   O balanceamento desses valores é **parametrizável por trilha/nível**
    (Etapa 6/12), permitindo calibração pedagógica.

> ***Justificativa:** escassez é o que transforma \"clicar\" em
> \"decidir\". Sem economia de ações, não há trade-off; sem trade-off,
> não há pensamento crítico. A economia é, portanto, um **dispositivo
> pedagógico**, não só um dispositivo de jogo.*

### 6. Curva de dificuldade

A complexidade cresce **gradualmente**, acompanhando as eras (Etapa 7) e
os níveis de domínio da Modelagem (§4:
Aprendiz→Explorador→Investigador→Guardião). O objetivo é manter o
jogador no **canal de fluxo** (nem tédio, nem ansiedade ---
Csikszentmihalyi).

**Como novos sistemas são desbloqueados:** um subsistema por vez,
atrelado à era e à pesquisa. O aluno domina clima antes de acoplar
oceanografia; domina ecologia simples antes de coevolução. (Evita
sobrecarga --- Sweller.)

**Quando novos fenômenos aparecem:** eventos leves e raros no início
(uma seca localizada); eventos sistêmicos e encadeados no avançado (era
glacial + pandemia). A introdução é **just-in-time** (Gee): o fenômeno
surge quando o aluno tem base para entendê-lo.

**Como a IA ajusta a dificuldade:** o **Diretor** (RF-020) e a
progressão adaptativa (§9 Modelagem) calibram frequência/severidade de
eventos e complexidade das missões ao domínio estimado (RF-072). Quem
emperra recebe *scaffolding* e desafios menores; quem domina recebe
complexidade e autonomia maiores --- sempre sem alterar a
competência-alvo.

  ----------------------------------------------------------------------------------
  **Perfil**          **Variáveis    **Eventos**    **Scaffolding**   **Objetivo
                      ativas**                                        típico**
  ------------------- -------------- -------------- ----------------- --------------
  **Iniciante**       Poucas,        Raros, leves,  Alto (dicas,      \"Crie um
                      guiadas        isolados       conselheiros)     mundo
                                                                      habitável\"

  **Intermediário**   Subsistemas    Moderados,     Sob demanda       \"Estabilize o
                      acoplados      ocasionais em                    clima após uma
                                     cadeia                           erupção\"

  **Avançado**        Todas,         Frequentes,    Mínimo (fade-out) \"Sustente a
                      coevolução     sistêmicos,                      prosperidade
                                     encadeados                       por N eras sob
                                                                      crises\"
  ----------------------------------------------------------------------------------

**Anti-pico de complexidade:** cada novo elemento vem com um
**desafio-tutorial** de baixa aposta (erro seguro, RP-010) antes de
compor com os demais --- garantindo crescimento suave.

### 7. Narrativa das eras

A progressão macro é contada como a **saga do planeta** --- uma
narrativa **emergente** (escrita pelas decisões do aluno), não
linear-roteirizada. Cada era introduz conteúdo, mecânica, desafio,
descoberta e objetivo pedagógico novos, num crescimento suave (Etapa 6).

  -------------------------------------------------------------------------------------------------------
  **Era**          **Novos                 **Desafio central**    **Descobertas**    **Objetivo
                   conteúdos/mecânicas**                                             pedagógico
                                                                                     (módulo/BNCC)**
  ---------------- ----------------------- ---------------------- ------------------ --------------------
  **1. Formação    Criação e parâmetros;   Estabelecer um mundo   Zona habitável     M1/M2 · EF06CI11/14,
  Planetária**     física/órbita           viável                                    EF09CI16

  **2. Surgimento  Hidrologia, oceanos,    Formar oceanos         Marés, correntes   M3/M5
  da Água**        ciclo da água           estáveis                                  

  **3. Moléculas   Química prebiótica;     Criar condições para a Química da vida    M3 · EM13CNT201
  Orgânicas**      ciclos                  vida                                      

  **4. Primeiras   Vida microbiana; O2     Iniciar e sustentar a  Fotossíntese, O2   M6/M7
  Formas de Vida** (oxigenação)            biosfera                                  

  **5.             Motor evolutivo; códex  Promover               Especiação,        M7 · EF09CI11
  Diversificação   de espécies             biodiversidade         adaptação          
  Biológica**                                                                        

  **6. Colonização Vida em terra; biomas;  Expandir a vida ao     Cadeias tróficas   M6 · EF07CI07/08
  Terrestre**      sucessão                continente                                

  **7. Grandes     Eventos sistêmicos      Sobreviver/recuperar   Resiliência,       M4/M9 · EF08CI16
  Extinções**      encadeados              de crises              pontos de inflexão 

  **8.             Coevolução; simbiose;   Manter um sistema      Redes ecológicas   M6
  Ecossistemas     equilíbrio              maduro e estável                          
  Complexos**                                                                        

  **9.             Influência; trade-offs  Prosperar sem destruir Sustentabilidade   M8 ·
  Civilizações**   antrópicos              o mundo                                   EM13CNT203/206/306
  *(futuro)*                                                                         
  -------------------------------------------------------------------------------------------------------

**Como a narrativa mantém o engajamento:**

-   **Progresso épico:** ir do vazio cósmico a um mundo vivo dá uma
    sensação de jornada grandiosa.

-   **Emergência narrativa:** \"a extinção da Era 7 que abriu espaço
    para os grandes herbívoros\" é uma história que **o aluno** criou
    --- memorável e pessoal.

-   **Curiosidade de continuação:** cada era termina abrindo a próxima
    (\"a vida chegou aos oceanos... conseguirá alcançar a terra?\").

-   **Ritmo variado:** eras contemplativas (assistir a vida surgir)
    alternam com eras tensas (crises) --- controle de ritmo (*pacing*)
    que sustenta o fluxo.

### 8. Sistema de progressão

A progressão **não** é XP/níveis arbitrários. É **baseada em
conhecimento adquirido e decisões tomadas** --- coerente com a
progressão por competências da Modelagem (§4/§6). Quatro eixos
entrelaçados:

**8.1 Árvore Científica (compreensão).** Gastando Pontos de Pesquisa e
**experimentando**, o aluno desbloqueia *entendimento* (novos conceitos
no Códex, camadas de dados, instrumentos de observação). Avançar aqui é
literalmente \"aprender coisas\". *Ex.:* dominar \"efeito estufa\"
desbloqueia a camada de temperatura e a intervenção de captura de
carbono.

**8.2 Árvore Tecnológica (capacidades).** Desbloqueia *ferramentas de
intervenção* (energia limpa, geoengenharia, políticas). Depende da
Árvore Científica: **você só pode fazer o que entende** --- princípio
pedagógico embutido na mecânica.

**8.3 Evolução do planeta (macro).** As eras (Etapa 7) são a progressão
do mundo; cada uma é um marco de estado (oceanos, vida, biomas,
civilização).

**8.4 Evolução do jogador (maestria).** Os níveis
Aprendiz→Explorador→Investigador→Guardião **não** são comprados: são
**inferidos pelo stealth assessment** (RF-072) a partir de competências
demonstradas. O Códex/Diário (3.15) é a representação visível dessa
evolução.

> ***Desbloqueios por domínio, não por grind:** um conteúdo abre quando
> o aluno **demonstra** a competência pré-requisito (mastery learning),
> nunca por tempo de tela. Isso alinha diversão (novidade constante) e
> pedagogia (sem lacunas cumulativas).*

### 9. Eventos dinâmicos

Sistema estocástico condicionado ao estado do planeta (proposta §8;
RF-019/020). Eventos são a principal fonte de **tensão** e de
**narrativa emergente**, e um poderoso gerador de evidências
(resiliência, resolução de problemas).

  -----------------------------------------------------------------------------------------------------------------
  **Categoria**         **Exemplos**    **Frequência**   **Impacto**            **Probabilidade**   **Interação com
                                                                                                    a IA**
  --------------------- --------------- ---------------- ---------------------- ------------------- ---------------
  **Naturais/gerais**   Incêndios,      Média            Local-médio            Condicionada a      Diretor modula
                        pragas                                                  seca/densidade      ritmo

  **Climáticos**        Seca, enchente, Média-baixa      Médio-alto/sistêmico   Sobe com            Acopla a
                        era glacial,                                            instabilidade       autômatos (M4)
                        onda de calor                                           climática           

  **Geológicos**        Terremoto,      Baixa            Alto                   Sobe com atividade  Injeta
                        erupção,                                                tectônica           CO2/aerossóis
                        tsunami,                                                                    (acopla clima)
                        supervulcão                                                                 

  **Biológicos**        Pandemia,       Média            Médio-alto             Sobe com baixa      Acopla a AG/ABM
                        mutação,                                                biodiversidade      (M6/M7)
                        espécie                                                                     
                        invasora,                                                                   
                        colapso de                                                                  
                        polinizadores                                                               

  **Astronômicos**      Meteoro,        Baixa (raros)    Muito alto             Base + risco por    Gerador de
                        cometa,                                                 parâmetros          Poisson; testa
                        tempestade                                                                  campo magnético
                        solar, variação                                                             
                        estelar                                                                     
  -----------------------------------------------------------------------------------------------------------------

**Princípios:**

-   **Probabilidade condicionada:** um planeta com pouca biodiversidade
    é mais vulnerável a pandemias --- o evento \"ensina\" a fragilidade
    sistêmica.

-   **Impacto propaga:** todo evento cascateia pelos acoplamentos
    (proposta §8) --- reforço de pensamento sistêmico.

-   **IA como curadora:** o Diretor escolhe *quando* e *quão forte*,
    respeitando o objetivo pedagógico e o fluxo (nunca \"injusto\"); a
    plausibilidade científica é preservada.

-   **Telegrafia:** eventos maiores dão sinais prévios (instrumentos de
    observação detectam), premiando o aluno atento (letramento de dados)
    e evitando frustração aleatória.

### 10. IA como Mestre da Simulação

A IA age como um \"mestre de jogo\" invisível --- mas com uma
**fronteira rígida**: o que o aluno precisa **entender** permanece
**determinístico e explicável**; a IA governa o que deve ser
**emergente, adaptativo ou mediado**. (Coerência: proposta §9; princípio
de IA explicável.)

  -----------------------------------------------------------------------
  **Função durante o      **Determinístico ou     **Técnica**
  gameplay**              IA**                    
  ----------------------- ----------------------- -----------------------
  Física, órbitas,        **Determinístico**      Simulação numérica
  gravidade, radiação                             (Verlet/RK4)

  Ciclos químicos,        **Determinístico**      Estoques e fluxos
  balanço de energia                              (regras)

  Clima e geologia (dado  **Determinístico**      Autômatos
  o *seed*)               (reprodutível, RF-023)  celulares/procedural

  Equilíbrio ecológico e  **IA (emergente)**      ABM (Mesa, RF-032)
  populações                                      

  Evolução das espécies   **IA (emergente)**      Algoritmos evolutivos
                                                  (DEAP, RF-031)

  Gerar/temporizar        **IA (adaptativo)**     Diretor:
  eventos                                         probabilístico + RL
                                                  contido (RF-020)

  Adaptar desafios e      **IA (adaptativo)**     Modelo do aluno BKT/IRT
  desbloqueios                                    (RF-072/073)

  Sugerir hipóteses /     **IA (mediação)**       Tutor/conselheiros
  oportunidades de                                (RF-033/036)
  aprendizagem                                    

  Personalizar feedback e **IA (mediação)**       LLM+RAG
  explicações                                     (RF-033/034/039)

  Ajustar parâmetros da   **IA (adaptativo)**     Diretor, dentro de
  simulação (dificuldade)                         limites plausíveis
  -----------------------------------------------------------------------

**Regra de ouro:** a IA **nunca** falsifica a ciência para \"ajudar\"
--- ela ajusta o *contexto* (quais desafios, quando, com quanto apoio),
não as *leis* do mundo. Assim, o aluno pode sempre confiar na
causalidade que observa (condição do aprendizado científico). Decisões
que exigem confiança e reprodutibilidade (física, correção de conceitos)
são determinísticas; decisões que exigem variedade, personalização e
vida (evolução, ecologia, ritmo, feedback) são de IA.

### 11. Motivação e engajamento

Estratégias ancoradas em teorias de motivação, cada uma com
implementação concreta no jogo.

  -------------------------------------------------------------------------
  **Estratégia**          **Teoria**              **Como o jogo
                                                  implementa**
  ----------------------- ----------------------- -------------------------
  **Autonomia**           SDT (Deci & Ryan); PENS O aluno decide *o quê*,
                          (Ryan et al., 2006)     *quando* e *como* no
                                                  sandbox; múltiplos
                                                  caminhos válidos

  **Competência**         SDT; Flow               Curva suave + feedback
                                                  claro → sensação
                                                  crescente de domínio

  **Pertencimento**       SDT                     Autoria compartilhável;
                                                  modo colaborativo
                                                  (futuro)

  **Curiosidade**         Malone & Lepper (1987)  Mistérios do mundo, \"e
                                                  se...?\", telegrafia de
                                                  eventos

  **Descoberta**          GBL (Gee)               Códex que se preenche;
                                                  espécies e conceitos a
                                                  revelar

  **Exploração**          Sandbox / flow          Liberdade de vasculhar o
                                                  planeta e testar ideias

  **Experimentação**      IBL; Koster (fun =      Erro seguro (RP-010);
                          aprender)               prever→testar como
                                                  diversão

  **Recompensas           Motivação intrínseca    Conquistas por
  significativas**                                *insight*/feito
                                                  científico, não por grind

  **Sensação de           Flow; GameFlow          Eras, árvores
  progresso**             (Sweetser & Wyeth,      científica/tecnológica,
                          2005)                   códex

  **Narrativa emergente** Design centrado no      A saga do planeta é
                          jogador                 escrita pelas escolhas do
                                                  aluno
  -------------------------------------------------------------------------

**Fluxo e GameFlow.** O *design* persegue os critérios de **GameFlow**
(concentração, desafio equilibrado, controle, metas claras, feedback,
imersão): metas de missão dão clareza; o Diretor mantém o desafio na
medida; o *core loop* fornece feedback constante; a beleza reativa do
mundo gera imersão. **Motivação intrínseca** é priorizada sobre
extrínseca (evitar pontos vazios), pois é a que sustenta aprendizagem
profunda e duradoura.

### 12. Balanceamento

Equilibrar seis eixos, cada um com **alavancas parametrizáveis** (para
calibração pedagógica por trilha):

  -----------------------------------------------------------------------
  **Eixo**                **Alavancas**           **Risco se
                                                  desbalanceado**
  ----------------------- ----------------------- -----------------------
  **Dificuldade**         Severidade/frequência   Frustração (alto) ou
                          de eventos; nº de       tédio (baixo)
                          variáveis ativas        

  **Tempo de jogo**       Duração de era;         Sessões longas demais
                          velocidade de simulação para EF

  **Quantidade de         Pontos de ação por era; Paralisia (muitas) ou
  decisões**              *cooldowns*             trivialidade (poucas)

  **Frequência de         Taxa base +             Caos (alta) ou
  eventos**               condicionantes do       monotonia (baixa)
                          Diretor                 

  **Velocidade da         Escala de tempo; taxas  Evolução imperceptível
  evolução**              do AG/ABM               ou brusca demais

  **Complexidade          Subsistemas ativos por  Sobrecarga cognitiva
  científica**            trilha/era              (Sweller)
  -----------------------------------------------------------------------

**Métodos de validação do balanceamento (durante o desenvolvimento):**

-   **Telemetria/learning analytics** (RF-071): taxas de conclusão,
    abandono, tempo por era, uso de dicas → detectam picos e vales.

-   **Playtesting** com a faixa etária-alvo (personas P1/P2) e
    observação estruturada.

-   **A/B testing** de parâmetros (proposta §17) --- comparar
    configurações de dificuldade/eventos.

-   **Métricas de fluxo/motivação** (IMI, escala de fluxo, GameFlow) e
    **engajamento** (sessão, retorno).

-   **Auto-tuning pelo Diretor** dentro de faixas seguras + **revisão de
    especialista** (científica e pedagógica) para preservar
    plausibilidade e objetivo.

-   **Curva de aprendizagem** (ganho de Hake) por versão --- o
    balanceamento certo é o que maximiza aprendizado *e* engajamento
    simultaneamente.

### 13. Interface e experiência do usuário (UX)

**Princípio central:** *mostrar, não contar.* Para o Ensino Fundamental
(personas P1/P2, RNF-022), a interface é **visual, tátil e enxuta** ---
o planeta é o protagonista; o texto é mínimo; ícones e cores comunicam
estado. (Acessibilidade: RNF-014--020.)

┌──────────────────────── ECOSFERA ─ Era: Diversificação Biológica
─────────────────────┐

│ 24°C O2 19% pH 8,1 Biodiv ▓▓▓▓▁ Prosperidade ▓▓▓▁▁ │ ← HUD
(indicadores-chave)

│ │

│ ╭──────────────────────────╮ \[Camadas ▾\] │

│ │ (planeta 3D) │ ▸ Temperatura │

│ \[Ações 3/5\] │ orbitar · zoom · focar │ ▸ Biomas │

│ Reflorestar │ │ ▸ População │

│ Industrializar ╰──────────────────────────╯ ▸ Recursos │

│ Pesquisar │

│ Observar \[gráfico: O2 ao longo das eras\] \"Alga floresceu!\" │

│ │

│ \[(tempo) Avançar tempo ▶\] \[ Missão: atingir 3 biomas\] \[ Tutor: por que
caiu o O2?\] │

└────────────────────────────────────────────────────────────────────────────────────────┘

**Diretrizes de UX:**

-   **HUD:** poucos indicadores essenciais, sempre visíveis, com ícone +
    cor + valor (redundância para daltonismo, RNF-015).

-   **Visualização do planeta:** central, manipulável
    (orbitar/zoom/focar, RF-053); mudanças de estado refletem
    **imediatamente** (feedback visual).

-   **Painéis e camadas:** dados sob demanda (progressive disclosure)
    --- mapas de calor (temperatura, população), gráficos de série
    temporal (RF-021/054); nada de sobrecarregar a tela inicial.

-   **Notificações:** curtas, com ícone, acionáveis (\"Alga floresceu!
    Investigar\") --- telegrafam eventos e convidam à observação.

-   **Tutoriais:** *onboarding* guiado e **incorporado ao jogo**
    (aprender fazendo, não lendo manuais); dicas *just-in-time*.

-   **Feedback visual:** toda ação tem resposta visível e/ou sonora; o
    tutor aparece contextualmente, sem bloquear o fluxo.

-   **Acessibilidade:** navegação por teclado (RNF-017), leitor de tela
    com descrições textuais do estado do planeta (RNF-018), alto
    contraste e fontes ajustáveis (RNF-016/020), alvos de toque grandes.

-   **Carga cognitiva:** um conceito/painel novo por vez (Sweller);
    linguagem simples e apropriada à idade (RP-003/006).

### 14. Fundamentação em Game Design

  -----------------------------------------------------------------------------------
  **Decisão de design**   **Base teórica**        **Como sustenta o projeto**
  ----------------------- ----------------------- -----------------------------------
  Conteúdo emerge das     **MDA** (Hunicke,       Estética/aprendizagem nascem das
  mecânicas               LeBlanc & Zubek, 2004); regras, não de quizzes
                          Bogost (2007)           

  \"Diversão é aprender\" **Koster** (2013, *A    Legitima o serious game: dominar o
                          Theory of Fun*)         sistema É o prazer

  Jogo significativo      **Salen & Zimmerman**   Trade-offs com consequências
  (ação↔consequência      (2004, *Rules of Play*) legíveis = *meaningful play*
  clara)                                          

  Lentes de design /      **Schell** (2008, *Art  Guia a avaliação multidimensional
  iteração                of Game Design*)        do design

  Fluxo e desafio         **Csikszentmihalyi**    Curva de dificuldade e Diretor
  equilibrado             (1990); **GameFlow**    mantêm o canal de fluxo
                          (Sweetser & Wyeth,      
                          2005)                   

  Motivação intrínseca    **Malone & Lepper**     Autonomia/competência/curiosidade
                          (1987); **Deci & Ryan** guiam o engajamento
                          (SDT); **Ryan et al.**  
                          (2006, PENS)            

  Aprendizagem em jogos   **Gee** (2003);         Princípios de GBL (identidade,
                          **Squire** (2011);      agência, *just-in-time*)
                          **Plass et al.** (2015) 

  Simulação de sistemas   **Wilensky & Rand**     Precedentes de mundos vivos e
  educacional             (2015); tradição        evolução como jogo
                          *SimEarth*/*Spore*      
                          (Maxis)                 

  Emergência e sistemas   **Holland** (1998);     Base do \"mundo que surpreende\" e
  complexos               **Meadows** (2008)      do pensamento sistêmico
  -----------------------------------------------------------------------------------

**Referências de Game Design adicionais** (além das já citadas na
proposta §20):

-   HUNICKE, R.; LeBLANC, M.; ZUBEK, R. MDA: A Formal Approach to Game
    Design and Game Research. *AAAI Workshop*, 2004.

-   KOSTER, R. *A Theory of Fun for Game Design*. 2. ed. O\'Reilly,
    2013.

-   MALONE, T.; LEPPER, M. Making learning fun. In: *Aptitude, Learning
    and Instruction*, 1987.

-   RYAN, R.; RIGBY, C.; PRZYBYLSKI, A. The motivational pull of video
    games: a self-determination theory approach. *Motivation and
    Emotion*, 2006.

-   SALEN, K.; ZIMMERMAN, E. *Rules of Play: Game Design Fundamentals*.
    MIT Press, 2004.

-   SCHELL, J. *The Art of Game Design: A Book of Lenses*. Morgan
    Kaufmann, 2008.

-   SWEETSER, P.; WYETH, P. GameFlow: a model for evaluating player
    enjoyment in games. *ACM Computers in Entertainment*, 2005.

### 15. Entregáveis e recomendações

### 15.1 Entregáveis desta etapa (contidos no GDD)

22. Visão geral do gameplay (§1) · 2. Core Loop (§2) · 3. Mecânicas
    principais (§3) · 4. Sistema de trade-offs (§4) · 5. Economia de
    ações (§5) · 6. Curva de dificuldade (§6) · 7. Narrativa das eras
    (§7) · 8. Sistema de progressão (§8) · 9. Sistema de eventos (§9)
    · 10. Papel da IA no gameplay (§10) · 11. Estratégias de motivação
    (§11) · 12. Plano de balanceamento (§12) · 13. Diretrizes de UX
    (§13) · 14. Fundamentação de Game Design (§14) · 15. Recomendações
    (abaixo).

### 15.2 Recomendações para a próxima etapa (arquitetura, software e IA)

-   *Construir um* vertical slice **de** uma era completa *(ex.:
    \"Diversificação Biológica\") atravessando todo o* core loop ---
    valida diversão, desempenho (RSK-02) e o tutor (RSK-03) antes de
    escalar.

-   *Especificar o contrato do* tick *de simulação (entrada de estado →
    subsistemas → saída de* delta*) e a fronteira determinístico×IA*
    (§10) diretamente no design da arquitetura.

-   **Definir esquemas de dados** para: estado do planeta (Mongo),
    **eventos** (catálogo + condicionantes), **economia de ações**
    (configuração parametrizável por trilha) e **telemetria** --- esta
    última **alinhada à Matriz de Evidências** (§8 da Modelagem) para o
    stealth.

-   **Formalizar a política do Diretor** (regras/limites; RL contido)
    preservando plausibilidade científica.

-   *Traduzir os* wireframes *de UX* (§13) em componentes React/Three.js
    (RF-051--058), com acessibilidade desde o início.

-   **Parametrizar o balanceamento** (§12) em arquivos de configuração
    versionados, habilitando A/B testing e ajuste pedagógico sem
    recompilar.

-   **Mapear cada mecânica → RF → evidência → competência** na matriz de
    rastreabilidade (recomendada no ERS §16.2), fechando o elo game
    design ↔ pedagogia ↔ código.

> ***Consistência garantida:** todas as mecânicas deste GDD derivam de
> requisitos (RF-011--078) e servem a objetivos pedagógicos (M1--M10,
> BNCC, competências), com diversão e aprendizagem projetadas como **a
> mesma coisa**, não como camadas separadas.*

*Fim do Game Design Document conceitual. Pronto para orientar a
implementação do jogo, a arquitetura de software e o sistema de IA,
mantendo coerência com a proposta, o resumo executivo, o ERS e a
Modelagem Pedagógica.*

# PARTE IV — Engenharia de Requisitos


## 8 Especificação de Requisitos (ERS)

### 1. Objetivos da Engenharia de Requisitos

**Objetivos desta etapa.** Transformar a visão da proposta ECOSFERA em
um conjunto de requisitos **claros, verificáveis, priorizados e
rastreáveis**, que sirva de contrato técnico-pedagógico entre as partes
e de fundação para a arquitetura, o modelo de dados, a implementação, os
testes e a validação com estudantes. Especificamente: (i) identificar
*stakeholders* e suas necessidades; (ii) especificar o que o sistema
deve fazer (funcional), como deve se comportar (não funcional) e o que
deve ensinar (pedagógico); (iii) alinhar funcionalidades às competências
da BNCC; (iv) estabelecer prioridades, dependências e riscos.

**Importância do levantamento de requisitos.** É a etapa de maior
alavancagem de custo de todo o ciclo: erros de requisito descobertos em
produção custam ordens de grandeza mais do que se corrigidos agora. Num
produto que é simultaneamente *software*, *jogo* e *instrumento
pedagógico regulado* (BNCC, LGPD, público infantojuvenil), a ambiguidade
de requisitos é especialmente perigosa --- ela se propaga para a
modelagem científica, para a avaliação de aprendizagem e para a
conformidade legal.

**Impacto sobre arquitetura, desenvolvimento e validação.**

-   *Arquitetura:* a decisão de simulação **híbrida cliente-servidor**
    (proposta, §11.1), a separação **Java/plataforma × Python/IA** e a
    persistência poliglota nascem de requisitos de desempenho,
    escalabilidade e explicabilidade --- precisam estar formalizados
    aqui.

-   *Desenvolvimento:* requisitos priorizados por MoSCoW definem o MVP e
    a ordem de implementação (mapa de dependências).

-   *Validação:* cada requisito recebe **critérios de aceitação**, e
    cada objetivo de aprendizagem recebe **evidências mensuráveis** ---
    habilitando o desenho quase-experimental previsto na proposta (§14,
    §17).

### 2. Stakeholders

  ----------------------------------------------------------------------------------
  **Stakeholder**     **Responsabilidades**   **Necessidades**    **Expectativas**
  ------------------- ----------------------- ------------------- ------------------
  **Aluno (EF II /    Criar e evoluir seu     Interface simples,  Aprender
  Médio / Técnico)**  planeta; tomar          divertida,          \"brincando\";
                      decisões; refletir      acessível; feedback sentir autoria e
                                              compreensível       progresso

  **Professor         Ancorar atividades a    Painel claro;       Ganhar tempo;
  (Ciências,          objetivos; acompanhar;  alinhamento à BNCC; enxergar
  Matemática etc.)**  mediar                  baixo esforço de    aprendizagem real;
                                              preparo             engajar a turma

  **Coordenador       Garantir alinhamento    Relatórios          Evidência de
  pedagógico**        curricular; apoiar      agregados;          impacto;
                      docentes                conformidade BNCC;  padronização entre
                                              trilhas por nível   turmas

  **Diretor / gestor  Decidir adoção;         Custo previsível;   ROI pedagógico e
  escolar**           orçamento; comunicação  segurança/LGPD;     de imagem; risco
                      institucional           diferenciação da    controlado
                                              escola              

  **Escola / rede de  Prover infraestrutura;  Integração (LTI),   Solução estável,
  ensino**            contratar; integrar ao  operação simples,   escalável e
                      LMS                     suporte             conforme

  **Responsáveis      Consentir tratamento de Transparência;      Uso ético dos
  (pais)**            dados do menor;         privacidade;        dados; benefício
                      acompanhar              segurança do filho  educacional real

  **Administrador do  Gerir contas, turmas,   Ferramentas de      Baixa manutenção;
  sistema (TI         integrações,            administração;      deploy simples
  escola)**           infraestrutura          observabilidade;    (Docker)
                                              documentação        

  **Pesquisadores**   Validar eficácia;       *Learning           Dados confiáveis e
                      publicar; melhorar      analytics*; dataset éticos; base para
                      modelos                 anonimizado;        P&D
                                              reprodutibilidade   

  **Equipe técnica    Construir, testar,      Requisitos claros;  Especificação
  (dev/IA/design)**   operar o sistema        arquitetura         estável; débito
                                              definida; CI/CD     técnico controlado

  **Especialistas de  Validar plausibilidade  Parâmetros          Rigor científico
  conteúdo            científica dos modelos  ajustáveis; canal   compatível com
  (Ciências)**                                de revisão          simplificação
                                                                  didática

  **Órgãos de fomento Avaliar mérito e        Documentação,       Inovação, impacto
  / avaliadores de    viabilidade para        métricas, plano de  e viabilidade
  edital**            financiamento           validação           demonstráveis
  *(Recomendação)*                                                
  ----------------------------------------------------------------------------------

> ***Justificativa (Recomendação):** incluí responsáveis, especialistas
> de conteúdo e órgãos de fomento como stakeholders de primeira classe.
> Os dois primeiros são exigidos pela natureza do público (menores) e
> pela necessidade de validade científica; o terceiro reflete o
> posicionamento de \"projeto financiável\" destacado no resumo
> executivo --- decisões de requisito (métricas, dataset,
> reprodutibilidade) atendem diretamente a esse público.*

### 3. Personas

P1 --- Lucas, 12 anos --- Aluno do Ensino Fundamental II

-   **Perfil:** 7º ano, escola pública, joga no celular e no Chromebook
    da escola. Curioso, dispersa fácil em aula expositiva.

-   **Objetivos:** se divertir, \"ganhar\", mostrar seu planeta aos
    colegas.

-   **Dificuldades:** textos longos, termos técnicos, instruções
    ambíguas; frustra-se com erro sem explicação.

-   **Necessidades:** interface visual e tátil, feedback imediato e
    simples, metas curtas, tutor que explique \"com palavras dele\".

-   **Nível tecnológico:** alto como usuário (apps/jogos), baixo como
    conceitos técnicos.

P2 --- Sofia, 16 anos --- Aluna do Ensino Médio

-   **Perfil:** 2ª série, foco em vestibular/ENEM, gosta de entender \"o
    porquê\".

-   **Objetivos:** aprender de forma que ajude nas provas; conectar
    disciplinas.

-   **Dificuldades:** falta de tempo; conteúdos abstratos (ciclos,
    energia) sem aplicação.

-   **Necessidades:** rigor um pouco maior, gráficos, ligação explícita
    com o conteúdo escolar e com a BNCC/ENEM.

-   **Nível tecnológico:** alto.

P3 --- Professora Marina --- Docente de Ciências

-   **Perfil:** 38 anos, 12 anos de sala de aula, 3 turmas grandes,
    pouco tempo de preparo.

-   **Objetivos:** engajar a turma, cumprir o currículo, avaliar sem se
    sobrecarregar.

-   **Dificuldades:** turmas heterogêneas; difícil evidenciar
    aprendizagem; receio de tecnologia complexa.

-   **Necessidades:** montar uma atividade em minutos, atrelada a uma
    habilidade BNCC; painel que mostre quem entendeu o quê; material de
    apoio.

-   **Nível tecnológico:** médio; usa LMS e apresentações, evita
    ferramentas que exijam configuração pesada.

P4 --- Professor Rafael --- Docente de Matemática

-   **Perfil:** 45 anos, gosta de dados e modelos, cético quanto a
    \"jogos educativos\" genéricos.

-   **Objetivos:** usar o planeta para ensinar funções, proporção,
    estatística e leitura de gráficos.

-   **Dificuldades:** ver relevância matemática real; evitar que o jogo
    vire só \"entretenimento\".

-   **Necessidades:** acesso às séries numéricas do planeta, exportação
    de dados, atividades quantitativas.

-   **Nível tecnológico:** médio-alto.

P5 --- Coordenadora Beatriz --- Coordenação Pedagógica

-   **Perfil:** 50 anos, responsável por alinhamento curricular e
    formação docente.

-   **Objetivos:** garantir cobertura da BNCC; comparar resultados entre
    turmas; justificar a adoção.

-   **Dificuldades:** consolidar evidências; formar professores;
    padronizar o uso.

-   **Necessidades:** relatórios agregados, matriz BNCC, trilhas por
    nível, indicadores de impacto.

-   **Nível tecnológico:** médio.

P6 --- Administrador Carlos --- TI da Escola

-   **Perfil:** 34 anos, cuida de rede, Chromebooks e do LMS da escola.

-   **Objetivos:** implantar e manter com esforço mínimo; garantir
    segurança e LGPD.

-   **Dificuldades:** hardware modesto, internet instável, muitas
    ferramentas para manter.

-   **Necessidades:** deploy simples (contêineres), integração LTI,
    funcionamento com hardware fraco/offline parcial, documentação e
    observabilidade.

-   **Nível tecnológico:** alto.

P7 --- Helena --- Responsável/Mãe *(Recomendação)*

-   **Perfil:** 41 anos, mãe do Lucas; preocupada com tempo de tela e
    privacidade.

-   **Objetivos:** que o filho aprenda com segurança; entender o que a
    escola coleta.

-   **Dificuldades:** desconfia de coleta de dados; pouco tempo.

-   **Necessidades:** consentimento claro (LGPD), transparência,
    conteúdo apropriado à idade, controle.

-   **Nível tecnológico:** médio.

> ***Justificativa (Recomendação):** a persona do responsável é
> indispensável porque o consentimento e a transparência (LGPD) são
> requisitos legais para o público infantojuvenil; ela orienta
> requisitos de privacidade, comunicação e apropriação etária do
> conteúdo.*

### 4. Requisitos Funcionais (por módulo)

Cada requisito traz **Descrição**, **Prioridade (MoSCoW)**, **Critérios
de aceitação** (resumidos) e **Dependências**. As tabelas por módulo
constituem, em conjunto, o **Catálogo de Requisitos Funcionais**.

### 4.1 Módulo Cadastro, Contas e Gestão de Acesso

  --------------------------------------------------------------------------------------
  **ID**         **Descrição**         **Prior.**     **Critérios de      **Depend.**
                                                      aceitação**         
  -------------- --------------------- -------------- ------------------- --------------
  RF-001         Cadastrar             M              Escola criada com   ---
                 instituição/escola                   dados básicos;      
                                                      admin inicial       
                                                      gerado              

  RF-002         Cadastrar e gerir     M              Papel atribuído;    RF-001
                 usuários com papéis                  permissões (RBAC)   
                 (aluno, professor,                   aplicadas por papel 
                 coordenador, admin)                                      

  RF-003         Autenticar usuário    M              Credencial válida   RF-002
                 (login)                              concede sessão;     
                                                      inválida é negada e 
                                                      registrada          

  RF-004         Autorizar ações por   M              Cada ação verifica  RF-003
                 papel (RBAC)                         permissão; acesso   
                                                      indevido bloqueado  

  RF-005         Criar turmas e        M              Turma com alunos e  RF-002
                 vincular                             docente; aluno vê   
                 alunos/professor                     só sua(s) turma(s)  

  RF-006         Recuperar/redefinir   S              Fluxo seguro de     RF-003
                 senha                                redefinição por     
                                                      e-mail/admin        

  RF-007         Cadastrar responsável M              Vínculo             RF-002
                 e vincular a aluno                   responsável↔aluno   
                 menor                                registrado          

  RF-008         Registrar             M              Sem consentimento   RF-007
                 **consentimento do                   válido, conta do    
                 responsável** (LGPD)                 menor fica restrita 
                 no cadastro de menor                                     

  RF-009         Integrar turmas via   S              Turma/alunos        RF-005
                 **LTI 1.3** (LMS)                    importados do LMS;  
                                                      SSO funcional       

  RF-010         Gerir perfil e        S              Preferências        RF-002
                 preferências (idioma,                persistem e afetam  
                 acessibilidade)                      a UI                
  --------------------------------------------------------------------------------------

### 4.2 Módulo Simulação (Motor do Planeta)

  -------------------------------------------------------------------------------------
  **ID**         **Descrição**           **Prior.**     **Critérios de   **Depend.**
                                                        aceitação**      
  -------------- ----------------------- -------------- ---------------- --------------
  RF-011         Criar planeta           M              Planeta          RF-005
                 parametrizando                         persistido com   
                 dimensões (astronômica,                parâmetros       
                 física, geológica,                     válidos; valores 
                 química, hidrológica,                  fora de faixa    
                 biológica)                             bloqueados       

  RF-012         IA sugerir valores      M              Ao gerar         RF-011, RF-031
                 plausíveis e **alertar                 combinação       
                 combinações inviáveis**                inviável,        
                 na criação                             sistema avisa e  
                                                        explica          

  RF-013         Avançar o tempo em      M              Estado evolui de RF-011
                 escalas ajustáveis (era                forma            
                 geológica↔ecológica)                   determinística   
                                                        por *seed*;      
                                                        velocidade       
                                                        ajustável        

  RF-014         Simular subsistemas     M              Alterar variável RF-013
                 acoplados (clima,                      de um subsistema 
                 geologia, oceanos,                     propaga aos      
                 química, ecologia,                     acoplados        
                 evolução)                                               

  RF-015         Salvar, carregar e      M              Recarregar       RF-011
                 versionar (checkpoint)                 reproduz o       
                 o estado do planeta                    estado salvo     
                                                        fielmente        

  RF-016         Rebobinar/reproduzir a  S              Aluno navega por RF-015
                 linha do tempo (replay)                eras anteriores  
                                                        e observa a      
                                                        evolução         

  RF-017         Aplicar intervenções do M              Ação consome     RF-014
                 jogador limitadas por                  orçamento;       
                 \"pontos de ação\"                     efeito aplicado; 
                                                        sem orçamento,   
                                                        bloqueada        

  RF-018         Materializar            M              Cada ação        RF-017
                 **trade-offs**: toda                   registra         
                 ação gera consequência                 efeitos + e −    
                 positiva e negativa                    rastreáveis      

  RF-019         Gerar, aplicar e        M              Evento altera    RF-014
                 **propagar eventos                     variáveis e      
                 aleatórios**                           cascateia pelos  
                 condicionados ao estado                acoplamentos     

  RF-020         Diretor de dificuldade  C              Ritmo de eventos RF-019
                 ajustar                                se adapta ao     
                 frequência/severidade                  desempenho do    
                 de eventos                             aluno            

  RF-021         Exibir séries temporais M              Gráficos         RF-014
                 e indicadores do                       atualizam        
                 planeta (temperatura,                  conforme a       
                 O2, população...)                      simulação;       
                                                        exportáveis      

  RF-022         Professor definir       S              Aluno inicia no  RF-011, RF-041
                 cenário/desafio inicial                cenário          
                 e parâmetros                           definido;        
                 habilitados por trilha                 parâmetros fora  
                                                        da trilha        
                                                        ocultos          

  RF-023         Garantir                S              Mesma *seed* +   RF-013
                 *reprodutibilidade por*                mesmas ações ⇒   
                 seed (comparação em                    mesmo resultado  
                 turma)                                                  
  -------------------------------------------------------------------------------------

### 4.3 Módulo Inteligência Artificial

  -----------------------------------------------------------------------------------------------------
  **ID**         **Descrição**               **Prior.**     **Critérios de aceitação**   **Depend.**
  -------------- --------------------------- -------------- ---------------------------- --------------
  RF-031         Motor evolutivo (AG) das    M              Populações evoluem conforme  RF-014
                 espécies: mutação, seleção,                pressão ambiental; genoma    
                 especiação, extinção                       inspecionável                

  RF-032         ABM ecológico: dinâmica     M              Padrões (biodiversidade,     RF-014
                 populacional e cadeias                     predador-presa) emergem das  
                 tróficas                                   regras                       

  RF-033         Tutor generativo (LLM) que  M              Após cada era/ação, gera     RF-021
                 **explica a causalidade**                  explicação correta e         
                 dos resultados                             apropriada à idade           

  RF-034         Ancorar o tutor por **RAG** M              Explicações citam dados      RF-033
                 ao estado real e ao                        reais da simulação; sem      
                 currículo (reduzir                         invenção factual             
                 alucinação)                                                             

  RF-035         Personalizar dificuldade,   S              Dicas variam conforme        RF-033, RF-061
                 dicas e ritmo ao aluno                     desempenho e nível           

  RF-036         Conselheiros/agentes        C              Aluno consulta               RF-033
                 (papéis científicos) como                  \"biólogo/climatologista\" e 
                 *scaffolding*                              recebe orientação            

  RF-037         **Filtros de segurança de   M              Saída do LLM filtrada;       RF-033
                 conteúdo** apropriados a                   conteúdo impróprio bloqueado 
                 menores                                    e registrado                 

  RF-038         Gerar relatório explicativo S              Relatório resume decisões,   RF-033
                 por era (para aluno e                      efeitos e conceitos          
                 professor)                                 científicos                  

  RF-039         Expor a **cadeia causal**   M              Aluno acessa \"por que isso  RF-014, RF-033
                 de cada resultado (IA                      aconteceu\" com passos       
                 explicável)                                rastreáveis                  

  RF-040         Executar LLM                S              Inferência funciona sem      RF-033
                 **localmente/on-premise**                  serviço externo; dados não   
                 (privacidade/offline)                      saem da rede                 
  -----------------------------------------------------------------------------------------------------

### 4.4 Módulo Interface / Visualização 3D

  ---------------------------------------------------------------------------------
  **ID**         **Descrição**        **Prior.**     **Critérios de  **Depend.**
                                                     aceitação**     
  -------------- -------------------- -------------- --------------- --------------
  RF-051         Renderizar planeta   M              Planeta         RF-011
                 3D interativo no                    exibido;        
                 navegador                           interação       
                                                     fluida no       
                                                     hardware-alvo   

  RF-052         Alterar              M              Mudança de      RF-014, RF-051
                 dinamicamente                       estado reflete  
                 atmosfera, oceanos,                 visualmente em  
                 vegetação, espécies,                tempo hábil     
                 cidades, relevo,                                    
                 clima e desastres                                   

  RF-053         Navegação de câmera  M              Controles       RF-051
                 (orbitar, zoom,                     responsivos;    
                 focar região)                       foco em ponto   
                                                     de interesse    

  RF-054         Camadas de           S              Alternar        RF-051, RF-021
                 visualização                        camadas         
                 (temperatura,                       sobrepõe dados  
                 biomas, população,                  ao globo        
                 recursos)                                           

  RF-055         HUD com indicadores  M              HUD mostra      RF-017
                 e painel de                         estado e        
                 ações/intervenções                  permite acionar 
                                                     RF-017          

  RF-056         Efeitos visuais de   S              Evento tem      RF-019, RF-051
                 eventos (erupção,                   representação   
                 meteoro, seca)                      visual clara    

  RF-057         Desempenho           M              Em GPU sem      RF-051
                 adaptativo e                        WebGPU, cai     
                 **fallback WebGL 2**                para WebGL 2    
                                                     sem quebrar     

  RF-058         Modos de             M              Paletas         RF-051,
                 acessibilidade                      alternativas e  RNF-020
                 visual (daltonismo,                 contraste       
                 alto contraste)                     conforme WCAG   

  RF-059         Linha do tempo       C              Arrastar a      RF-016
                 visual navegável                    linha do tempo  
                 (*scrubbing*)                       mostra o        
                                                     planeta na era  
  ---------------------------------------------------------------------------------

### 4.5 Módulo Painel do Professor

  ---------------------------------------------------------------------------------------------------
  **ID**         **Descrição**                 **Prior.**     **Critérios de           **Depend.**
                                                              aceitação**              
  -------------- ----------------------------- -------------- ------------------------ --------------
  RF-061         Gerir turmas, alunos e        M              Professor administra sua RF-005
                 trilhas                                      turma e define a trilha  
                 (Fundamental/Médio/Técnico)                                           

  RF-062         Criar/atribuir desafios       M              Desafio vinculado a      RF-022
                 ancorados a **objetivo BNCC**                habilidade BNCC e a      
                                                              parâmetros               

  RF-063         Acompanhar progresso          M              Painel mostra avanço,    RF-071
                 individual e da turma                        dificuldades e           
                 (dashboard)                                  engajamento              

  RF-064         Visualizar relatórios de      M              Relatório liga           RF-072
                 aprendizagem (*stealth                       evidências a             
                 assessment*)                                 competências             

  RF-065         Comparar planetas/decisões    C              Visualização comparativa RF-063
                 entre alunos                                 de                       
                                                              estratégias/resultados   

  RF-066         Exportar relatórios (PDF/CSV) S              Exportação íntegra e     RF-064
                                                              legível                  

  RF-067         Enviar feedback/mensagens ao  S              Aluno recebe e visualiza RF-063
                 aluno                                        o retorno do professor   

  RF-068         Gerir consentimento e         M              Professor vê status de   RF-008
                 privacidade da turma                         consentimento; respeita  
                                                              restrições               
  ---------------------------------------------------------------------------------------------------

### 4.6 Módulo Avaliação e Aprendizagem

  ------------------------------------------------------------------------------
  **ID**         **Descrição**    **Prior.**     **Critérios de   **Depend.**
                                                 aceitação**      
  -------------- ---------------- -------------- ---------------- --------------
  RF-071         Registrar        M              Ações relevantes RF-017
                 **learning                      são capturadas   
                 analytics**                     com contexto     
                 (telemetria                                      
                 pedagógica das                                   
                 ações)                                           

  RF-072         *Stealth         M              Modelo estima    RF-071
                 assessment*:                    domínio por      
                 inferir                         competência a    
                 competências das                partir de        
                 ações (modelo                   evidências       
                 bayesiano/IRT)                                   

  RF-073         Manter modelo de S              Estimativas      RF-072
                 conhecimento do                 atualizam com    
                 aluno atualizado                novas evidências 

  RF-074         Integrar         S              Testes           RF-002
                 pré/pós-teste                   aplicáveis e     
                 (opcional, para                 vinculados ao    
                 validação)                      perfil do aluno  

  RF-075         Aplicar rubricas S              Ações avaliadas  RF-071
                 de pensamento                   por rubrica;     
                 científico e de                 resultado        
                 *trade-offs*                    registrado       

  RF-076         Mapear           M              Cada evidência   RF-072, §5
                 evidências →                    associa-se a     
                 **habilidades                   habilidade(s) da 
                 BNCC**                          matriz           

  RF-077         Alertar          S              Alerta gerado    RF-073
                 professor sobre                 por limiar       
                 aluno em                        configurável     
                 dificuldade                                      

  RF-078         Exportar         C              Exportação sem   RF-071,
                 **dataset                       dados pessoais   RNF-013
                 anonimizado**                   identificáveis   
                 para pesquisa                                    
  ------------------------------------------------------------------------------

> ***Nota de escopo.** Cidades/civilizações aparecem aqui apenas como
> estado avançado da simulação (era antrópica), coerente com a proposta;
> a modelagem de **civilizações inteligentes** completa permanece em
> Trabalhos Futuros (proposta §19) e **não** integra o MVP.*

### 5. Requisitos Pedagógicos e Alinhamento à BNCC

> ***Aviso de precisão (importante).** As **competências gerais** da
> BNCC abaixo são reproduzidas com fidelidade. Já os **códigos de
> habilidade específicos** (ex.: EF07CI08, EM13CNT301) são apresentados
> como **referência de trabalho** e **devem ser validados linha a linha
> contra o texto oficial da BNCC (2018) e do Complemento de Computação
> (2022)** antes de qualquer submissão a edital ou material oficial ---
> o mapeamento pedagógico (objeto de conhecimento ↔ funcionalidade) é
> robusto; a numeração exata é que exige conferência. (Recomendação de
> processo.)*

### 5.1 Competências Gerais da Educação Básica (BNCC)

As mais mobilizadas por ECOSFERA: **CG2 --- Pensamento científico,
crítico e criativo**; **CG5 --- Cultura digital**; **CG7 ---
Argumentação (com base em fatos, dados e informações confiáveis)**;
**CG10 --- Responsabilidade e cidadania (incl. socioambiental)**. Também
são acionadas CG1 (conhecimento), CG4 (comunicação) e CG9 (empatia e
cooperação, no modo colaborativo futuro).

### 5.2 Estrutura curricular acionada

-   **Ciências da Natureza (EF)** --- unidades temáticas: **Matéria e
    energia**, **Vida e evolução**, **Terra e Universo**.

-   **Ciências da Natureza e suas Tecnologias (EM)** --- competências
    específicas 1--3 (com destaque à **competência 3**: análise,
    investigação e ação sobre situações-problema).

-   **Matemática (EF/EM)** --- proporcionalidade, funções, estatística e
    probabilidade.

-   **Geografia (EF)** --- dinâmica da natureza (relevo, clima,
    recursos).

-   **Computação (Complemento BNCC 2022)** --- pensamento computacional
    e modelagem.

### 5.3 Matriz de alinhamento Funcionalidade ↔ BNCC

  ----------------------------------------------------------------------------------------------------------
  **Funcionalidade (RF)**   **Disciplina**           **Competência**   **Habilidade BNCC   **Objetivo
                                                                       *(código a          pedagógico**
                                                                       validar)***         
  ------------------------- ------------------------ ----------------- ------------------- -----------------
  Criar planeta / zona      Astronomia/Ciências      CG2               Astronomia 9º ano   Compreender
  habitável (RF-011/012)                                               --- sistema solar,  condições
                                                                       ordem de grandeza   planetárias e
                                                                       *(ref.              habitabilidade
                                                                       EF09CI14--17)*      

  Atmosfera, O2/CO2, efeito Química/Física           CG2, CG10         Terra e Universo 7º Relacionar
  estufa (RF-014)                                                      --- composição do   atmosfera,
                                                                       ar, efeito estufa   energia e
                                                                       *(ref.              temperatura
                                                                       EF07CI12--13)*      

  Clima, glaciações,        Geografia/Ciências       CG2, CG10         Terra e Universo 8º Explicar dinâmica
  desertificação                                                       --- clima e         climática e
  (RF-014/019)                                                         previsão *(ref.     feedbacks
                                                                       EF08CI12--16)*      

  Cadeias tróficas e        Ecologia/Biologia        CG2, CG10         Vida e evolução 7º  Analisar fluxo de
  ecossistemas (RF-032)                                                --- teias           energia e
                                                                       alimentares,        equilíbrio
                                                                       impactos *(ref.     
                                                                       EF07CI07--08)*      

  Evolução das espécies     Biologia                 CG2               Vida e evolução 9º  Compreender
  (RF-031)                                                             --- hereditariedade seleção natural,
                                                                       e seleção natural   adaptação,
                                                                       *(ref.              especiação
                                                                       EF09CI09--13)*      

  Geologia: tectônica,      Geografia/Geologia       CG2               Dinâmica da         Entender
  vulcões, erosão (RF-014)                                             natureza (Geografia processos que
                                                                       EF) *(ref. a        moldam o relevo
                                                                       validar)*           

  Ciclos do                 Química/Ciências         CG2, CG10         Ciclos da matéria e Modelar ciclos
  carbono/água/nitrogênio                                              energia *(ref.      biogeoquímicos
  (RF-014)                                                             EF/EM)*             

  Séries temporais e        Matemática/Estatística   CG2, CG5          Estatística e       Ler, interpretar
  gráficos (RF-021)                                                    proporcionalidade   e relacionar
                                                                       *(ref. EF07MA17;    dados
                                                                       EF0xMA ---          
                                                                       gráficos)*          

  Trade-offs e decisões     Meio Ambiente/Sustentab. CG7, CG10         Ação socioambiental Argumentar e
  socioambientais (RF-018)                                             *(ref.              decidir sob
                                                                       EM13CNT301/306; Ed. trade-offs
                                                                       Ambiental           
                                                                       transversal)*       

  Tutor explicando          Transversal              CG2, CG4, CG7     Pensamento          Formular/testar
  causalidade (RF-033/039)                                             científico e        hipóteses;
                                                                       argumentação        justificar com
                                                                                           dados

  Modelagem e parâmetros    Computação               CG5               Pensamento          Modelar sistemas
  (criar/ajustar)                                                      computacional       e abstrair
                                                                       (Complemento 2022)  variáveis
  ----------------------------------------------------------------------------------------------------------

**Como o jogo atende cada habilidade (síntese).** ECOSFERA implementa a
**retórica procedural** (proposta §4.6): o conteúdo não é \"dito\", é
**vivenciado nas regras**. Ao manipular O2/CO2 e observar a temperatura
subir, o aluno *pratica* a relação da habilidade de efeito estufa; ao
ver populações oscilarem em predador-presa, *pratica* teias alimentares;
ao ler as séries temporais para decidir, *pratica* estatística. O tutor
de IA fecha o ciclo transformando a experiência em conceito explícito
(conceituação abstrata de Kolb).

### 5.4 Catálogo de Requisitos Pedagógicos

  --------------------------------------------------------------------------------------
  **ID**            **Requisito             **Prior.**        **Critério de
                    pedagógico**                              verificação**
  ----------------- ----------------------- ----------------- --------------------------
  RP-001            Toda atividade deve ser M                 Desafio exige seleção de
                    ancorável a ≥1                            habilidade (RF-062)
                    habilidade BNCC pelo                      
                    professor                                 

  RP-002            Oferecer trilhas        M                 Parâmetros e formalização
                    diferenciadas por nível                   matemática variam por
                    (EF II, Médio, Técnico)                   trilha

  RP-003            Feedback formativo      M                 Explicações passam em
                    imediato e                                teste de legibilidade por
                    compreensível à faixa                     nível
                    etária                                    

  RP-004            Avaliação embutida sem  M                 Evidências coletadas sem
                    interromper o jogo                        prova adicional (RF-072)
                    (*stealth assessment*)                    

  RP-005            Objetivos de            S                 Cada módulo declara nível
                    aprendizagem mapeados à                   cognitivo-alvo (§6)
                    taxonomia de Bloom                        
                    revisada                                  

  RP-006            Conteúdo e linguagem    M                 Filtro de conteúdo
                    apropriados à idade e                     (RF-037) + revisão
                    livres de conteúdo                        pedagógica
                    sensível                                  

  RP-007            Preservar o papel       M                 Professor configura,
                    mediador do professor                     acompanha e intervém
                    (IA como apoio, não                       (Painel)
                    substituto)                               

  RP-008            Plausibilidade          S                 Checklist de revisão
                    científica validada por                   científica por subsistema
                    especialista de                           
                    conteúdo                                  

  RP-009            Promover pensamento     M                 Explicações conectam ≥2
                    sistêmico e                               disciplinas por era
                    interdisciplinaridade                     
                    explícita                                 

  RP-010            Errar deve ser seguro e M                 Consequências
                    pedagógico (erro →                        reversíveis/analisáveis;
                    aprendizagem, não                         sem \"game over\" punitivo
                    punição)                                  
  --------------------------------------------------------------------------------------

### 6. Objetivos de Aprendizagem (Taxonomia de Bloom revisada)

Para cada módulo: **conhecimentos**, **habilidades**, **competências**,
**resultados esperados** e nível cognitivo-alvo (Lembrar → Entender →
Aplicar → Analisar → Avaliar → Criar).

-   **Criação do Planeta (RF-011/012).**

    -   *Conhecimentos:* variáveis planetárias, zona habitável, relações
        de dependência.

    -   *Habilidades:* configurar parâmetros coerentes; prever
        viabilidade.

    -   *Competências:* pensamento científico; modelagem.

    -   *Bloom:* **Aplicar/Criar**. *Resultado:* o aluno projeta um
        mundo viável justificando escolhas.

-   **Clima e Química Atmosférica (RF-014).**

    -   *Conhecimentos:* efeito estufa, balanço de energia, ciclos.

    -   *Habilidades:* relacionar composição, energia e temperatura;
        interpretar feedbacks.

    -   *Bloom:* **Entender/Analisar**. *Resultado:* explica por que o
        planeta aqueceu/esfriou.

-   **Ecologia e Cadeias Tróficas (RF-032).**

    -   *Conhecimentos:* fluxo de energia, capacidade de suporte,
        predador-presa.

    -   *Habilidades:* analisar equilíbrio; prever efeitos em cascata.

    -   *Bloom:* **Analisar**. *Resultado:* antecipa impacto de
        remover/introduzir espécie.

-   **Evolução (RF-031).**

    -   *Conhecimentos:* variação, seleção natural, adaptação,
        especiação, extinção.

    -   *Habilidades:* relacionar ambiente e aptidão; interpretar
        mudança do genoma.

    -   *Bloom:* **Entender/Analisar**. *Resultado:* explica adaptações
        observadas.

-   **Geologia e Oceanografia (RF-014).**

    -   *Conhecimentos:* tectônica, vulcanismo, erosão, correntes,
        marés.

    -   *Habilidades:* relacionar processos internos/externos ao relevo
        e ao clima.

    -   *Bloom:* **Entender/Aplicar**. *Resultado:* interpreta a
        formação da paisagem.

-   **Intervenções e Trade-offs (RF-017/018).**

    -   *Conhecimentos:* sustentabilidade, custo-benefício, pontos de
        inflexão.

    -   *Habilidades:* decidir sob restrição; argumentar com dados.

    -   *Competências:* CG7, CG10.

    -   *Bloom:* **Avaliar/Criar**. *Resultado:* justifica decisões
        ponderando ganhos e perdas.

-   **Dados e Estatística (RF-021).**

    -   *Conhecimentos:* gráficos, proporção, probabilidade, correlação
        vs. causa.

    -   *Habilidades:* ler séries e fundamentar decisões.

    -   *Bloom:* **Aplicar/Analisar**. *Resultado:* usa evidência
        quantitativa para agir.

-   **Tutoria e Reflexão (RF-033/038).**

    -   *Habilidades:* metacognição; conectar experiência e conceito.

    -   *Bloom:* **Entender/Avaliar**. *Resultado:* verbaliza o que
        aprendeu e por quê.

### 7. Requisitos Técnicos

As decisões abaixo **derivam da proposta** (§11--§13); aqui viram
requisitos verificáveis. Adições de engenharia estão marcadas
**(Recomendação)**.

### 7.1 Plataforma

-   **Web-native**, executando no navegador **sem instalação**
    (proposta, resumo executivo).

-   **Progressive Web App (PWA)** **(Recomendação)** --- adiciona
    instalabilidade, tela cheia e *cache offline* sem sair da via web;
    justifica-se pelo hardware escolar modesto e conectividade instável
    (persona P6) e habilita os requisitos de *offline* (§8).

-   **Responsivo** (desktop, Chromebook, tablet; celular como alvo
    secundário).

-   **Desktop/mobile nativos:** fora de escopo do MVP; reservados a
    Trabalhos Futuros (via Godot, proposta §12.1) caso surja
    necessidade.

### 7.2 Linguagens (justificativa)

-   TypeScript (Node.js/NestJS) --- plataforma educacional:
    autenticação/RBAC, turmas, painel do professor, LTI, relatórios e
    integridade transacional. Competência da equipe e unificação de
    linguagem com o front-end, permitindo compartilhar contratos e
    validação.

-   TypeScript (React/Next.js) --- front-end e visualização 3D
    (Three.js). Inalterado.

-   Python --- simulação científica e IA (todo o ecossistema de
    ML/AG/ABM/LLM). Inalterado. A divisão Node×Python isola
    responsabilidades e reduz acoplamento.

### 7.3 Tecnologias sugeridas

Front: React + Next.js + TypeScript, Three.js (react-three-fiber + drei)
com WebGPU e fallback WebGL 2, TailwindCSS, Recharts/visx/D3, Zustand.
Back plataforma: Node.js + NestJS (REST/OpenAPI, LTI 1.3, RBAC),
TypeORM. Back IA/ciência: Python + FastAPI; DEAP (evolução), Mesa (ABM),
LangGraph + Ollama + sentence-transformers (tutor LLM/RAG),
pgmpy/scikit-learn (avaliação), NumPy/SciPy (simulação), ARQ (jobs),
MLflow (rastreio). Infra: Docker/Docker Compose, Traefik/Nginx (TLS),
GitHub Actions (CI/CD), Prometheus + Grafana, MinIO. Build: pnpm +
Turborepo (TS) e uv (Python).

### 7.4 Banco de dados

-   PostgreSQL (+pgvector) com dois schemas: platform (repositório
    relacional autoritativo --- usuários, turmas, avaliação --- via
    TypeORM) e rag (vetores do RAG --- via Alembic).

-   MongoDB --- estados de simulação (JSON aninhado que evolui por era)
    e logs de eventos.

-   Redis --- cache, pub/sub de WebSocket e Redis Streams (barramento de
    eventos no MVP; NATS a partir do Inc 7 se o volume exigir).

-   SQLite/IndexedDB --- desenvolvimento e implantação local/offline no
    cliente.

### 7.5 Comunicação

-   **REST** --- requisição-resposta e chamadas Java↔Python.

-   **WebSocket** --- *streaming* de estado/*tick* ao cliente
    (atualização do planeta em tempo real).

-   **Fila (Redis/RabbitMQ)** **(Recomendação)** --- *jobs* longos
    (evolução por geração, inferência LLM), evitando bloqueio síncrono.

### 7.6 Requisitos arquiteturais (catálogo)

  ------------------------------------------------------------------------
  **ID**                  **Requisito              **Prior.**
                          técnico/arquitetural**   
  ----------------------- ------------------------ -----------------------
  RT-001                  Arquitetura modular com  M
                          **simulação híbrida      
                          cliente-servidor**       
                          (cliente = render + sim  
                          leve; servidor =         
                          ciência/IA +             
                          persistência)            

  RT-002                  Separação de serviços    M
                          **plataforma (Java)** ×  
                          **IA/ciência (Python)**  
                          com contratos REST       
                          versionados              

  RT-003                  Renderização com         M
                          **WebGPU + fallback      
                          WebGL 2** e qualidade    
                          adaptativa               

  RT-004                  Persistência poliglota   M
                          (Postgres/Mongo/Redis;   
                          SQLite no modo local)    

  RT-005                  Comunicação em tempo     M
                          real via WebSocket para  
                          o estado do planeta      

  RT-006                  Empacotamento e          M
                          implantação por          
                          contêineres (Docker      
                          Compose)                 

  RT-007                  Integração LMS via **LTI S
                          1.3**                    

  RT-008                  Inferência de LLM        S
                          **local/on-premise**     
                          habilitável              
                          (privacidade/offline)    

  RT-009                  Reprodutibilidade por    S
                          *seed* nos serviços de   
                          simulação                

  RT-010                  Observabilidade          S
                          (métricas de simulação,  
                          latência de IA,          
                          engajamento)             
  ------------------------------------------------------------------------

### 8. Requisitos Não Funcionais

### 8.1 Catálogo (RNF)

  -------------------------------------------------------------------------------------------------------------------
  **ID**         **Categoria**         **Requisito**                      **Meta/critério**            **Prior.**
  -------------- --------------------- ---------------------------------- ---------------------------- --------------
  RNF-001        Desempenho            Render 3D fluido no hardware-alvo  ≥ 30 FPS em Chromebook       M
                                                                          típico; *fallback*           
                                                                          automático se abaixo         

  RNF-002        Desempenho            Latência de intervenção            ≤ 1 s (p95) para efeitos     M
                                       (ação→feedback visual)             locais                       

  RNF-003        Desempenho            Explicação do tutor (LLM)          ≤ 5 s (p95); *streaming* de  S
                                                                          texto                        

  RNF-004        Escalabilidade        Simulação em tempo real na GPU do  Servidor não escala          M
                                       cliente                            por-aluno na parte real-time 

  RNF-005        Escalabilidade        Suportar turmas concorrentes       ≥ 40 alunos simultâneos por  S
                                                                          instância escolar sem        
                                                                          degradação                   

  RNF-006        Segurança             Autenticação e **RBAC** por papel  Toda ação sensível           M
                                                                          autorizada; testes de acesso 
                                                                          indevido                     

  RNF-007        Segurança             Transporte cifrado (TLS) e dados   HTTPS obrigatório; segredos  M
                                       em repouso protegidos              em cofre                     

  RNF-008        Segurança             Proteção do LLM (injeção de        Filtros de entrada/saída;    M
                                       prompt, conteúdo impróprio)        *guardrails* p/ menores      

  RNF-009        Privacidade/LGPD      **Consentimento do responsável**   Sem consentimento → dados    M
                                       antes de tratar dados de menor     não coletados/uso restrito   

  RNF-010        Privacidade/LGPD      **Minimização de dados** (coletar  Inventário de dados          M
                                       só o necessário)                   justificado por finalidade   

  RNF-011        Privacidade/LGPD      **Anonimização/pseudonimização**   Dataset de pesquisa sem PII  M
                                       para analytics e pesquisa          (RF-078)                     

  RNF-012        Privacidade/LGPD      Direitos do titular (acesso,       Fluxos disponíveis; política S
                                       correção, exclusão) e retenção     de retenção documentada      
                                       definida                                                        

  RNF-013        Privacidade/LGPD      Armazenamento seguro e segregação  Isolamento lógico; controle  M
                                       por escola/turma                   de acesso a dados pessoais   

  RNF-014        Acessibilidade        Conformidade **WCAG 2.1 AA**       Auditoria por página/fluxo   M
                                       (meta)                             crítico                      

  RNF-015        Acessibilidade        **Daltonismo**: paletas seguras e  Informação redundante        M
                                       não depender só de cor             (forma/rótulo) + modos de    
                                                                          paleta                       

  RNF-016        Acessibilidade        **Baixa visão**: fontes            Escala de fonte e contraste  M
                                       adaptáveis, zoom, alto contraste   ajustáveis                   

  RNF-017        Acessibilidade        **Navegação por teclado** completa Todos os fluxos operáveis    M
                                                                          sem mouse                    

  RNF-018        Acessibilidade        **Leitores de tela** (ARIA) na UI; Elementos rotulados;         S
                                       alternativas ao 3D                 descrições textuais do       
                                                                          estado do planeta            

  RNF-019        Acessibilidade        **Legendas** e transcrições em     Todo áudio com               S
                                       áudio/vídeo                        legenda/transcrição          

  RNF-020        Acessibilidade        **Contraste** mínimo conforme WCAG Texto ≥ 4.5:1; elementos ≥   M
                                                                          3:1                          

  RNF-021        Offline               Funcionamento parcial sem conexão  Criar/continuar planeta      S
                                       (ver §8.2)                         local; sincronizar depois    

  RNF-022        Usabilidade           Adequação a **crianças do EF**     Testes de usabilidade com a  M
                                       (ver §8.3)                         faixa etária aprovados       

  RNF-023        Portabilidade         Rodar em navegadores modernos e    Compatível com               M
                                       Chromebooks                        Chrome/Edge/Firefox/Safari   
                                                                          recentes                     

  RNF-024        Manutenibilidade      Código modular, testado e          Cobertura mínima definida;   S
                                       documentado                        ADR para decisões            

  RNF-025        Observabilidade       Métricas, logs e alertas           Painéis de saúde e de        S
                                       (Prometheus/Grafana)               engajamento ativos           

  RNF-026        Internacionalização   Arquitetura i18n (pt-BR base)      Strings externalizadas;      C
                                                                          pronto para novos idiomas    
  -------------------------------------------------------------------------------------------------------------------

### 8.2 Funcionamento Offline (análise)

-   **Deve funcionar offline (parcial):** continuar um planeta já
    carregado, criar/ajustar parâmetros, avançar a simulação client-side
    (render + autômatos), registrar ações localmente. **(Recomendação)**
    viabilizado por PWA + **SQLite/armazenamento local (IndexedDB)**.

-   **Requer conexão (ou LLM local):** tutor generativo pleno, avaliação
    bayesiana no servidor, painel do professor, sincronização entre
    alunos. Com **Ollama on-premise** (RT-008), o tutor pode operar sem
    internet externa.

-   **Sincronização posterior:** ações e checkpoints locais são
    **reconciliados** ao reconectar (estratégia *last-write-wins* por
    planeta, coerente com a proposta §12.5), preservando a linha do
    tempo do aluno.

### 8.3 Usabilidade para crianças do Ensino Fundamental

Requisitos específicos: linguagem simples e ícones; poucos passos por
objetivo; *onboarding* guiado; *feedback* imediato e positivo;
tolerância a erro (RP-010); metas curtas e progresso visível; ausência
de texto denso; controles grandes (toque); sem mecânicas de
pressão/tempo estressantes; nada de conteúdo sensível (RF-037).
*(Fundamenta-se nas personas P1/P7 e no design motivacional ARCS/fluxo
da proposta.)*

### 8.4 Portabilidade, Manutenibilidade, Observabilidade, i18n

-   **Portabilidade:** *core* independente de navegador/SO; contêineres
    tornam a implantação reproduzível (nuvem ou servidor da escola).

-   **Manutenibilidade:** limites claros entre serviços; testes
    automatizados; **ADRs** (Architecture Decision Records)
    **(Recomendação)** para rastrear justificativas.

-   **Observabilidade:** além de infra, **métricas pedagógicas**
    (engajamento, conclusão) e de IA (latência, fidelidade do RAG).

-   **Internacionalização:** externalizar strings desde o início mesmo
    que só pt-BR seja lançado --- barato agora, caro depois; habilita
    expansão internacional citada no resumo executivo.

### 9. Plano de Levantamento --- Entrevistas

Como não há entrevistas reais nesta fase, define-se um **plano de
elicitação** para validar e refinar os requisitos com usuários reais
antes/durante o desenvolvimento.

**Método:** entrevistas semiestruturadas (30--45 min) + questionários
(fechados) para escala; amostragem por conveniência em 2--3 escolas
parceiras; registro com consentimento; análise temática das abertas e
estatística descritiva das fechadas. **Ética:** para menores,
consentimento dos responsáveis e assentimento do aluno.

> *Escalas fechadas usam **Likert 1--5** (1 = discordo totalmente /
> nada; 5 = concordo totalmente / muito).*

### 9.1 Professores

*Abertas:* Quais são hoje suas maiores dificuldades para ensinar
ciências de forma integrada? Como você percebe o engajamento da turma?
Como avalia aprendizagem hoje? O que faria você adotar (ou abandonar)
uma ferramenta nova? Que conteúdos são mais difíceis de ensinar?
*Fechadas (Likert):* Tenho tempo para preparar atividades digitais. Meus
alunos se engajam com aulas expositivas. Confio em ferramentas de IA
para apoio pedagógico. Preciso de alinhamento explícito à BNCC. Um
painel de aprendizagem automático seria útil. *Investiga:* dificuldades,
expectativas, conteúdos prioritários, metodologias, avaliação, interesse
por IA.

### 9.2 Coordenadores pedagógicos

*Abertas:* Como garantem cobertura da BNCC? Como comparam resultados
entre turmas? O que consideram evidência de aprendizagem? Que barreiras
existem para adotar tecnologia? Como formam os professores? *Fechadas:*
Relatórios agregados por competência ajudariam a coordenação. A
padronização entre turmas é um desafio. Precisamos de evidências para
justificar investimentos. Trilhas por nível seriam úteis.

### 9.3 Diretores / gestores

*Abertas:* Que critérios definem a adoção de uma solução? Quais
preocupações sobre custo, segurança e LGPD? Como a escola se diferencia
hoje? Que retorno esperam (pedagógico e institucional)? *Fechadas:*
Custo previsível é decisivo. Conformidade com LGPD é pré-requisito.
Inovação em IA agrega valor à marca da escola. Suporte e estabilidade
são críticos.

### 9.4 Especialistas em Educação / conteúdo

*Abertas:* Quais simplificações científicas são aceitáveis sem induzir
concepções errôneas? Que habilidades são mais bem trabalhadas por
simulação? Como evitar que o jogo vire só entretenimento? Como avaliar
pensamento científico? *Fechadas:* Simulações favorecem pensamento
sistêmico. É viável alinhar mecânicas de jogo à BNCC. *Stealth
assessment* é confiável como evidência complementar.

### 9.5 Alunos

*Abertas (linguagem simples):* O que te deixa animado para aprender? O
que te faz desistir de um jogo? O que gostaria de criar no seu planeta?
Quando erra, o que ajudaria a entender? *Fechadas:* Gosto de aprender
jogando. Prefiro descobrir a ouvir explicação. Gosto de mostrar o que
criei. Prefiro metas curtas.

### 9.6 Pais / responsáveis

*Abertas:* Que preocupações têm sobre tempo de tela e dados do seu
filho? O que esperam de uma ferramenta educacional? Que transparência
gostariam de ter? *Fechadas:* Confio em ferramentas escolares digitais.
Quero controle sobre os dados do meu filho. Consentimento claro é
importante. Prefiro conteúdo apropriado à idade.

### 10. Casos de Uso

> *Notação resumida: **A** = atores, **PRÉ** = pré-condições, **FP** =
> fluxo principal, **FA** = fluxos alternativos, **PÓS** =
> pós-condições.*

UC-01 --- Criar planeta (aluno)

-   **A:** Aluno; (apoio) IA de sugestão.

-   **PRÉ:** aluno autenticado, vinculado a turma, consentimento válido.

-   **FP:** 1) aluno inicia criação; 2) ajusta parâmetros por
    dimensão; 3) IA sugere/valida; 4) confirma; 5) planeta é criado e
    persistido; 6) render 3D inicial.

-   **FA:** 3a) combinação inviável → IA alerta e explica; aluno ajusta
    ou prossegue ciente. 5a) falha de persistência → salva rascunho
    local (offline) e sincroniza depois.

-   **PÓS:** planeta disponível para simulação.

UC-02 --- Avançar era / simular (aluno)

-   **A:** Aluno; motor de simulação.

-   **PRÉ:** planeta existente.

-   **FP:** 1) aluno define velocidade e avança; 2) subsistemas evoluem
    acoplados; 3) estado atualiza no 3D e nos gráficos; 4) checkpoint
    gravado.

-   **FA:** 2a) evento aleatório dispara → propaga efeitos (UC-05
    relacionado). 1a) offline → simula client-side e enfileira sync.

-   **PÓS:** nova era registrada na linha do tempo.

UC-03 --- Realizar intervenção com trade-off (aluno)

-   **A:** Aluno; motor; tutor de IA.

-   **PRÉ:** pontos de ação disponíveis.

-   **FP:** 1) aluno escolhe ação (ex.: industrializar); 2) sistema
    debita pontos; 3) aplica efeitos + e −; 4) subsistemas
    recalculam; 5) tutor explica a cadeia causal.

-   **FA:** 2a) pontos insuficientes → ação bloqueada com aviso. 5a)
    tutor indisponível (offline sem LLM local) → registra explicação
    para gerar depois.

-   **PÓS:** planeta e indicadores alterados; evidência de avaliação
    registrada.

UC-04 --- Obter explicação do tutor (aluno)

-   **A:** Aluno; tutor LLM+RAG.

-   **PRÉ:** houve mudança de estado ou dúvida.

-   **FP:** 1) aluno pergunta \"por quê?\"; 2) RAG recupera estado
    real + material; 3) LLM gera explicação apropriada à idade; 4)
    filtro de segurança; 5) exibe com passos causais.

-   **FA:** 3a) baixa confiança/ancoragem → tutor pede reformulação ou
    remete ao professor.

-   **PÓS:** compreensão registrada; possível evidência de aprendizagem.

UC-05 --- Enfrentar evento aleatório (aluno)

-   **A:** Aluno; sistema de eventos; diretor de dificuldade.

-   **PRÉ:** simulação em andamento.

-   **FP:** 1) diretor seleciona evento conforme estado; 2) evento
    aplica-se; 3) efeitos cascateiam; 4) aluno responde com
    intervenções; 5) tutor contextualiza.

-   **FA:** 1a) aluno em dificuldade → diretor reduz severidade
    (fluxo/estado).

-   **PÓS:** resiliência do sistema testada; consequências registradas.

UC-06 --- Criar desafio ancorado à BNCC (professor)

-   **A:** Professor.

-   **PRÉ:** professor autenticado; turma e trilha definidas.

-   **FP:** 1) professor cria desafio; 2) seleciona habilidade(s)
    BNCC; 3) define cenário/parâmetros habilitados; 4) atribui à
    turma; 5) sistema disponibiliza aos alunos.

-   **FA:** 2a) sem habilidade selecionada → sistema exige (RP-001).

-   **PÓS:** desafio ativo; evidências passarão a mapear-se à
    habilidade.

UC-07 --- Acompanhar aprendizagem (professor)

-   **A:** Professor; módulo de avaliação.

-   **PRÉ:** alunos jogaram; telemetria coletada.

-   **FP:** 1) professor abre dashboard; 2) vê progresso por
    aluno/competência; 3) recebe alertas de dificuldade; 4) envia
    feedback; 5) exporta relatório.

-   **FA:** 4a) aluno sem consentimento → dados pessoais ocultos,
    respeitando LGPD.

-   **PÓS:** decisões pedagógicas informadas por evidência.

UC-08 --- Cadastrar aluno menor com consentimento (admin/responsável)

-   **A:** Administrador; Responsável.

-   **PRÉ:** escola cadastrada.

-   **FP:** 1) admin registra aluno; 2) sistema solicita consentimento
    ao responsável; 3) responsável consente; 4) conta ativada
    plenamente.

-   **FA:** 3a) sem consentimento → conta restrita (sem coleta de dados
    pessoais/analytics).

-   **PÓS:** conta conforme LGPD.

### 11. Histórias de Usuário (padrão INVEST)

> *Cada história é Independent, Negotiable, Valuable, Estimable, Small,
> Testable. Critérios em **Dado/Quando/Então**.*

**US-01 (Aluno) ---** *Como aluno, quero criar meu planeta ajustando
suas características, para me sentir autor do meu mundo.*

-   Dado que estou na criação, Quando ajusto um parâmetro, Então vejo o
    efeito previsto e posso confirmar. **(RF-011/012)**

**US-02 (Aluno) ---** *Como aluno, quero avançar o tempo e ver meu
planeta evoluir, para aprender observando.*

-   Dado um planeta, Quando avanço uma era, Então o 3D e os gráficos se
    atualizam de forma coerente. **(RF-013/014/021)**

**US-03 (Aluno) ---** *Como aluno, quero que minhas decisões tenham prós
e contras, para entender consequências reais.*

-   Dado pontos de ação, Quando executo uma intervenção, Então vejo
    efeitos positivos e negativos explicados. **(RF-017/018/033)**

**US-04 (Aluno) ---** *Como aluno, quero perguntar \"por quê?\" e
receber uma explicação simples, para compreender a causa.*

-   Dado uma mudança, Quando pergunto, Então recebo explicação
    apropriada à minha idade, baseada no que aconteceu.
    **(RF-033/034/039)**

**US-05 (Aluno) ---** *Como aluno, quero continuar meu planeta mesmo sem
internet, para não perder meu progresso.*

-   Dado que estou offline, Quando ajo, Então as ações são salvas
    localmente e sincronizadas depois. **(RNF-021)**

**US-06 (Professor) ---** *Como professora de Ciências, quero criar uma
atividade ligada a uma habilidade da BNCC em poucos minutos, para
economizar tempo.*

-   Dado o painel, Quando crio um desafio, Então seleciono a habilidade
    e atribuo à turma sem configuração complexa. **(RF-062/RP-001)**

**US-07 (Professor) ---** *Como professor de Matemática, quero acessar
as séries numéricas do planeta, para trabalhar gráficos e proporção.*

-   Dado um planeta, Quando abro os dados, Então posso visualizar e
    exportar as séries. **(RF-021/066)**

**US-08 (Professor) ---** *Como professora, quero um painel que mostre
quem entendeu o quê, para intervir com foco.*

-   Dado que a turma jogou, Quando abro o dashboard, Então vejo domínio
    por competência e alertas. **(RF-063/064/077)**

**US-09 (Coordenador) ---** *Como coordenadora, quero relatórios
agregados por competência, para evidenciar cobertura da BNCC.*

-   Dado várias turmas, Quando gero o relatório, Então vejo indicadores
    agregados alinhados à BNCC. **(RF-064/076)**

**US-10 (Administrador) ---** *Como TI da escola, quero implantar com
Docker e integrar ao LMS, para operar com baixo esforço.*

-   Dado o pacote, Quando faço o deploy, Então o sistema sobe em
    contêineres e importa turmas via LTI. **(RT-006/007)**

**US-11 (Responsável) ---** *Como mãe, quero consentir e entender que
dados são coletados, para proteger meu filho.*

-   Dado o cadastro do menor, Quando reviso o consentimento, Então vejo
    finalidades claras e decido. **(RF-008/RNF-009)**

**US-12 (Aluno com baixa visão) ---** *Como aluno com baixa visão, quero
aumentar fontes e contraste, para usar o jogo com conforto.*

-   Dado as preferências, Quando ativo alto contraste/fonte maior, Então
    a UI se adapta. **(RNF-016/020)**

**US-13 (Pesquisador) ---** *Como pesquisador, quero exportar um dataset
anonimizado, para estudar eficácia com ética.*

-   Dado permissões, Quando exporto, Então recebo dados sem PII.
    **(RF-078/RNF-011)**

**US-14 (Aluno) ---** *Como aluno, quero enfrentar eventos surpresa
(meteoro, seca), para tornar o jogo desafiador e realista.*

-   Dado a simulação, Quando um evento ocorre, Então vejo seus efeitos e
    posso reagir. **(RF-019/056)**

**US-15 (Professor) ---** *Como professor, quero definir a trilha
(EF/Médio/Técnico), para adequar o rigor à turma.*

-   Dado a turma, Quando escolho a trilha, Então parâmetros e
    formalização se ajustam. **(RF-061/RP-002)**

### 12. Priorização (MoSCoW + Kano)

**Escolha do método (justificativa):** adota-se **MoSCoW** como método
principal por ser simples, comunicável a *stakeholders* não técnicos
(professores, gestores) e ideal para delimitar o **MVP**. Complementa-se
com **Kano** em decisões de experiência, para distinguir o que é
*básico* (esperado), *linear* (quanto mais, melhor) e *encantador*
(diferencial). *(Recomendação de processo.)*

### 12.1 Resumo MoSCoW

-   **Must (MVP):** RF-001--005, RF-011--019, RF-021, RF-031--034,
    RF-037, RF-039, RF-051--053, RF-055, RF-057, RF-058, RF-061--064,
    RF-068, RF-071--072, RF-076; RT-001--006;
    RNF-001/002/006/007/008/009/010/011/013/014/015/016/017/020/022/023.

-   **Should:** RF-006/009/010, RF-016/022/023, RF-035/038/040,
    RF-054/056, RF-066/067, RF-073--075/077; RT-007--010;
    RNF-003/005/012/018/019/021/024/025.

-   **Could:** RF-020, RF-036, RF-059, RF-065, RF-078; RNF-026.

-   **Won\'t (por ora):** clientes nativos (Godot), multiplayer, RV/RA,
    civilizações inteligentes plenas --- Trabalhos Futuros (proposta
    §19).

### 12.2 Leitura por Kano (exemplos)

-   **Básicos (insatisfação se faltarem):** privacidade/LGPD
    (RNF-009/010/013), desempenho mínimo (RNF-001), acessibilidade
    essencial (RNF-014/017/020), autenticação (RF-003).

-   **Lineares:** riqueza da simulação/subsistemas (RF-014/031/032),
    qualidade dos gráficos (RF-021), profundidade do painel
    (RF-063/064).

-   **Encantadores (diferenciais):** tutor que explica causalidade
    (RF-033/039), trade-offs vívidos (RF-018), eventos com efeitos
    visuais (RF-056), conselheiros-agentes (RF-036).

### 13. Mapa de Dependências

**Ordem de construção recomendada** (implementar antes → depois):

\[Fundação\]

RF-001 Escola ─► RF-002 Usuários/RBAC ─► RF-003 Login ─► RF-004
Autorização

└─► RF-005 Turmas ─► RF-007/008 Responsável+Consentimento (LGPD)

\[Núcleo de Simulação\]

RF-011 Criar planeta ─► RF-013 Avançar tempo ─► RF-014 Subsistemas
acoplados

│ ├─► RF-021 Séries/indicadores

│ ├─► RF-017 Intervenções ─► RF-018 Trade-offs

│ └─► RF-019 Eventos ─► RF-020 Diretor

└─► RF-015 Checkpoint ─► RF-016 Replay ─► RF-059 Timeline

\[IA\] (depende de RF-014/021)

RF-031 Evolução(AG) ; RF-032 Ecologia(ABM) ; RF-033 Tutor(LLM) ─► RF-034
RAG ─► RF-039 Cadeia causal

RF-037 Filtros ; RF-035 Personalização ; RF-040 LLM local

\[Visualização\] (depende de RF-011/014)

RF-051 Render ─► RF-052 Alteração dinâmica ─► RF-053 Câmera ; RF-055 HUD
; RF-057 Fallback ; RF-058 Acess. visual

\[Professor\] (depende de RF-005/022)

RF-061 Turmas/Trilhas ─► RF-062 Desafios BNCC ─► RF-063 Dashboard ─►
RF-065/066/067

\[Avaliação\] (depende de RF-017/071)

RF-071 Analytics ─► RF-072 Stealth assessment ─► RF-073 Modelo do aluno
─► RF-076 Mapa BNCC ─► RF-078 Dataset

└─► RF-077 Alertas ─► RF-063 (feed dashboard)

**Dependências críticas de caminho:** a cadeia **RF-011 → RF-013 →
RF-014** habilita quase todo o resto (IA, visualização, avaliação); é o
*coração* do MVP e deve ser priorizada. **RF-071 → RF-072** habilita
todo o valor pedagógico do painel. **RF-007/008 (consentimento)** é
bloqueante legal para coletar qualquer dado de menor.

### 14. Riscos e Mitigação

  -----------------------------------------------------------------------------------------------------------
  **ID**      **Risco**             **Categoria**        **Prob.**   **Impacto**   **Mitigação**
  ----------- --------------------- -------------------- ----------- ------------- --------------------------
  RSK-01      Simulação acoplada    Técnico/Científico   Média       Alto          Modelos simples validados
              instável/irrealista                                                  por especialista; testes
              (efeitos absurdos)                                                   de sanidade; *seeds*
                                                                                   reprodutíveis

  RSK-02      Desempenho 3D         Técnico              Média       Alto          Qualidade adaptativa;
              insuficiente em                                                      *fallback* WebGL 2;
              hardware escolar                                                     orçamento de render;
                                                                                   testes em Chromebook real

  RSK-03      LLM alucina ou dá     IA/Pedagógico        Média       Alto          RAG ancorado ao estado;
              explicação                                                           *guardrails*; revisão;
              cientificamente                                                      opção de remeter ao
              errada                                                               professor

  RSK-04      Conteúdo impróprio    Ético/Legal          Baixa       Muito alto    Filtros de entrada/saída;
              gerado para menores                                                  listas de bloqueio; LLM
                                                                                   local controlado;
                                                                                   auditoria

  RSK-05      Não conformidade LGPD Legal                Média       Muito alto    Consentimento no cadastro;
              (consentimento,                                                      minimização; anonimização;
              retenção)                                                            DPO/assessoria jurídica

  RSK-06      Códigos/habilidades   Pedagógico           Média       Médio         Validação da matriz com
              BNCC incorretos                                                      especialista/coordenação
                                                                                   antes de publicar

  RSK-07      Escopo excessivo      Gestão               Alta        Alto          MoSCoW rígido; Trabalhos
              (creep) comprometendo                                                Futuros fora do MVP;
              o MVP                                                                revisões de escopo
                                                                                   justificadas

  RSK-08      Baixa adoção por      Adoção               Média       Alto          Onboarding, formação,
              professores                                                          criação de desafio em
              (curva/tempo)                                                        minutos, materiais de
                                                                                   apoio

  RSK-09      Custo/infra de IA     Financeiro/Técnico   Média       Médio         LLMs abertos leves via
              (LLM) inviável para                                                  Ollama; inferência local;
              escolas                                                              degradação graciosa

  RSK-10      Conectividade         Operacional          Alta        Médio         PWA + offline parcial;
              instável nas escolas                                                 sincronização posterior;
                                                                                   SQLite local

  RSK-11      Viés algorítmico na   Ético/IA             Média       Médio         Transparência do modelo;
              avaliação (stealth                                                   validação; professor como
              assessment)                                                          autoridade final

  RSK-12      Dependência de        Técnico/Jurídico     Baixa       Médio         Priorizar open-source (já
              terceiros/licenças                                                   é diretriz); revisar
                                                                                   licenças
  -----------------------------------------------------------------------------------------------------------

### 15. Lacunas, Inconsistências e Oportunidades

Análise crítica da proposta original sob a ótica de requisitos. **Cada
item é uma recomendação com justificativa.**

**Requisitos ausentes (recomenda-se especificar):**

23. **Política de retenção e ciclo de vida de dados** --- a proposta
    trata privacidade em nível principiológico; falta definir *por
    quanto tempo* e *como* dados são retidos/excluídos. *Benefício:*
    conformidade LGPD e confiança dos responsáveis. (→ RNF-012)

24. **Faixa etária mínima e regras para \<13 anos** --- definir
    tratamento específico para os mais novos (consentimento reforçado,
    coleta ainda mais restrita). *Benefício:* segurança jurídica e
    ética. (→ RF-008)

25. **Fluxo de autoria/curadoria de conteúdo do professor** --- como o
    docente cria/edita cenários e materiais. *Benefício:* adoção e reuso
    pedagógico.

26. **Moderação de conteúdo gerado pelo aluno** (nomes de
    planetas/espécies, textos) --- filtro anti-abuso. *Benefício:*
    ambiente seguro para menores.

27. **Formação e onboarding de professores** --- requisito de produto
    (tutoriais, exemplos prontos). *Benefício:* mitiga RSK-08.

28. **Governança de modelos de IA** --- versionamento de
    prompts/modelos, avaliação contínua de qualidade e viés.
    *Benefício:* reprodutibilidade e segurança (parcialmente via
    MLflow/W&B).

29. **Modelo de negócio/licenciamento operacional** --- citado no resumo
    executivo, mas sem requisitos (planos, limites por escola).
    *Benefício:* sustentabilidade.

30. **Requisitos de suporte e SLA** para escolas. *Benefício:* operação
    previsível.

**Inconsistências/ambiguidades a resolver:**

-   **Faixa etária:** o *briefing* fala em \"Ensino Fundamental\"; a
    proposta em \"EF II, Médio e Técnico\"; o resumo em \"Fundamental,
    Médio e Técnico\". *Recomendação:* adotar **EF II (6º--9º) + Médio +
    Técnico** como público oficial, com EF I como Trabalho Futuro ---
    impacta linguagem, acessibilidade e LGPD.

-   **\"Intervenções limitadas\":** a proposta não quantifica o
    orçamento de \"pontos de ação\" nem os *cooldowns*. *Recomendação:*
    tratar como parâmetro de *game design* balanceável por trilha
    (RF-017).

-   **Escalas de tempo:** granularidade dos *ticks* e mapeamento
    tempo-real↔tempo-simulado precisam ser definidos (RF-013).
    *Recomendação:* escalas discretas selecionáveis.

-   **Fronteira \"cidades/civilizações\":** parcialmente no núcleo (era
    antrópica) e parcialmente em Trabalhos Futuros. *Recomendação:* MVP
    inclui apenas *era antrópica simplificada*; civilizações
    inteligentes ficam fora (já registrado na §4.6).

-   **RL (aprendizado por reforço):** a proposta o mantém \"contido\";
    requer definir exatamente onde (Diretor de dificuldade / calibração
    offline) para não comprometer explicabilidade (RF-020).

**Oportunidades de melhoria:**

-   **PWA + offline** (adotado como RNF-021/RT): amplia alcance a
    escolas de baixa conectividade --- forte diferencial de mercado.

-   **LLM local (Ollama)**: resolve privacidade *e* custo *e* offline
    simultaneamente --- decisão de alto valor.

-   *Reprodutibilidade por* seed: habilita comparação em turma e
    pesquisa (RF-023) --- barato e pedagogicamente rico.

-   **Dataset anonimizado aberto**: fortalece o perfil \"financiável\"
    do projeto (resumo executivo) --- atrai fomento e parcerias de
    pesquisa.

-   **ADRs e i18n desde o início**: baixo custo agora, alto retorno na
    manutenção e na expansão internacional.

### 16. Entregáveis e Recomendações para a Próxima Fase

### 16.1 Entregáveis desta etapa (contidos neste documento)

31. **Documento completo de levantamento de requisitos** (este ERS).

32. **Catálogo de Requisitos Funcionais** (§4).

33. **Catálogo de Requisitos Não Funcionais** (§8.1).

34. **Catálogo de Requisitos Pedagógicos** (§5.4).

35. **Matriz de alinhamento com a BNCC** (§5.3).

36. **Personas** (§3).

37. **Stakeholders** (§2).

38. **Casos de uso** (§10).

39. **Histórias de usuário** (§11).

40. **Plano de entrevistas** (§9).

41. **Matriz de priorização** (§12).

42. **Lista de riscos** (§14).

43. **Recomendações para a próxima fase** (abaixo).

### 16.2 Recomendações para a próxima fase (Modelagem/Arquitetura)

-   **Validar a matriz BNCC** com coordenação/especialista (mitiga
    RSK-06) --- pré-condição para materiais oficiais.

-   **Definir o MVP** exatamente pelos itens **Must** (§12.1), com foco
    no caminho crítico **RF-011→013→014**.

-   **Detalhar a arquitetura**: diagrama de componentes, contratos
    REST/WebSocket (Java↔Python↔cliente), e o **modelo de dados**
    poliglota (Postgres relacional + esquema de estado em Mongo + chaves
    Redis).

-   **Prototipar cedo** o *core loop* (criar planeta → simular →
    intervir → explicar) para validar desempenho (RSK-02) e a
    experiência do tutor (RSK-03).

-   **Especificar governança de dados** (retenção, DPO, fluxos de
    titular) antes de coletar dados reais (RSK-05).

-   **Escrever ADRs** para as decisões-chave já tomadas (web-native,
    Java×Python, WebGPU+fallback, LLM local).

-   **Planejar o estudo de validação** (grupos, instrumentos, ética/CEP)
    em paralelo ao desenvolvimento, conforme a proposta (§14/§17).

> ***Rastreabilidade:** recomenda-se manter uma **matriz de
> rastreabilidade** (Requisito → Caso de uso → Componente de arquitetura
> → Teste → Evidência de aprendizagem) a partir da próxima fase,
> garantindo que nada se perca entre requisito, código e avaliação
> pedagógica. (Recomendação.)*

*Fim da Etapa 1 --- Engenharia de Requisitos. Documento pronto para
embasar a modelagem de arquitetura, do banco de dados e da
implementação. Escopo preservado em relação à proposta ECOSFERA; todas
as adições de engenharia estão sinalizadas como recomendações
justificadas.*

# PARTE V — Arquitetura, Simulação e Inteligência Artificial


## 9 Modelo de Simulação Científica dos Subsistemas

A simulação é um **acoplamento de subsistemas** que trocam variáveis a
cada *tick*. Cada subsistema é modelado com a técnica mais adequada ao
fenômeno *e* à exigência de explicabilidade.

### 6.1 Evolução biológica

-   **Fenômenos:** seleção natural, mutação, adaptação, especiação,
    extinção.

-   **Modelagem:** **algoritmos evolucionários** (AG/estratégias
    evolutivas, e opcionalmente NEAT para evoluir o \"cérebro\" das
    criaturas). Cada organismo é um **genoma** (vetor de traços:
    tamanho, metabolismo, tolerância térmica, dieta, taxa reprodutiva).
    A *aptidão* (*fitness*) é **emergente do ambiente**: sobrevive quem
    melhor se ajusta às condições atuais (temperatura, recursos,
    predadores). Mutação e recombinação geram variação; a pressão
    seletiva do ambiente faz o resto. Especiação surge por
    **isolamento** (geográfico via relevo/oceanos, ou por deriva de
    nicho).

-   **Por que AG:** é, literalmente, um modelo computacional da própria
    seleção natural --- o mapeamento pedagógico é perfeito e
    **totalmente transparente** (o aluno vê o genoma mudar).

### 6.2 Ecologia

-   **Fenômenos:** biodiversidade, sucessão ecológica, equilíbrio
    ambiental, relações simbióticas (mutualismo, comensalismo,
    parasitismo), espécies invasoras.

-   **Modelagem:** **modelagem baseada em agentes (ABM)** --- cada
    indivíduo/população é um agente com regras locais de alimentação,
    reprodução e movimento; padrões (biodiversidade, sucessão)
    **emergem** da interação. Complementada por **equações
    populacionais** (crescimento logístico, capacidade de suporte K).

### 6.3 Cadeias alimentares

-   **Fenômenos:** produtores, consumidores, decompositores, predadores,
    presas.

-   **Modelagem:** **grafo trófico** (rede de fluxo de energia) + ABM. A
    energia flui dos produtores (fotossíntese, função da luz estelar e
    CO2) para consumidores, com perdas por nível (regra dos \~10%).
    Decompositores fecham o ciclo de nutrientes. Predador-presa segue
    **Lotka--Volterra** discretizado --- o aluno visualiza oscilações
    acopladas.

### 6.4 Reprodução

-   **Fenômenos:** reprodução sexuada, assexuada, taxas populacionais.

-   **Modelagem:** parâmetro do genoma. A **sexuada** (com recombinação)
    acelera a adaptação sob ambiente instável, mas custa energia e
    depende de densidade; a **assexuada** é rápida e barata, porém
    frágil a mudanças --- um *trade-off* evolutivo explícito e didático.

### 6.5 Clima

-   **Fenômenos:** ciclos climáticos, aquecimento global, eras glaciais,
    desertificação.

-   **Modelagem:** **modelo de balanço de energia** simplificado +
    **autômatos celulares** sobre uma grade (temperatura, umidade,
    precipitação por célula). Retroalimentações-chave: **gelo--albedo**
    (gelo reflete → esfria → mais gelo) e **estufa** (CO2/CH4 retêm
    calor). Emergem zonas climáticas, monções, e transições abruptas
    (pontos de inflexão).

### 6.6 Geologia

-   **Fenômenos:** terremotos, vulcões, formação de montanhas, erosão,
    sedimentação.

-   **Modelagem:** **geração procedural** do relevo (ruído de
    Perlin/Simplex com *domain warping*) + **simulação baseada em
    regras** de tectônica simplificada (placas que colidem elevam
    cadeias; que se afastam abrem riftes) e **erosão
    hidráulica/térmica** por autômatos. Vulcanismo injeta CO2 e minerais
    (acopla com clima e solo).

### 6.7 Oceanografia

-   **Fenômenos:** correntes, marés, salinidade.

-   **Modelagem:** correntes derivadas de gradientes de
    temperatura/salinidade e da rotação (efeito de Coriolis
    simplificado); marés em função das luas (acopla com Astronomia).
    Opcionalmente *águas rasas (*shallow-water*) em* compute shader
    (WebGPU) para dinâmica de fluidos aproximada.

### 6.8 Física

-   **Fenômenos:** gravidade, órbitas, radiação, energia.

-   **Modelagem:** **simulação numérica determinística** (integração de
    Verlet/Runge--Kutta) para órbita e rotação; gravidade superficial
    derivada de massa/raio; radiação pela **lei do inverso do quadrado**
    da distância à estrela, atenuada por atmosfera/campo magnético.
    Determinística e exata --- aqui **não** se usa IA (seria
    desnecessário e menos preciso).

### 6.9 Química

-   **Fenômenos:** ciclos químicos, formação de compostos, atmosfera.

-   **Modelagem:** **dinâmica de sistemas** (estoques e fluxos) para os
    ciclos do **carbono, nitrogênio, oxigênio e água** --- balanço de
    massa baseado em regras. A fotossíntese converte CO2→O2; a
    respiração e a combustão fazem o inverso; o intemperismo sequestra
    carbono. O aluno \"vê\" o O2 atmosférico subir com a proliferação da
    vida (analogia à Grande Oxigenação).

### 6.10 Astronomia

-   **Fenômenos:** influência da estrela, luas, meteoritos, cometas.

-   **Modelagem:** mecânica orbital determinística + **gerador
    probabilístico** de impactos (processo de Poisson). A estrela evolui
    (aumenta luminosidade com a idade), pressionando a \"zona
    habitável\".

### 6.11 Fenômenos adicionais sugeridos

Para enriquecer a simulação: **campo magnético e auroras**; **ciclo de
nutrientes limitantes (P, N)**; **acidificação oceânica**; **ciclo de
rochas**; **migração e dispersão de sementes**; **coevolução** (corridas
armamentistas predador-presa, polinizadores-flores); **ecossistemas
extremófilos** (fontes hidrotermais); **ciclos de Milankovitch**
(variações orbitais dirigindo glaciações); **incêndios florestais** como
agentes de sucessão; e **feedbacks biogeoquímicos tipo Gaia** (a biota
regulando o clima).

## 10 Arquitetura de Software

### 1. Visão geral da arquitetura

### 1.1 Comparação de abordagens

  -----------------------------------------------------------------------------
  **Abordagem**        **Prós para       **Contras**          **Veredito**
                       ECOSFERA**                             
  -------------------- ----------------- -------------------- -----------------
  **Camadas** (n-tier) Simples, familiar Tende a acoplar      Usar *dentro* dos
                                         regra a              serviços, não
                                         infraestrutura       como topo

  **Clean              Regra de negócio  Verbosidade inicial  **Adotar**
  Architecture**       isolada de                             (interno)
                       framework/BD;                          
                       testável                               

  **Hexagonal (Ports & Troca de          Curva conceitual     **Adotar**
  Adapters)**          adaptadores (BD,                       (interno)
                       LLM, fila) sem                         
                       tocar no domínio                       

  **DDD**              Linguagem ubíqua  Overhead se mal      **Adotar**
                       alinhada à        aplicado             (tático +
                       pedagogia;                             contextos)
                       *bounded                               
                       contexts* claros                       

  **Monólito Modular** Baixa             Escala tudo junto    **Adotar** p/ a
                       complexidade                           plataforma Java
                       operacional;                           
                       ideal p/ equipe                        
                       enxuta e pesquisa                      

  **Microsserviços**   Escala granular   Complexidade         **Evitar** agora
                                         operacional alta;    
                                         risco de             
                                         *over-engineering*   
                                         (RSK-07)             
  -----------------------------------------------------------------------------

### 1.2 Decisão: **Sistema poliglota orientado a serviços por \"costura\",
com monólito modular na plataforma**

Em vez de microsserviços (complexos demais para a equipe e para o
momento) ou de um monólito único (impossível, pois IA/ciência exigem
Python e escala própria), adota-se um **pequeno conjunto de unidades
implantáveis separadas nas costuras naturais** --- linguagem, escala e
ritmo de mudança:

44. **\`web-client\`** --- SPA/PWA em React/Next.js + TypeScript +
    Three.js (render 3D + **simulação leve client-side**).

45. **\`platform-api\`** --- **monólito modular** em Java/Spring Boot,
    organizado por **bounded contexts (DDD)** com **Clean/Hexagonal**
    interno (identidade, plataforma educacional, avaliação-leitura,
    orquestração).

46. **\`ai-sim-service\`** --- serviço(s) Python/FastAPI para
    **simulação científica autoritativa** e **IA** (evolução, ecologia,
    eventos, tutor, stealth), com *workers* assíncronos.

47. **\`llm-runtime\`** --- Ollama servindo LLMs abertos
    (local/on-premise; RF-040/RT-008).

48. **Dados** --- PostgreSQL (+pgvector), MongoDB, Redis, MinIO; SQLite
    embarcado no cliente (offline).

**Justificativa técnica e pedagógica.** (a) *Equipe enxuta e pesquisa*
--- monólito modular reduz atrito operacional e favorece
reprodutibilidade acadêmica (RT-009). (b) *Integração com IA* --- o
serviço Python isola o ecossistema científico/ML e escala
independentemente do CRUD educacional. (c) *Manutenção/evolução* ---
Hexagonal permite trocar LLM, banco ou fila sem tocar no domínio; DDD
mantém a **linguagem ubíqua** alinhada aos artefatos pedagógicos
(Competência, Evidência, Missão, Planeta). (d) *Escopo* --- evita o
custo de microsserviços prematuros (RSK-07), mas as costuras já permitem
extrair um serviço no futuro sem reescrita.

### 1.3 Diagrama de contexto (C4 --- Nível 1)

┌───────────────────────────────────────────────┐

Aluno ─────────────► │

Professor ─────────► ECOSFERA (Sistema) │

Coordenador ───────► Jogo educacional + IA + avaliação embutida │

Admin/TI ──────────► │

Responsável ───────► │

└───────┬───────────────┬───────────────────────┘

│ │

LMS da escola (LTI 1.3) Órgãos de pesquisa

\[importa turmas/SSO\] \[dataset anonimizado\]

O sistema é **web-native** (sem instalação; RT-Plataforma), integra-se
ao **LMS** via LTI e expõe **dados anonimizados** para pesquisa
(RF-078/RNF-011). EOF echo \"Etapa 1 anexada.\"

### 2. Módulos do sistema

Módulos agrupados pela **unidade implantável** a que pertencem (mapeados
aos módulos do enunciado e do ERS).

### 2.1 platform-api (Node.js / NestJS) --- plataforma educacional

Monólito modular em Node.js/NestJS (TypeScript), organizado por
Domain-Driven Design com arquitetura hexagonal interna e quatro bounded
contexts: identity, education, assessment e orchestration. A migração a
partir de Java/Spring Boot decorreu da recomposição da equipe, agora
TypeScript-cêntrica; o NestJS preserva a modularidade, a injeção de
dependência e a organização hexagonal originais.

  -------------------------- ---------------------------- ------------------------
  **Módulo**                 **Responsabilidades**        **Tecnologias**

  **Autenticação (IAM)**     Login, sessão, tokens,       NestJS + Passport, JWT,
                             SSO/LTI                      OAuth2/OIDC

  **Autorização (RBAC)**     Permissões por papel         Guards e decorators do
                             (RF-004)                     NestJS

  **Usuários & Perfis**      CRUD, preferências,          TypeORM
                             consentimento                
                             (RF-002/007/008/010)         

  **Turmas & Trilhas**       Turmas, vínculos, trilha por NestJS, TypeORM
                             nível (RF-005/061)           

  **Missões & Currículo      Desafios ancorados a         NestJS
  (BNCC)**                   habilidades (RF-062/RP-001)  

  **Painel do Professor**    Indicadores e relatórios     NestJS, WebSocket
                             (RF-063--067)                Gateway

  **Integração LMS (LTI)**   Importar turmas, SSO         Biblioteca LTI 1.3
                             (RF-009/RT-007)              (Node)

  **Administração**          Escolas, tenants,            NestJS
                             configuração (RF-001)        

  **Orquestração/Gateway**   Encaminha chamadas ao        NestJS, cliente HTTP
                             ai-sim-service               (undici/axios) + Redis
                                                          Streams
  -------------------------- ---------------------------- ------------------------

Bounded contexts: identity (IAM, RBAC, usuários e consentimento);
education (turmas, trilhas, missões BNCC, administração); assessment
(painel do professor e leitura de avaliação); orchestration (gateway,
integração com o ai-sim-service e LTI). A explicitação preserva a
linguagem ubíqua alinhada aos artefatos pedagógicos e mantém a costura
para extração futura de serviços, sem incorrer no custo de
microsserviços prematuros (RSK-07).

### 2.2 ai-sim-service (Python / FastAPI) --- simulação e IA

  ---------------------------------------------------------------------------------------------------------------------------------
  **Módulo**                 **Responsabilidades**   **Entradas**             **Saídas**       **Dependências**   **Tecnologias**
  -------------------------- ----------------------- ------------------------ ---------------- ------------------ -----------------
  **Motor da Simulação**     Orquestra o *tick*;     Estado do planeta,       Novo estado      Subsistemas        NumPy/SciPy
                             integra subsistemas;    ações, *seed*            (*delta*)                           
                             resolve acoplamentos                                                                 
                             (RF-013/014)                                                                         

  **Motor Climático**        Autômatos climáticos,   Estado                   Campos de clima  Motor Simulação    NumPy
                             feedbacks (M4)          atmosférico/energético                                       

  **Motor Geológico**        Tectônica, vulcanismo,  Estado geológico         Relevo/eventos   Motor Simulação    NumPy, ruído
                             erosão, relevo (M5)                              geo                                 procedural

  **Motor Biológico**        Evolução (AG) +         População, ambiente      Espécies,        Motor Simulação    DEAP, Mesa
                             ecologia (ABM)                                   dinâmica                            
                             (RF-031/032)                                                                         

  **Motor de Eventos +       Gera/temporiza eventos  Estado, perfil do aluno  Eventos          Motor Simulação,   SciPy, SB3
  Diretor**                  (RF-019/020)                                     aplicados        Stealth            (contido)

  **Sistema de IA (Tutor)**  Explicações causais,    *Delta*, currículo,      Texto            RAG, LLM runtime   LangGraph,
                             hipóteses               perguntas                explicativo                         Transformers
                             (RF-033/034/039)                                                                     

  **Feedback Inteligente**   Feedback                Ação, estado, modelo do  Mensagem de      Tutor, Stealth     LangGraph
                             imediato/contextual     aluno                    feedback                            
                             (Modelagem §10)                                                                      

  **Stealth Assessment**     Inferir competências    Eventos de telemetria    Estimativas por  Analytics          pgmpy,
                             das ações                                        competência                         scikit-learn
                             (RF-071/072/073)                                                                     

  **Analytics**              Coletar/normalizar      Eventos do jogo          Evidências       ---                FastAPI,
                             telemetria pedagógica                            estruturadas                        Kafka/Redis
                             (RF-071)                                                                             

  **Adaptação/Progressão**   Ajusta dificuldade,     Modelo do aluno,         Parâmetros       Stealth, Diretor   pgmpy/IRT
                             dicas, desbloqueios     objetivo                 adaptativos                         
                             (RF-035)                                                                             
  ---------------------------------------------------------------------------------------------------------------------------------

### 2.3 web-client (TypeScript / React) --- cliente

  -------------------------------------------------------------------------------------------------------------------------
  **Módulo**        **Responsabilidades**   **Entradas**   **Saídas**                **Dependências**   **Tecnologias**
  ----------------- ----------------------- -------------- ------------------------- ------------------ -------------------
  **Visualização    Renderizar planeta      Estado do      Cena 3D                   Netcode            Three.js +
  3D**              reativo (RF-051--059)   planeta                                                     react-three-fiber

  **Simulação leve  Render em tempo real,   *Delta* do     Interpolação visual       Visualização       WebGPU compute /
  (client-side)**   partículas, autômatos   servidor                                                    WASM
                    leves                                                                               

  **UI/HUD**        HUD, painéis, gráficos, Estado,        Interações do aluno       Netcode            React, Tailwind,
                    notificações (GDD §13)  indicadores                                                 Recharts

  **Netcode**       REST + WebSocket + fila Ações, estado  Requisições/assinaturas   platform-api       fetch, WebSocket
                    de sync                                                                             

  **Offline/PWA**   Cache, armazenamento    Estado local   Reconciliação             Netcode            Service Worker,
                    local, sync (RNF-021)                                                               IndexedDB/SQLite
  -------------------------------------------------------------------------------------------------------------------------

### 2.4 Módulos transversais

-   **Persistência** (Etapa 9): Postgres, Mongo, Redis, MinIO; SQLite no
    cliente.

-   **Configurações**: parâmetros de balanceamento/economia/eventos
    versionados (GDD §12), servidos por *feature flags*/config service.

### 3. Componentes internos

### 3.1 Motor da Simulação (ai-sim-service)

-   **Orquestrador de Tick** --- lê estado, dispara subsistemas na ordem
    correta, aplica acoplamentos, produz *delta*; garante *determinismo
    por* seed (RF-023).

-   **Simulador Climático** --- balanço de energia + autômatos
    (temperatura, precipitação, feedbacks gelo-albedo/estufa).

-   **Simulador Geológico** --- tectônica simplificada, vulcanismo,
    erosão hidráulica/térmica, geração procedural de relevo.

-   **Simulador Oceanográfico/Hidrológico** --- correntes, marés (acopla
    luas), salinidade, ciclo da água.

-   **Simulador Químico** --- ciclos (C, N, O, água) como estoques e
    fluxos; composição atmosférica.

-   **Simulador Físico** --- órbita/rotação/gravidade/radiação
    (determinístico, RK4/Verlet).

-   **Simulador Populacional (ABM)** --- agentes, capacidade de suporte,
    predador-presa (Mesa).

-   **Simulador Evolutivo (AG)** --- genomas, mutação, seleção,
    especiação, extinção (DEAP).

### 3.2 Sistema de IA (ai-sim-service)

-   **Orquestrador de Agentes (LangGraph)** --- coordena tutor e
    conselheiros; roteia ferramentas (consultar estado, currículo).

-   **Recuperador (RAG)** --- *embeddings* (sentence-transformers) +
    busca vetorial (pgvector/Chroma) sobre estado da simulação e
    material curricular.

-   **Gerador (LLM)** --- Ollama (Llama 3/Phi-3) para
    explicação/feedback/geração de conteúdo.

-   **Guardrails** --- filtros de entrada/saída, apropriação etária
    (RF-037), anti-injeção.

-   **Diretor** --- política de eventos/dificuldade (regras + RL
    contido).

-   **Motor de Stealth** --- rede bayesiana (pgmpy) + calibração IRT;
    atualiza o **Perfil Cognitivo**.

-   **Adaptador de Progressão** --- decide desbloqueios/dicas a partir
    do Perfil Cognitivo.

### 3.3 Plataforma (platform-api)

-   **AuthN/AuthZ** --- provedor de identidade, emissor JWT, avaliador
    RBAC, adaptador LTI.

-   **Serviços de Aplicação** (casos de uso do ERS) --- orquestram
    domínio e repositórios.

-   **Agregador de Dashboard** --- compõe indicadores por
    competência/turma (assina eventos de avaliação).

-   **Adaptadores de Saída** --- repositórios (JPA), cliente do
    ai-sim-service, produtor de eventos.

### 3.4 Cliente (web-client)

-   **Renderer** --- cena Three.js (WebGPU → WebGL2 *fallback*, RT-003),
    shaders de planeta/atmosfera/oceano, LOD.

-   **Sim-Lite** --- interpolação/efeitos em *compute shaders*; nunca é
    autoritativa (a verdade é do servidor).

-   **State Store** --- estado de UI e do planeta (Zustand);
    reconciliação com *deltas*.

-   **Netcode** --- REST (ações/consultas), WebSocket (stream de
    estado), fila offline (sync).

### 4. Modelo de comunicação

  ------------------------------------------------------------------------------
  **Interação**      **Mecanismo**     **Sínc./Assínc.**   **Justificativa**
  ------------------ ----------------- ------------------- ---------------------
  Cliente ↔          **REST/JSON**     Síncrono            Requisição-resposta
  plataforma (ações,                                       simples, cacheável,
  CRUD, auth)                                              RESTful (RT-002)

  Stream de estado   **WebSocket**     Assíncrono          Atualização em tempo
  do planeta                                               real bidirecional
  (*tick*/*delta*)                                         (RF-021/052, RT-005)

  Explicação do      **SSE** (ou WS)   Assíncrono          *Streaming*
  tutor (texto                                             unidirecional de
  gerado)                                                  tokens do LLM
                                                           (RNF-003)

  Plataforma (Java)  **REST**          Sín. p/ leve;       Chamadas rápidas por
  ↔ IA/Sim (Python)  interno +         **assín.** p/       REST; *jobs* longos
                     **fila**          pesado              (evolução por
                                                           geração, LLM) por
                                                           fila (RT-fila)

  Eventos de domínio **Mensageria      Assíncrono          Desacopla produtor
  (avaliação,        pub/sub**                             (jogo) de
  telemetria)                                              consumidores
                                                           (stealth, dashboard,
                                                           analytics) ---
                                                           **EDA**

  Cache e *fan-out*  **Redis**         ---                 Baixa latência;
  de WebSocket                                             distribui *deltas* a
                                                           múltiplas conexões
  ------------------------------------------------------------------------------

**Princípios.** *Síncrono* onde o usuário espera a resposta (login,
criar planeta, aplicar ação). *Assíncrono/orientado a eventos* onde o
trabalho é pesado ou tem múltiplos interessados (evolução, inferência de
LLM, atualização do stealth, alimentação do dashboard). A **arquitetura
orientada a eventos (EDA)** para telemetria→avaliação é o que permite o
*stealth assessment* rodar **sem interromper** o jogo (RP-004): a ação
emite um evento; o motor de stealth consome-o em segundo plano.

### 5. Contratos de API

**Convenções.** Base /{service}/api/v1. Autenticação Authorization:
Bearer \<JWT\>. JSON em UTF-8. Erros no formato **RFC 7807 (Problem
Details)**:

{ \"type\":\"/errors/validation\", \"title\":\"Dados inválidos\",
\"status\":422,

\"detail\":\"massa fora da faixa permitida\", \"instance\":\"/planets\",
\"traceId\":\"\...\" }

**Códigos comuns:** 200 OK, 201 Created, 202 Accepted (job assíncrono),
204 No Content, 400/422 (validação), 401 (não autenticado), 403 (sem
permissão), 404, 409 (conflito), 429 (limite), 5xx.

### 5.1 Autenticação

  -----------------------------------------------------------------------------------------------------------------------------
  **Método**   **URL**            **Descrição**   **Auth**   **Request**      **Response**                        **Códigos**
  ------------ ------------------ --------------- ---------- ---------------- ----------------------------------- -------------
  POST         /auth/login        Autentica e     ---        {email,senha}    {accessToken,refreshToken,perfil}   200/401
                                  emite JWT                                                                       

  POST         /auth/refresh      Renova token    refresh    {refreshToken}   {accessToken}                       200/401

  POST         /auth/lti/launch   SSO via LTI 1.3 LTI        *LTI claims*     {accessToken,turma}                 200/401

  POST         /auth/logout       Encerra sessão  Bearer     ---              204                                 204
  -----------------------------------------------------------------------------------------------------------------------------

**Exemplo (login) →** 201? não: 200. *Erros:* 401 credenciais inválidas;
429 tentativas excessivas.

### 5.2 Usuários & Consentimento

  -------------------------------------------------------------------------------------------------
  **Método**     **URL**                   **Descrição**           **Auth**          **Códigos**
  -------------- ------------------------- ----------------------- ----------------- --------------
  POST           /users                    Cria usuário (papel)    admin/prof        201/409

  GET            /users/{id}               Perfil                  dono/prof/admin   200/403/404

  PATCH          /users/{id}/preferences   Acessibilidade/idioma   dono              200
                                           (RF-010)                                  

  POST           /users/{id}/consent       Registra consentimento  responsável       201
                                           do responsável (RF-008)                   

  GET            /users/{id}/consent       Status LGPD             prof/admin        200
  -------------------------------------------------------------------------------------------------

### 5.3 Turmas, Trilhas e Missões

  ------------------------------------------------------------------------------------------
  **Método**     **URL**                  **Descrição**        **Auth**       **Códigos**
  -------------- ------------------------ -------------------- -------------- --------------
  POST           /classes                 Cria turma           prof           201

  POST           /classes/{id}/students   Vincula alunos       prof           200

  PATCH          /classes/{id}/track      Define trilha        prof           200
                                          (EF/Médio/Técnico)                  

  POST           /missions                Cria missão ancorada prof           201/422
                                          à BNCC (RF-062)                     

  GET            /missions?classId=       Lista missões da     prof/aluno     200
                                          turma                               
  ------------------------------------------------------------------------------------------

### 5.4 Planetas & Simulação

  ------------------------------------------------------------------------------------------------------------------------------
  **Método**   **URL**                        **Descrição**           **Auth**    **Request**   **Response**       **Códigos**
  ------------ ------------------------------ ----------------------- ----------- ------------- ------------------ -------------
  POST         /planets                       Cria planeta (RF-011)   aluno       {params,      {planetId, state}  201/422
                                                                                  seed?,                           
                                                                                  missionId?}                      

  GET          /planets/{id}                  Estado atual            dono/prof   ---           {state, era,       200
                                                                                                indicators}        

  POST         /planets/{id}/validate         Valida parâmetros       aluno       {params}      {ok, warnings\[\]} 200
                                              (RF-012)                                                             

  POST         /planets/{id}/tick             Avança tempo (RF-013)   aluno       {steps,       202 {jobId} ou     200/202
                                                                                  speed}        {delta}            

  POST         /planets/{id}/interventions    Aplica                  aluno       {action,      {delta, tradeoffs, 200/409
                                              intervenção/trade-off               target, cost} actionPoints}      
                                              (RF-017/018)                                                         

  GET          /planets/{id}/timeline         Linha do                dono/prof   ---           {eras\[\],         200
                                              tempo/checkpoints                                 checkpoints\[\]}   
                                              (RF-015/016)                                                         

  POST         /planets/{id}/checkpoints      Salva checkpoint        aluno       ---           201 {checkpointId} 201
                                              (RF-015)                                                             

  GET          /planets/{id}/series?metric=   Séries temporais        dono/prof   ---           {points\[\]}       200
                                              (RF-021)                                                             
  ------------------------------------------------------------------------------------------------------------------------------

**Exemplo (intervenção):** *Request*
{\"action\":\"INDUSTRIALIZE\",\"target\":\"region-7\",\"cost\":{\"actionPoints\":2,\"energy\":10}};
*Response* { \"delta\":{\...},
\"tradeoffs\":\[{\"gain\":\"prosperity+\",\"cost\":\"co2+, temp+\"}\],
\"actionPoints\":{\"remaining\":3} }. *Erros:* 409 pontos insuficientes;
404 planeta; 403 não é dono.

### 5.5 Eventos

  -------------------------------------------------------------------------------------------
  **Método**     **URL**                        **Descrição**   **Auth**       **Códigos**
  -------------- ------------------------------ --------------- -------------- --------------
  GET            /planets/{id}/events           Histórico de    dono/prof      200
                                                eventos                        

  POST           /planets/{id}/events/respond   Responde a      aluno          200
                                                evento em curso                
  -------------------------------------------------------------------------------------------

### 5.6 IA (Tutor / Feedback / Adaptação)

  ----------------------------------------------------------------------------------------------------------------------
  **Método**   **URL**                      **Descrição**        **Auth**     **Request**   **Response**   **Códigos**
  ------------ ---------------------------- -------------------- ------------ ------------- -------------- -------------
  POST         /ai/explain                  Explicação causal    aluno        {planetId,    *SSE stream*   200
                                            (RF-033/039)                      contextRef,   de texto       
                                                                              question?}                   

  POST         /ai/hint                     Dica personalizada   aluno        {planetId,    {hint, level}  200
                                            (RF-035)                          missionId}                   

  POST         /ai/advisor                  Conselheiro-agente   aluno        {role, query} {advice}       200
                                            (RF-036)                                                       

  GET          /ai/adaptation/{studentId}   Parâmetros           plataforma   ---           {difficulty,   200
                                            adaptativos                                     unlocks\[\]}   
  ----------------------------------------------------------------------------------------------------------------------

### 5.7 Avaliação & Stealth Assessment

  --------------------------------------------------------------------------------------------------------
  **Método**     **URL**                              **Descrição**          **Auth**       **Códigos**
  -------------- ------------------------------------ ---------------------- -------------- --------------
  POST           /assessment/events                   Ingesta de             serviço        202
                                                      telemetria/evidência                  
                                                      (RF-071)                              

  GET            /assessment/students/{id}/profile    Perfil cognitivo por   prof/dono      200
                                                      competência                           
                                                      (RF-072/073)                          

  GET            /assessment/students/{id}/evidence   Evidências rastreáveis prof           200
                                                      (RF-076)                              

  GET            /assessment/students/{id}/bncc       Domínio mapeado à BNCC prof/coord     200
  --------------------------------------------------------------------------------------------------------

### 5.8 Painel do Professor / Coordenação

  -----------------------------------------------------------------------------------------------------
  **Método**     **URL**                                  **Descrição**   **Auth**       **Códigos**
  -------------- ---------------------------------------- --------------- -------------- --------------
  GET            /dashboard/classes/{id}/overview         Visão de turma  prof           200
                                                          (RF-063)                       

  GET            /dashboard/classes/{id}/competencies     Progresso por   prof/coord     200
                                                          competência                    

  GET            /dashboard/classes/{id}/alerts           Alertas de      prof           200
                                                          dificuldade                    
                                                          (RF-077)                       

  POST           /dashboard/students/{id}/feedback        Envia feedback  prof           201
                                                          ao aluno                       
                                                          (RF-067)                       

  GET            \`/dashboard/reports/export?format=pdf   csv\`           Exporta        prof/coord
                                                                          relatório      
                                                                          (RF-066)       

  GET            /research/dataset?anonymized=true        Dataset         pesquisador    200
                                                          anonimizado                    
                                                          (RF-078)                       
  -----------------------------------------------------------------------------------------------------

### 5.9 Canais de tempo real (WebSocket)

-   ws://.../planets/{id}/stream --- *deltas* de estado por *tick*,
    eventos, notificações (RF-021/052/056).

-   Mensagens tipadas: {type:\"delta\"\|\"event\"\|\"tutor\"\|\"alert\",
    payload:{\...}, tickId}.

-   Autenticação no *handshake* (JWT); *fan-out* via Redis pub/sub.

### 6. Modelo de dados

### 6.1 Modelo conceitual (entidades e relacionamentos)

Escola 1───N Usuario ──(Papel: Aluno\|Professor\|Coordenador\|Admin)

Usuario(menor) 1───1 Consentimento N───1 Responsavel

Professor 1───N Turma 1───1 Trilha ; Turma N───N Aluno (Matricula)

Aluno 1───N Planeta ; Planeta N───1 Missao (opcional)

Missao N───N HabilidadeBNCC N───1 Competencia

Planeta 1───N Estado(Era) ; Planeta 1───N Checkpoint

Planeta 1───N Especie ; Planeta 1───N Ecossistema ; Especie N───N
Ecossistema

Planeta 1───N Evento ; Planeta 1───N Intervencao 1───1
Decisao(Trade-off)

Aluno 1───N Sessao 1───N Evidencia

Evidencia N───1 EventoDoJogo ; Evidencia N───1 Competencia

Aluno 1───1 PerfilCognitivo 1───N EstimativaCompetencia

Avaliacao 1───N Evidencia ; Aluno 1───N Feedback

**Relacionamentos-chave (explicação).** Uma **Turma** pertence a um
**Professor** e adota uma **Trilha** (nível); alunos entram por
**Matrícula** (N:N). Cada **Aluno** cria **Planetas**; um Planeta pode
estar vinculado a uma **Missão**, que referencia **Habilidades da BNCC**
(cada uma sob uma **Competência**). O Planeta acumula **Estados por
Era** e **Checkpoints**, e contém **Espécies**, **Ecossistemas**,
**Eventos** e **Intervenções** (cada intervenção encapsula uma
**Decisão** com seu trade-off). A jogabilidade gera **Evidências** (por
**Sessão**), ligadas a **Eventos do jogo** e a **Competências**; o motor
de stealth mantém o **Perfil Cognitivo** (uma **Estimativa por
Competência**). **Avaliação** agrega evidências e **Feedback** é
dirigido ao aluno.

### 6.2 Modelo lógico (tabelas e coleções)

**Relacional (PostgreSQL):** school, user(role), guardian, consent,
class, enrollment, track, mission, mission_bncc, bncc_skill, competency,
cognitive_profile, competency_estimate, evidence(estruturada),
assessment, feedback, planet_meta(id, owner, current*era, seed,
mission*id), audit_log, embedding(pgvector). **Documento (MongoDB):**
planet_state(estado aninhado por era/checkpoint),
species(genoma+traços), ecosystem, event_log, telemetry(eventos brutos
de sessão). **Chave-valor (Redis):** action_points:{planetId},
session:{id}, canais pub/sub, filas de *job*. **Objetos (MinIO):**
*assets*, exportações (PDF/CSV), *dumps* de dataset.

### 6.3 Modelo físico --- escolha de armazenamento (justificativa)

  -------------------------------------------------------------------------
  **Dado**          **Padrão de         **Store**         **Por quê**
                    acesso**                              
  ----------------- ------------------- ----------------- -----------------
  Usuários, turmas, Transacional,       **PostgreSQL**    Integridade ACID,
  consentimento,    relacional,                           *joins*, análise;
  missões,          consultas                             LGPD/auditoria
  competências,     longitudinais                         exigem
  perfil cognitivo,                                       consistência
  avaliação,                                              
  auditoria                                               

  *Embeddings* do   Busca vetorial      **PostgreSQL +    Evita mais um
  RAG                                   pgvector**        banco;
                                                          co-localizado

  Estado do planeta Escrita intensa,    **MongoDB**       Documento encaixa
  (aninhado, evolui esquema                               em estado nested
  por era),         flexível/variável                     que muda por era;
  espécies,                                               alto volume
  ecossistemas, log                                       
  de eventos,                                             
  telemetria                                              

  Contadores        Baixa latência,     **Redis**         Tempo real e
  efêmeros, cache,  volátil                               desacoplamento
  pub/sub, filas                                          

  Assets, exports,  Blob                **MinIO**         S3-compatível
  dataset                                                 open-source

  Estado local      Embarcado,          **SQLite**        Offline em escola
  offline + fila de single-instance     (cliente)         (RNF-021)
  sync                                                    
  -------------------------------------------------------------------------

**Postgres × Mongo × SQLite (decisão).** Nenhum banco único atende bem a
*tudo*: a plataforma exige **relacional/ACID** (Postgres); o estado do
planeta é um **documento aninhado e mutável** (Mongo); o modo offline
pede **embarcado** (SQLite). Adota-se **persistência poliglota** ---
cada store para seu padrão de acesso, coerente com RT-004 e proposta
§12.5.

### 7. Modelo de domínio (DDD)

### 7.1 Bounded Contexts

┌──────────────┐ ┌───────────────────────┐ ┌──────────────────────────┐

│ Identidade & │ │ Plataforma Educacional │ │ Simulação │

│ Acesso │ │ Turma·Trilha·Missão· │ │ Planeta(raiz)·Subsistemas │

│ Usuário·Papel│ │ Currículo(BNCC) │ │ Espécie·Evento·Intervenção│

└──────┬───────┘ └───────────┬────────────┘ └───────────┬──────────────┘

│ │ │ (Domain Events)

└──────────────┬───────┴─────────────┬──────────────┘

▼ ▼

┌──────────────────┐ ┌────────────────────┐

│ Avaliação │ │ Tutoria / IA │

│ Competência· │ │ Tutor·Feedback· │

│ Evidência· │ │ Adaptação │

│ PerfilCognitivo │ │ │

└──────────────────┘ └────────────────────┘

### 7.2 Agregados, entidades e objetos de valor

-   **Agregado \`Planeta\`** (raiz) --- entidades internas: Estado/Era,
    Espécie, Ecossistema, Intervenção, Evento, Checkpoint.
    **Invariantes:** conservação de recursos/energia; coerência de era;
    determinismo por *seed*. Objetos de valor: ParâmetrosPlanetários,
    Genoma, Região/Coordenada, IndicadorAmbiental,
    Trade-off(ganho,custo), PontosDeAção, Seed.

-   **Agregado \`Turma\`** (raiz) --- Matrícula, Trilha. VO: Nível.

-   **Agregado \`Missão\`** (raiz) --- vínculos HabilidadeBNCC. VO:
    HabilidadeBNCC(código), ObjetivoPedagógico.

-   **Agregado \`PerfilCognitivo\`** (raiz) --- EstimativaCompetência.
    VO: CompetênciaScore(valor, incerteza) (probabilístico/IRT).

-   **Agregado \`Usuário\`** (raiz) --- Papel, Consentimento. VO:
    Preferências.

### 7.3 Serviços de domínio

-   **ServiçoDeSimulação** --- executa o *tick* (orquestra subsistemas;
    puro/determinístico).

-   **ServiçoDeEvolução** --- aplica AG sobre populações.

-   **ServiçoDeAvaliação** --- infere competências das evidências
    (regras do *evidence model*).

-   **ServiçoDeAdaptação** --- decide dificuldade/desbloqueios a partir
    do Perfil Cognitivo.

-   **ServiçoDeExplicação** --- gera a narrativa causal (via IA).

### 7.4 Eventos de domínio (base da EDA)

PlanetaCriado, EraAvançada, IntervençãoAplicada, EventoOcorreu,
EvidênciaGerada, CompetênciaAtualizada, MissãoConcluída. Esses eventos
são o **contrato assíncrono** entre Simulação → Avaliação → Dashboard,
viabilizando o stealth sem acoplamento.

> ***Linguagem ubíqua:** os nomes de domínio (Planeta, Espécie,
> Trade-off, Competência, Evidência, Missão, PerfilCognitivo) são **os
> mesmos** dos artefatos pedagógicos e do GDD --- DDD mantém pedagogia,
> game design e código falando a mesma língua.*

### 8. Integração com IA

O ai-sim-service reúne **quatro famílias de modelos** com papéis
distintos, respeitando a **fronteira determinístico×IA** do GDD (§10): a
IA governa o emergente, o adaptativo e a mediação --- **nunca**
falsifica a física/ciência que o aluno precisa entender.

  ------------------------------------------------------------------------------------------------------------------
  **Família**               **Papel**                         **Entradas**   **Saídas**     **Técnica/Lib**
  ------------------------- --------------------------------- -------------- -------------- ------------------------
  **Simulação (emergente)** Evolução e ecologia vivas         População,     Espécies,      AG (DEAP), ABM (Mesa)
                                                              ambiente,      dinâmica       
                                                              *seed*         populacional   

  **Adaptação**             Ajustar                           Perfil         Parâmetros     BKT/IRT (pgmpy/sklearn),
                            dificuldade/dicas/desbloqueios;   Cognitivo,     adaptativos,   RL contido (SB3)
                            ritmo de eventos                  objetivo da    política do    
                                                              missão         Diretor        

  **Feedback/Explicação**   Explicar causalidade; feedback    *Delta* do     Texto          LLM+RAG (Ollama,
                            inteligente                       estado,        explicativo    LangGraph,
                                                              currículo,     (SSE)          sentence-transformers)
                                                              pergunta                      

  **Geração de conteúdo**   Descrições de espécies/eras,      Estado,        Conteúdo       LLM (Ollama) +
                            cenários, dicas                   contexto       textual        guardrails (RF-037)
                                                              pedagógico     apropriado à   
                                                                             idade          
  ------------------------------------------------------------------------------------------------------------------

**Integração com o jogo.** O *tick* (/planets/{id}/tick) invoca os
modelos de **simulação**; a resposta (*delta*) segue por WebSocket ao
cliente. As explicações vêm do modelo de **feedback** via /ai/explain
(SSE). A **adaptação** entrega parâmetros consumidos pela plataforma
para calibrar missões/eventos.

**Integração com o Stealth Assessment.** Cada ação emite um **evento de
telemetria** → o **Analytics** normaliza em **Evidência** → o **Motor de
Stealth** (rede bayesiana) atualiza o **Perfil Cognitivo** → que
realimenta a **Adaptação** e o **Dashboard**. Fluxo assíncrono (EDA),
sem interromper o jogo (RP-004).

**Integração com o Painel do Professor.** O Perfil Cognitivo e as
Evidências (mapeadas à BNCC, RF-076) alimentam os indicadores do
dashboard (RF-063/064) e as **recomendações da IA** (Modelagem §11).

Ação do aluno ─► \[tick\] ─► Modelos de Simulação ─► delta ─► WebSocket
─► Cliente 3D

│

└─(evento)─► Analytics ─► Evidência ─► Stealth(BN) ─► Perfil Cognitivo

│ │

Adaptação ◄───┘ └──► Dashboard/IA-recomenda

│

└─► dificuldade/dicas/desbloqueios ─► próximo ciclo

Tutor: \[/ai/explain\] ─► RAG(estado+currículo) ─► LLM(Ollama) ─►
guardrails ─► SSE ─► Cliente

### 9. Persistência

Estratégia de persistência poliglota, com separação do PostgreSQL em
dois schemas de propriedade distinta --- decisão consolidada durante a
estruturação do monorepo.

  ------------------- -------------------------------- --------------------
  **Repositório**     **Papel**                        **Propriedade /
                                                       migrações**

  **PostgreSQL ---    Sistema de registro: usuários,   platform-api, via
  schema platform**   escolas, turmas, matrículas,     TypeORM
                      missões BNCC, avaliação,         
                      consentimento (RF-008)           

  **PostgreSQL ---    Vetores e metadados do RAG       ai-sim-service, via
  schema rag**        (extensão pgvector)              Alembic/SQLAlchemy

  **MongoDB**         Estado da simulação (JSON        ai-sim-service
                      aninhado que evolui por era) e   
                      logs de telemetria (RF-015/071)  

  **Redis**           Cache, sessões, pub/sub de       Compartilhado
                      WebSocket e Redis Streams para   
                      eventos                          

  **MinIO / S3**      Objetos e artefatos              platform-api

  **SQLite /          Persistência local no cliente    web-client
  IndexedDB**         para operação offline (RNF-021)  
  ------------------- -------------------------------- --------------------

Justificativa: cada serviço é proprietário exclusivo do seu schema e das
suas migrações, eliminando conflito entre TypeORM e Alembic e
materializando no banco a mesma fronteira de responsabilidade da
arquitetura. A extensão pgvector e os schemas são criados na
inicialização do banco; as tabelas residem exclusivamente nas migrações,
versionadas e reexecutáveis. Benefícios: isolamento de responsabilidade
sem um segundo servidor de banco; reaproveitamento do PostgreSQL como
repositório vetorial; possibilidade de roles restritas por schema em
produção.

+-----------------------------------------------------------------------+
| **Parâmetro de implementação**                                        |
|                                                                       |
| • A dimensão do vetor de embeddings está fixada em 768 (compatível    |
| com all-mpnet-base-v2).                                               |
|                                                                       |
| • Adotar outro modelo (ex.: all-MiniLM-L6-v2, 384) exige ajuste antes |
| da migração --- alterar depois obriga a recriar a tabela.             |
+-----------------------------------------------------------------------+

### 10. Segurança

Arquitetura de segurança em profundidade, atendendo RNF-006--013 e
RF-037.

-   **Autenticação.** **JWT** de vida curta + *refresh token*;
    **OAuth2/OIDC** para provedores externos; **LTI 1.3** para SSO via
    LMS. Senhas com *hash* forte (Argon2/bcrypt). **Nunca** o sistema
    pede/armazena credenciais de terceiros em texto.

-   **Autorização.** **RBAC** por papel
    (aluno/professor/coordenador/admin) + **verificação de posse**
    (aluno só acessa o próprio planeta). Aplicada no gateway e no
    domínio (defesa em profundidade).

-   **Criptografia.** **TLS** obrigatório em trânsito; dados sensíveis
    **cifrados em repouso**; segredos em cofre (ex.: variáveis
    seladas/secret manager), fora do código.

-   **LGPD.**

    -   **Consentimento do responsável** (RF-008) é *bloqueante*: sem
        ele, dados pessoais do menor não são coletados/processados
        (RNF-009).

    -   **Minimização** (RNF-010): coleta-se só o necessário à
        finalidade pedagógica.

    -   **Anonimização/pseudonimização** (RNF-011): dataset de pesquisa
        sem PII (RF-078); *pipeline* remove identificadores antes da
        exportação.

    -   **Retenção e direitos do titular** (RNF-012): política de
        retenção documentada; fluxos de acesso/correção/exclusão; DPO
        designado.

    -   **Segregação por escola/turma** (RNF-013): isolamento lógico
        *multi-tenant*.

-   **Proteção da IA.** *Guardrails* de entrada/saída no LLM (RF-037);
    defesa contra **injeção de prompt** (o conteúdo recuperado por RAG é
    tratado como dado, não como instrução); **redação de PII** antes de
    enviar contexto ao LLM.

-   **Auditoria e logs.** audit_log imutável para ações sensíveis
    (consentimento, exportações, mudanças de permissão); logs
    estruturados e correlacionados por traceId; alertas de acesso
    indevido.

-   **Rate limiting** e proteção contra abuso (429) nos endpoints de
    auth e IA.

### 11. Escalabilidade

A arquitetura escala por **decisões estruturais**, não só por hardware:

-   **Simulação em tempo real no cliente** (RT-001): o trabalho pesado
    de render/sim-leve roda na GPU do aluno --- o servidor **não**
    escala por-aluno nessa parte (RNF-004). Este é o maior fator de
    escala.

-   *Serviços* stateless *e horizontais. \`platform-api\` e os* workers
    *do \`ai-sim-service\` são sem estado (estado nos bancos/Redis) →
    escalam horizontalmente atrás de um balanceador (Nginx)*.

-   **Filas e processamento assíncrono.** *Jobs* pesados (evolução por
    geração, inferência LLM, atualização de stealth) vão para **filas**;
    *workers* consomem em paralelo, absorvendo picos sem travar a
    experiência.

-   **Cache (Redis).** Reduz carga em estado quente, dashboards e RAG.

-   **Banco.** Postgres com **réplicas de leitura** para
    dashboards/relatórios; Mongo **sharded** por planeta/escola se o
    volume de telemetria crescer.

-   **LLM.** *Pool* de instâncias Ollama com *batching*; escolas grandes
    podem hospedar o llm-runtime localmente (privacidade + custo).

-   **Multi-tenant.** Isolamento lógico por escola (RNF-013);
    crescimento em nº de escolas/turmas é linear e independente.

  -----------------------------------------------------------------------
  **Cenário de crescimento**          **Mecanismo**
  ----------------------------------- -----------------------------------
  Mais alunos por turma               Sim no cliente + WebSocket
                                      *fan-out* via Redis

  Muitas escolas/turmas               Multi-tenant + escala horizontal +
                                      réplicas

  Picos de simulação/IA               Filas + *workers* Python
                                      autoescaláveis

  Múltiplos servidores                *Stateless* + balanceamento +
                                      estado externalizado
  -----------------------------------------------------------------------

**Opções de implantação:** (a) **nuvem multi-tenant** (SaaS) para a
maioria; (b) **on-premise por escola** (Docker Compose + Ollama local)
para requisitos de privacidade/offline --- a mesma base de código serve
às duas.

### 12. Tecnologias

### 12.1 Backend --- divisão Node.js × Python

  -------------------------- ---------------------- ---------------------
  **Responsabilidade**       **Stack**              **Porquê**

  **Plataforma (auth,        Node.js + NestJS       Competência atual da
  turmas, missões, painel,   (TypeScript)           equipe; unificação de
  LTI, integridade)**                               linguagem com o
                                                    cliente; modularidade
                                                    e DI equivalentes ao
                                                    padrão anterior
                                                    (RT-002)

  **Simulação científica e   Python + FastAPI       Ecossistema
  IA**                                              ML/AG/ABM/LLM;
                                                    assíncrono e tipado
                                                    (inalterado)
  -------------------------- ---------------------- ---------------------

ORM: TypeORM no schema platform (platform-api) e Alembic/SQLAlchemy no
schema rag (ai-sim-service). Build e workspace: pnpm workspaces +
Turborepo (TypeScript) e uv (Python). Contratos congelados em pacote
compartilhado (OpenAPI 3.1).

### 12.2 Front-end

**React + Next.js + TypeScript**; estado com **Zustand**;
**TailwindCSS**; **Recharts/visx** para gráficos; PWA (Service Worker +
IndexedDB). Justificativa: TS traz segurança de tipos a um front
complexo; Next.js oferece roteamento/SSR e boa DX.

### 12.3 Visualização 3D --- análise web-first

  --------------------------------------------------------------------------
  **Biblioteca**       **Vantagens**     **Limitações**    **Veredito**
  -------------------- ----------------- ----------------- -----------------
  **Three.js** (+      Ecossistema       Requer montar     **Recomendada
  react-three-fiber,   enorme, TS,       recursos \"de     (núcleo)**
  drei)                integra com       engine\" à mão    
                       React; **WebGPU +                   
                       fallback WebGL                      
                       2**; controle                       
                       total de shaders;                   
                       *compute* p/ sim                    
                       leve                                

  **Babylon.js**       \"Baterias        Menos idiomática  Alternativa
                       inclusas\" (PBR,  em React          principal
                       física,                             
                       WGSL/WebGPU)                        

  **PlayCanvas**       Editor na nuvem,  Acoplamento de    Viável, não
                       ECS, boa          plataforma; menos preferida
                       performance       *code-first*      

  **CesiumJS**         Globo geoespacial Feito p/ Terra    Não (núcleo)
                       real (WGS84)      real; pesado para 
                                         planetas          
                                         fictícios         

  **A-Frame**          VR/AR declarativo Limitante para a  Futuro (RV)
                       (WebXR) sobre     app principal     
                       Three                               
  --------------------------------------------------------------------------

**Decisão:** **Three.js + react-three-fiber** (WebGPU→WebGL2), com
*compute shaders* para sim leve (RT-003). Atende alterar dinamicamente
atmosfera, oceanos, vegetação, espécies, cidades, relevo, clima e
desastres (RF-052) **sem** motor de jogos.

**Godot?** Só se houver **cliente nativo/offline \"jogo\"** no futuro
(proposta §12.1). Para a app web integrada (dashboards, LMS, avaliação),
a via web integra melhor; Godot na web tem *download* pesado, exige
COOP/COEP e isola-se do DOM. Se necessário motor: **Godot 4.x**
(open-source) é a primeira escolha.

### 12.4 Banco de dados

  -----------------------------------------------------------------------
  **Opção**               **Uso no projeto**      **Veredito**
  ----------------------- ----------------------- -----------------------
  **PostgreSQL**          Relacional              **Primário**
  (+pgvector)             autoritativo + vetores  
                          RAG                     

  **MongoDB**             Estado do               **Complementar**
                          planeta/telemetria      
                          (documento)             

  **SQLite**              Offline no cliente      **Modo local**

  **Redis**               Cache/pub-sub/filas     **Infra de apoio**
  -----------------------------------------------------------------------

### 12.5 Infraestrutura

**Docker + Docker Compose** (dev e on-premise; K8s só se escalar muito),
**Nginx** (proxy/TLS/COOP-COEP/balanceamento), **GitHub Actions**
(CI/CD), **Prometheus + Grafana** (observabilidade; inclui métricas
pedagógicas e de IA), **MinIO** (objetos), **Ollama** (LLM). Tudo
open-source.

### 13. Diagramas arquiteturais (C4 / UML em texto)

### 13.1 Container (C4 --- Nível 2)

┌───────────── web-client (React/Next/TS/Three.js --- PWA)
─────────────┐

│ UI/HUD · Visualização 3D (WebGPU→WebGL2) · Sim-leve · Netcode │

└───────┬───────────────────────────────┬─────────────────────────────┘

│ REST/JSON (ações, CRUD) │ WebSocket (delta/eventos) · SSE (tutor)

┌───────▼───────────────────────────────▼─────────────────────────────┐

│ Nginx (TLS · balanceador) │

└───────┬───────────────────────────────┬─────────────────────────────┘

▼ ▼

┌────────────────────────┐ ┌──────────────────────────────────────┐

│ platform-api (Java/ │◄───►│ ai-sim-service (Python/FastAPI) │

│ Spring --- monólito │REST │ Simulação · IA · Stealth · Analytics │

│ modular, DDD/Hexagonal)│+fila│ + workers assíncronos │

└───────┬─────────┬──────┘ └───────┬───────────────┬──────────────┘

│ │ │ │

▼ ▼ ▼ ▼

PostgreSQL Redis(cache/ MongoDB llm-runtime

(+pgvector) pub-sub/filas) (estado/telemetria) (Ollama)

│

MinIO (objetos)

### 13.2 Componente --- Simulação (C4 --- Nível 3)

Orquestrador de Tick

├─ Simulador Físico (determinístico) ├─ Simulador Químico (ciclos)

├─ Simulador Climático (autômatos) ├─ Simulador Geológico (procedural)

├─ Simulador Oceanográfico/Hidrológico ├─ Simulador Populacional
(ABM/Mesa)

└─ Simulador Evolutivo (AG/DEAP)

→ resolve acoplamentos → produz DELTA (determinístico por seed)

### 13.3 Fluxo da simulação

estado + ações + seed → Orquestrador de Tick → subsistemas acoplados →
delta → (persistência checkpoint + WebSocket ao cliente)

### 13.4 Fluxo da IA (tutor)

pergunta/contexto → RAG (estado + currículo, pgvector) → LLM (Ollama) →
guardrails → SSE → cliente

### 13.5 Fluxo de dados (intervenção)

Cliente → REST /interventions → platform-api (autoriza, debita pontos) →
ai-sim-service (aplica trade-off, recalcula) → Mongo (estado) + evento
de domínio → WebSocket (delta) + Analytics

### 13.6 Fluxo do Stealth Assessment

Ação ─►(evento telemetria)─► Analytics ─► Evidência ─► Motor Stealth
(rede bayesiana pgmpy)

─► atualiza Perfil Cognitivo (Postgres) ─► { Adaptação
(dificuldade/dicas) , Dashboard (RF-063/064) }

### 14. Roadmap técnico

Ordem de implementação derivada do **mapa de dependências do ERS (§13)**
e da recomendação do GDD de um ***vertical slice*** cedo. Estratégia
*incremental e* API-first (contratos OpenAPI antes do código).

  ---------------------------------------------------------------------------
  **Fase**          **Entregas**       **Depende de**    **RF/RNF
                                                         principais**
  ----------------- ------------------ ----------------- --------------------
  **F0 · Fundação** Repos, CI/CD,      ---               RF-001--005,
                    Docker Compose,                      RNF-006/007
                    IAM (auth/RBAC),                     
                    escola/turma                         

  **F1 · Núcleo de  Planeta CRUD,      F0                RF-011--014, RF-023
  Simulação**       orquestrador de                      
                    *tick*,                              
                    subsistemas                          
                    clima+química,                       
                    *seed*                               
                    reprodutível                         

  **F2 ·            Render 3D          F1                RF-051--055,
  Visualização +    (WebGPU/WebGL2),                     RF-017/018
  Loop**            HUD, intervenção +                   
                    trade-off                            

  **F3 · Vertical   Uma era completa   F2                GDD §2; RSK-02/03
  Slice (1 era)**   atravessando o                       
                    *core loop*                          
                    (valida diversão,                    
                    desempenho, tutor                    
                    básico)                              

  **F4 · IA de      Evolução (AG),     F1/F3             RF-031/032/019/020
  Simulação**       ecologia (ABM),                      
                    eventos + Diretor                    

  **F5 · Tutor e    LLM+RAG,           F3                RF-033/034/037/039
  Feedback**        explicação causal,                   
                    guardrails                           

  **F6 ·            Telemetria,        F3/F4             RF-071/072/073/076
  Avaliação**       Stealth (rede                        
                    bayesiana), Perfil                   
                    Cognitivo, mapa                      
                    BNCC                                 

  **F7 ·            Missões BNCC,      F6                RF-061--067
  Professor**       dashboard,                           
                    alertas,                             
                    exportação                           

  **F8 · Robustez** PWA/offline, LTI,  F2/F7             RNF-009--021/025,
                    LGPD,                                RF-009
                    acessibilidade,                      
                    observabilidade                      

  **F9 ·            Piloto em escolas, F7/F8             RF-078, proposta §17
  Validação**       ajustes, dataset                     
                    anonimizado                          
  ---------------------------------------------------------------------------

**Caminho crítico:** RF-011 → RF-013 → RF-014 (habilita quase tudo).
**Bloqueio legal:** consentimento (RF-008) antes de qualquer coleta de
dados de menor. **Estratégia:** *vertical slice* na F3 antes de ampliar
em largura; *feature flags* para ligar subsistemas gradualmente; testes
automatizados desde a F0.

### 15. Fundamentação técnica

  --------------------------------------------------------------------------
  **Decisão**             **Boa prática / padrão**   **Justificativa**
  ----------------------- -------------------------- -----------------------
  Domínio isolado de      **Clean Architecture /     Testabilidade; trocar
  framework/BD            Hexagonal**                LLM/BD/fila sem tocar
                                                     na regra

  Contextos e linguagem   **DDD**                    Alinha código à
  ubíqua                                             pedagogia e ao GDD
                                                     (Competência, Planeta,
                                                     Evidência)

  Componentes coesos e    **SOLID**                  Manutenção por equipe
  desacoplados                                       enxuta; extensibilidade

  Subsistemas de          **Strategy**               Cada subsistema é uma
  simulação                                          estratégia plugável no
  intercambiáveis                                    *tick*

  Telemetria→avaliação    **Observer / Pub-Sub ·     Stealth sem interromper
  desacoplada             EDA**                      o jogo (RP-004)

  Acesso a dados          **Repository**             Abstrai Postgres/Mongo
                                                     do domínio

  Adaptadores externos    **Ports & Adapters /       Isola integrações
  (LLM, LMS, fila)        Adapter**                  voláteis

  Criação de planeta      **Factory** · **Command**  Encapsula construção,
                          (intervenções) · **State** ações e transições
                          (eras)                     

  APIs                    **RESTful** + RFC 7807 +   Contratos claros,
                          OpenAPI                    cacheáveis, versionados

  Simulação               *Game loop determinístico  Reprodutibilidade
                          +* seed ; ABM/ECS-like     (RF-023) e emergência

  IA                      **RAG** +                  Reduz alucinação;
                          **model-as-a-service** +   modelos plugáveis;
                          orquestração (LangGraph)   explicabilidade

  Serviços separados por  **Monólito Modular +       Simplicidade
  costura                 serviço de IA**            operacional com escala
                                                     onde importa
  --------------------------------------------------------------------------

> ***Princípio transversal:** cada decisão arquitetural serve a um
> objetivo pedagógico. O determinismo por seed existe para o aluno
> **confiar na causalidade**; a EDA existe para **avaliar sem
> interromper**; a persistência poliglota existe para **reproduzir e
> pesquisar**; o LLM local existe para **privacidade (LGPD) e operação
> offline**.*

### 16. Entregáveis e recomendações

### 16.1 Entregáveis desta etapa (contidos no documento)

49. Documento completo de arquitetura · 2. Visão arquitetural (§1) · 3.
    Módulos (§2) · 4. Componentes internos (§3) · 5. Modelo de
    comunicação (§4) · 6. Contratos de API (§5) · 7. Modelo conceitual
    de dados (§6.1) · 8. Modelo lógico (§6.2/6.3) · 9. Modelo de domínio
    (§7) · 10. Arquitetura de IA (§8) · 11. Persistência (§9) · 12.
    Segurança (§10) · 13. Escalabilidade (§11) · 14. Comparativo de
    tecnologias (§12) · 15. Diagramas (§13) · 16. Roadmap técnico (§14)
    · 17. Recomendações (abaixo).

### 16.2 Recomendações para a próxima etapa (implementação)

-   **Especificar a API em OpenAPI 3.1** (contrato-primeiro) e gerar
    *stubs* Java/TS/Python --- congela os contratos do §5.

-   *Definir formalmente o contrato do* tick (esquema de estado de
    entrada/saída e a fronteira determinístico×IA do §8) --- é o coração
    técnico.

-   *Escrever* migrations *do Postgres e os* schemas *do Mongo a partir
    do §6; alinhar o esquema de telemetria à Matriz de Evidências*
    (Modelagem §8).

-   *Implementar o* vertical slice *(F3)* de uma era end-to-end antes de
    ampliar --- valida desempenho (RSK-02) e tutor (RSK-03).

-   **Registrar ADRs** para as decisões-chave (monólito modular + IA;
    Three.js/WebGPU; poliglota; LLM local).

-   *Elaborar um* threat model e a estratégia de testes (unit,
    integração, contrato, E2E, desempenho em Chromebook).

-   **Configurar observabilidade** (Prometheus/Grafana) com métricas
    técnicas **e** pedagógicas desde o início.

> ***Consistência garantida:** toda a arquitetura deriva dos artefatos
> anteriores (RF/RNF/RT, Modelagem Pedagógica, GDD), sem alteração de
> escopo, e mantém a rastreabilidade Requisito → Componente → API → Dado
> → Evidência pedagógica.*

*Fim do Documento de Arquitetura de Software. Pronto para servir como
especificação técnica direta da implementação, preservando coerência com
a proposta, o resumo executivo, o ERS, a Modelagem Pedagógica e o GDD.*

### 10.1 Estado Atual da Implementação

Seção incorporada na versão 2.0. Registra o que já foi efetivamente
construído, distinguindo-o do que permanece planejado.

### 17.1 Infraestrutura e monorepo

-   Monorepo estruturado com pnpm workspaces e Turborepo, com TypeScript
    e lint compartilhados.

-   Ambiente de desenvolvimento em Docker Compose com PostgreSQL
    (pgvector), MongoDB, Redis, MinIO e Ollama.

-   Scripts de inicialização criando a extensão vector e os schemas
    platform e rag.

-   Migração baseline do platform-api via TypeORM, com 18 tabelas fiéis
    ao modelo relacional do dossiê.

-   Migração baseline do schema rag via Alembic, com a tabela de
    embeddings.

-   Pacotes compartilhados (config, api-contracts, ui, shared-types) e
    guias de desenvolvimento e onboarding.

### 17.2 Serviço de IA (walking skeleton validado)

-   Arquitetura hexagonal com portas e adaptadores e raiz de composição
    explícita.

-   Motor de regras causais determinístico, com cascata limitada; regras
    em YAML versionado, revisável por especialista sem novo deploy.

-   Ingestão de telemetria com gate de consentimento embutido,
    bloqueando a coleta sem consentimento (RF-071/RNF-009).

-   Camada HTTP versionada com erros conforme RFC 7807 e métricas
    expostas ao Prometheus.

-   Portão de qualidade verde: ruff e mypy \--strict limpos, testes
    aprovados com cobertura de 95%.

+-----------------------------------------------------------------------+
| **Decisão de sequenciamento da IA --- registro formal**               |
|                                                                       |
| • O feedback causal do MVP é entregue por um motor de regras          |
| determinístico, não pelo tutor LLM.                                   |
|                                                                       |
| • A hipótese pedagógica central (aprender por causa e efeito) precisa |
| ser testável já no MVP; o tutor LLM+RAG está previsto para o          |
| Incremento 6.                                                         |
|                                                                       |
| • O motor de regras produz saída no mesmo contrato do LLM futuro,     |
| permitindo substituição sem quebra.                                   |
+-----------------------------------------------------------------------+

### 10.2 Marcos do Projeto

Marcos de decisão derivados do roadmap incremental, distintos de sprints
e releases por representarem pontos de comprovação.

  --------------------- -------------------------------------- -------------
  **Marco**             **Comprovação exigida**                **Release**

  **M0 --- Fundação**   Monorepo, CI/CD, autenticação e        v0.1
                        ambiente de ponta a ponta              

  **M1 --- MVP          Ciclo completo: criar planeta, clima,  v0.2
  jogável**             vida básica, salvar, com feedback      
                        causal                                 

  **M2 --- Validação    Playtest confirmando engajamento e     v0.2
  pedagógica**          aprendizagem por causa e efeito        

  **M3 --- Mundo vivo** Motor ambiental, ecossistemas, eventos v0.3
                        e trade-offs completos                 

  **M4 --- Inteligência Tutor LLM+RAG ancorado ao estado real, v0.5
  ativa**               com guardrails                         

  **M5 --- Avaliação    Stealth assessment inferindo           v0.5
  invisível**           competências mapeadas à BNCC           

  **M6 --- Valor para o Docente cria missão BNCC e acompanha a v1.0
  professor**           turma sem assistência                  

  **M7 --- Pronto para  Acessibilidade, PWA/offline, LGPD,     v1.0
  piloto**              desempenho e segurança nas metas       

  **M8 --- Piloto       Uso real em turma com dados de         pós-v1.0
  validado**            aprendizagem coletados                 
  --------------------- -------------------------------------- -------------

### 10.3 Registro de Decisões Arquiteturais (ADRs)

Implementação da recomendação do próprio dossiê de registrar as
decisões-chave.

A versão 3.0 acrescenta ao registro as decisões de arquitetura de projeto e **resolve a pendência de numeração por definição de escopo** (em vez de fusão): a série **projeto/arquitetura** (prefixo `ADR-ARCH-`) cobre decisões transversais entre Engines/serviços; a série **serviço** cobre decisões internas a um serviço. Novas entradas:

- **ADR-ARCH-0001 — Arquitetura de Engines.** Engines como módulos in-process; três camadas; dois canais de comunicação; superação do AG de fitness global por evolução emergente. *Benefício:* domínios científicos isolados e testáveis, Tutor auditável, determinismo/replay preservados, sem custo de microsserviços.
- **ADR-ARCH-0002 — Observabilidade por Design.** Quatro pilares sobre o Event Store; explicabilidade como requisito de schema; três públicos como projeções; granularidade agregada por padrão. *Benefício:* plataforma explicável e depurável por replay, com separação de responsabilidades preservada.


  -------------------------- -------------------------- ---------------------
  **Decisão**                **Justificativa**          **Benefício**

  **Migração Java/Spring →   Equipe agora               Produtividade,
  Node.js/NestJS**           TypeScript-cêntrica        unificação de
                                                        linguagem, tempo real

  **Persistência poliglota   Naturezas de dados         Integridade onde é
  (Postgres+Mongo+Redis)**   distintas: transacional ×  crítica;
                             estado mutável             flexibilidade onde é
                                                        necessária

  **Separação por schema     Isolar migrações de        Fronteira de
  (platform / rag)**         TypeORM e Alembic sem      responsabilidade
                             duplicar servidor          materializada no
                                                        banco

  **Feedback causal por      A hipótese pedagógica      Validação antecipada;
  regras antes do LLM**      precisa ser testável no    contrato compatível
                             MVP                        com o LLM futuro

  **Barramento escalonado    Evitar infraestrutura nova Simplicidade
  (Redis Streams → NATS)**   antes da necessidade       operacional inicial
                             medida                     (mitiga RSK-07)

  **ORM TypeORM (supera      Estado real do código;     Sem retrabalho;
  recomendação anterior de   baseline de 18 tabelas     modelo mental próximo
  Prisma)**                  aplicada                   ao JPA
  -------------------------- -------------------------- ---------------------

+-----------------------------------------------------------------------+
| **Pendência --- numeração de ADRs**                                   |
|                                                                       |
| • Coexistem duas séries iniciando em 0001 (nível de projeto e interna |
| ao ai-sim-service).                                                   |
|                                                                       |
| • Recomenda-se unificar em série única sob docs/adr/ ou prefixar por  |
| escopo (PROJ-, AISIM-) antes que a ambiguidade se torne custosa.      |
+-----------------------------------------------------------------------+

### 10.4 Arquitetura de Engines (atualização v3)

A versão 3.0 formaliza a evolução da "arquitetura de motores" para uma **arquitetura de Engines**: cada Engine representa um **domínio científico independente**, com responsabilidade única, contratos bem definidos, eventos próprios, testes, documentação, observabilidade e replay determinístico. Um Engine **nunca** acessa o estado interno de outro nem contém conhecimento pedagógico ou de outro domínio (o Climate Engine simula clima; ele não sabe que uma seca será usada numa atividade escolar). Esta seção resume a decisão; o registro formal está no **ADR-ARCH-0001** (série de projeto) e os contratos de implementação na **Especificação da Moldura Comum de Engines**.

A adoção segue **quatro emendas** de engenharia, que preservam o benefício do modelo sem recair no risco de microsserviços prematuros (RSK-07):

- **Engines são módulos in-process, não serviços.** Cada Engine é um módulo dentro de um único artefato implantável (o `ai-sim-service`), comunicando-se por um barramento em memória, com as costuras prontas para extrair um Engine para serviço próprio se e quando a escala exigir. Coerente com o monólito modular (§10.1) e com a equipe enxuta.

- **Dois canais de comunicação, não "tudo é evento".** O acoplamento físico contínuo (vulcanismo → CO2 → efeito estufa → temperatura → gelo → albedo) trafega por **World-State + deltas por tick** (ordenado, síncrono, determinístico); as ocorrências notáveis (erupção, especiação, extinção, início de seca) trafegam por **eventos discretos** (append-only, no Event Store). Consumidores (Tutor, Education, Analytics) assinam apenas os eventos.

- **Três camadas, não um template único.** Camada de **Simulação** (loop determinístico por tick): Planet (orquestrador), Geology, Atmosphere, Climate, Hydrology, Chemistry, Evolution, Ecology, Resource, Event. Camada de **Plataforma/Infra** (Ports & Adapters): Persistence, Observability/Event Store. Camada de **Consumidores** (read-side, assíncronos, que nunca recalculam ciência): Analytics, Education, AI Tutor.

- **Projetar a moldura comum + fatia vertical antes de escalar.** Especifica-se de uma vez o que é comum a todo Engine (interface, envelope de evento, protocolo de tick, contrato de world-state, contrato de observabilidade, replay) e valida-se com a fatia vertical Geology → Atmosphere → Climate, antes de crescer em largura.

**Evolução emergente supera o algoritmo genético de fitness global.** O RF-031, originalmente baseado em AG com função de fitness global, fica formalmente superado: a evolução deve **emergir da interação local organismo↔ambiente** (sobrevivência e reprodução individuais, no espírito da vida artificial), sem otimização teleológica global. Justificativa científica (fitness global é teleológico e reforça a concepção equivocada de que a evolução "mira" um ótimo), educacional (produz eventos causais legíveis, como "espécie X extinta porque a tolerância térmica foi excedida", insumo direto do Tutor) e computacional (exige o tick ordenado e determinístico por seed para preservar o replay bit-a-bit já implementado). O ABM ecológico (RF-032) permanece, subordinado à mesma seed.

### 10.5 Observabilidade por Design (atualização v3)

Por ser uma **plataforma educacional**, o ECOSFERA não precisa apenas funcionar: precisa ser **explicável, auditável e depurável**. Nenhum mecanismo relevante pode ser caixa-preta, e a IA Tutora **não infere o estado inspecionando objetos em memória** — ela consome uma **trilha de eventos**. A observabilidade é, portanto, requisito de arquitetura, obrigatório desde o início no Evolution Engine e padrão para todos os Engines de simulação. Registro formal: **ADR-ARCH-0002**.

**Princípio fundamental (invariante).** A simulação nunca depende dos logs; os logs dependem da simulação. Nenhuma decisão científica é tomada consultando logs, métricas ou traces. A **emissão** de eventos é determinística (mesma seed → mesmos eventos, na mesma ordem); a **consumação** (logs, métricas, traces, projeções) é assíncrona e fora do loop determinístico, logo **não afeta o replay**. Medir tempo de tick é permitido como métrica lateral, mas jamais realimenta a simulação.

**Quatro pilares sobre uma fonte de verdade.** O **Event Store** (append-only, determinístico, replayável) é a fonte única. Dela derivam: (1) **Events** — os domain events; (2) **Logs** — estruturados, como projeções dos eventos; (3) **Metrics** — Prometheus (tempo por Engine/tick, organismos processados, eventos emitidos, memória); (4) **Traces** — OpenTelemetry, encadeando a cadeia causal completa (ex.: mudança ambiental → declínio populacional → extinção).

**Três públicos = três projeções, não três emissores.** A visão Científica é projeção filtrada dos eventos; a visão Técnica/Diagnóstico reúne métricas, traces e eventos de diagnóstico; a **visão Educacional é renderizada pelos consumidores** (Education/AI Tutor) a partir dos eventos, e **não emitida pelo Engine científico**. O Engine emite eventos neutros e estruturados com metadados causais suficientes (o quê, quando, onde, quais organismos, quais fatores ambientais, quais genes, quais recursos, quais consequências, com `cause_code` como enum, nunca prosa pedagógica); a frase "a espécie Alpha perdeu população porque houve escassez de água por cinco ciclos" é produzida pelo Tutor. Assim a explicabilidade vira **requisito de schema do evento**, preservando a separação de responsabilidades.

**Adaptação à realidade do projeto.** Adotam-se desde já: Event Store como fonte de verdade, replay por seed, eventos com metadados causais, os quatro pilares, métricas por Engine, traces da cadeia causal e **orçamento por tick** (excedeu o teto configurável → emite evento de diagnóstico). Adaptam-se: a visão Educacional para projeção do consumidor; a granularidade para **agregada por padrão** (deltas por espécie), com detalhe por-organismo apenas sob demanda (evita explosão de eventos); e o diagnóstico profundo (cache/CPU/detecção de código quadrático) para métricas+traces agora e profilers on-demand em desenvolvimento. Adiam-se, com o fluxo de diagnóstico já aberto para consumo futuro: detecção automática de anomalias além do orçamento e auto-otimização por IA.

# PARTE VI — Plano de Execução


## 11 Plano de Desenvolvimento Incremental

### 1. Estratégia geral

### 1.1 Comparação de metodologias

  -------------------------------------------------------------------------
  **Metodologia**         **Aderência ao projeto**  **Limitação**
  ----------------------- ------------------------- -----------------------
  **Scrum**               Cadência, papéis e        Rígido demais para
                          cerimônias dão ritmo e    equipe muito enxuta;
                          previsibilidade; bom para overhead de cerimônias
                          stakeholders              
                          (escola/fomento)          

  **Kanban**              Fluxo contínuo, ótimo     Pouca previsibilidade
                          para                      de prazo; fraco para
                          pesquisa/experimentação e planejar releases
                          bugs                      

  **Scrumban**            Combina cadência do Scrum Requer disciplina de
                          (sprints, review, retro)  time
                          com fluxo/limites-WIP do  
                          Kanban                    

  **Lean**                Foco em valor, redução de É filosofia, não
                          desperdício,              processo operacional
                          *build-measure-learn*     completo
  -------------------------------------------------------------------------

### 1.2 Decisão: **Scrumban orientado por Lean Startup**

Recomenda-se **Scrumban** --- cadência leve de Scrum (sprints, review,
retrospectiva) com **quadro Kanban e limites de WIP** --- sob a
mentalidade **Lean Startup** (cada incremento é um experimento
*build-measure-learn* validado com usuários).

**Justificativa.** A equipe é enxuta e o projeto tem forte componente de
**pesquisa/experimentação** (simulação, IA, pedagogia) --- o fluxo
Kanban absorve a incerteza; a cadência de sprints garante **entregas
demonstráveis** e disciplina de validação com professores/alunos (reduz
risco cedo). É o meio-termo entre a previsibilidade do Scrum e a
flexibilidade do Kanban.

### 1.3 Parâmetros

-   **Sprints de 2 semanas** (equilíbrio entre feedback rápido e entrega
    significativa).

-   **Entregáveis por sprint:** incremento executável em *staging*,
    testes passando, demo curta.

-   **Revisões (review):** ao fim da sprint, demo do executável; a cada
    2--3 sprints, **validação com professores/alunos** (playtest).

-   **Retrospectivas:** ao fim de cada sprint (melhoria contínua).

-   **WIP limitado** por coluna do quadro (evita trabalho pela metade;
    reduz retrabalho).

-   **Refinamento contínuo** do backlog (mid-sprint), no espírito
    Kanban.

### 2. Definição do MVP

### 2.1 Escopo do MVP (= Incremento 1, sobre a Fundação)

O MVP é o ***vertical slice*** recomendado no GDD e na Arquitetura (Fase
F3): **uma volta completa do core loop** numa era inicial.

  ------------------------------------------------------------------------
  **Bloco**               **Funcionalidades**      **RF/RNF**
  ----------------------- ------------------------ -----------------------
  **Planeta**             Geração do planeta;      RF-011, RF-012
                          configuração inicial;    
                          parâmetros ambientais    

  **Clima**               Temperatura, água,       RF-014 (subconjunto)
                          atmosfera, ciclo         
                          climático simples        

  **Vida básica**         Surgimento das primeiras RF-014/031/032
                          espécies; crescimento    (simplificados)
                          populacional; relação    
                          ambiente↔sobrevivência   

  **Interface**           Visualização inicial do  RF-051/053/055, RF-021
                          planeta 3D; controles    (básico)
                          básicos; painel de       
                          indicadores              

  **Persistência**        Salvar e carregar        RF-015
                          simulação                

  **(Fundação mínima)**   Login, 1 turma, 1 aluno; RF-003/005/008
                          consentimento *stub*     

  **(Recomendação)        Explicação por           prepara RF-033/039
  Feedback causal         **regras** (\"CO2↑ →     
  simples**               temperatura↑\") ---      
                          ainda **sem LLM**        
  ------------------------------------------------------------------------

### 2.2 Por que essas funcionalidades bastam para validar o projeto

O MVP testa as **hipóteses de maior risco** do projeto de uma só vez:

-   **H1 --- Engajamento:** criar e ver um planeta \"viver\" prende o
    aluno? (valida a fantasia do GDD §1).

-   **H2 --- Aprendizagem por causalidade:** o loop
    *agir→observar→entender* ensina relações de causa e efeito? (valida
    a retórica procedural --- daí a **recomendação de incluir um
    feedback causal simples já no MVP**, mesmo baseado em regras; sem
    isso, a hipótese pedagógica central não é testável).

-   **H3 --- Desempenho:** render 3D + simulação rodam de forma fluida
    em **Chromebook** (RNF-001)? (mitiga RSK-02, o maior risco técnico).

-   **H4 --- Core loop:** o ciclo do GDD §2 é divertido e compreensível?

Com esses cinco blocos há um software **jogável, demonstrável e
mensurável** --- suficiente para playtests com professores/alunos e para
decisões de continuidade (Lean Startup). Tudo o que vem depois
**aprofunda** (mais subsistemas, IA, avaliação), não **viabiliza** ---
logo, não pertence ao MVP.

> ***Recomendação de consultor:** instrumentar **telemetria mínima**
> (RF-071) já no MVP --- mesmo sem o stealth assessment completo ---
> para que os playtests gerem dados de engajamento/uso desde o dia 1.
> Custo baixo agora, valor alto para validação.*

EOF echo \"Etapas 1-2 anexadas.\"

### 3. Roadmap incremental

### 3.1 Análise da sequência proposta e melhorias (recomendações de
consultor)

A sequência sugerida (MVP → Ambiental → Ecossistemas → Eventos →
Trade-offs → IA → Stealth → Professor → Polimento) é sólida e respeita o
caminho crítico da Arquitetura. Proponho **quatro ajustes** que reduzem
risco sem alterar o escopo:

50. **Adicionar o Incremento 0 (Fundação).** Infra, CI/CD, auth/turma e
    esqueleto dos repositórios precisam existir antes do MVP --- hoje
    estavam implícitos.

51. **Antecipar feedback causal e uma intervenção mínima.** A mecânica
    pedagógica central (causa-efeito por ação) deve ser testável cedo:
    incluir feedback causal por **regras** no MVP e uma **intervenção
    simples com trade-off** já no Incremento 2 (o sistema completo de
    trade-offs permanece no Inc 5). Sem isso, a hipótese pedagógica só
    seria validada muito tarde.

52. **Instrumentar telemetria desde o Inc 1.** O *stealth* completo fica
    no Inc 7, mas a **coleta de eventos** (RF-071) deve começar já,
    alimentando playtests.

53. **Tratar acessibilidade, segurança e LGPD como transversais, não
    como \"polimento\".** Consentimento (RF-008) é **bloqueante** antes
    de qualquer piloto; acessibilidade (RNF-014--020) entra no **DoD de
    cada incremento**. O Inc 9 passa a ser *hardening*/otimização, não a
    \"primeira vez\" que se pensa nisso.

### 3.2 Incrementos

**Incremento 0 --- Fundação** *(recomendado)*

-   **Objetivo:** base executável para todo o resto.

-   **Funcionalidades:** monorepo + CI/CD; auth (JWT/RBAC);
    escola/turma/aluno mínimos; consentimento *stub*; observabilidade
    básica.

-   **Requisitos:** RF-001--005, RF-008; RNF-006/007/025; RT-006.

-   **Critérios de aceitação:** login funcional por papel; turma criada;
    *pipeline* verde; deploy em *staging*.

-   **Dependências:** ---. **Riscos:** subestimar setup de infra
    (mitigar com Docker Compose desde o dia 1).

**Incremento 1 --- MVP (Planeta + Clima + Vida Básica)**

-   **Objetivo:** validar H1--H4 (engajamento, causalidade, desempenho,
    core loop).

-   **Funcionalidades:** criação/config do planeta; clima simples; vida
    básica; render 3D; painel; salvar/carregar; **feedback causal por
    regras**; **telemetria mínima**.

-   **Requisitos:** RF-011/012/014/015/021/051/053/055/071(básico);
    RNF-001.

-   **Critérios de aceitação:** aluno cria planeta, avança o tempo, vê
    vida surgir e recebe explicação causal; ≥30 FPS em Chromebook;
    salvar/carregar fiel.

-   **Dependências:** Inc 0. **Riscos:** desempenho 3D (RSK-02) ---
    *spike* de render antecipado.

**Incremento 2 --- Motor Ambiental**

-   **Objetivo:** enriquecer o mundo físico e completar o loop com uma
    intervenção.

-   **Funcionalidades:** relevo, biomas, oceanos, recursos naturais;
    **1ª intervenção simples com trade-off** *(recomendado)*.

-   **Requisitos:** RF-014 (geologia/oceano/hidrologia); RF-017/018
    (mínimo).

-   **Critérios de aceitação:** relevo/biomas coerentes; intervenção
    gera efeito + e − explicado.

-   **Dependências:** Inc 1. **Riscos:** acoplamento entre subsistemas
    ficar instável (RSK-01) --- testes de sanidade.

**Incremento 3 --- Ecossistemas**

-   **Objetivo:** vida emergente crível.

-   **Funcionalidades:** cadeia alimentar, biodiversidade, reprodução,
    adaptação (ABM/AG simplificados).

-   **Requisitos:** RF-031/032; M6/M7.

-   **Critérios de aceitação:** oscilações predador-presa observáveis;
    espécies catalogadas (códex).

-   **Dependências:** Inc 2. **Riscos:** custo computacional do ABM
    (mitigar: limites/otimização; parte no cliente).

**Incremento 4 --- Sistema de Eventos**

-   **Objetivo:** tensão e narrativa emergente.

-   **Funcionalidades:** terremotos, vulcões, meteoros, mudanças
    climáticas; propagação em cascata; Diretor básico.

-   **Requisitos:** RF-019/020; proposta §8.

-   **Critérios de aceitação:** evento altera estado e cascateia;
    telegrafia prévia.

-   **Dependências:** Inc 2/3. **Riscos:** eventos
    \"injustos\"/aleatórios demais (balanceamento).

**Incremento 5 --- Sistema de Trade-offs (completo)**

-   **Objetivo:** consolidar o núcleo pedagógico de decisão.

-   **Funcionalidades:** intervenções humanas, economia de ações
    (recursos limitados), impactos ambientais (GDD §4/§5).

-   **Requisitos:** RF-017/018; M8.

-   **Critérios de aceitação:** recursos escassos forçam priorização;
    cada ação tem consequência + e − rastreável.

-   **Dependências:** Inc 2/4. **Riscos:** balanceamento da economia
    (playtests + parâmetros configuráveis).

**Incremento 6 --- Motor de IA (tutor pleno)**

-   **Objetivo:** mediação inteligente.

-   **Funcionalidades:** tutor **LLM+RAG**, feedback inteligente,
    recomendações, personalização/adaptação.

-   **Requisitos:** RF-033/034/035/036/037/039/040.

-   **Critérios de aceitação:** explicações ancoradas ao estado real
    (RAG), apropriadas à idade; guardrails ativos.

-   **Dependências:** Inc 1 (feedback por regras) + estado rico (Inc
    2--5). **Riscos:** alucinação (RSK-03) --- avaliação de fidelidade
    do RAG; custo/latência (LLM local).

**Incremento 7 --- Stealth Assessment**

-   **Objetivo:** avaliar sem interromper.

-   **Funcionalidades:** coleta de evidências (já instrumentada),
    inferência de competências (rede bayesiana), indicadores de
    aprendizagem; Perfil Cognitivo.

-   **Requisitos:** RF-071/072/073/076; Modelagem §7/§8.

-   **Critérios de aceitação:** perfil por competência atualiza com
    evidências; mapeado à BNCC.

-   **Dependências:** Inc 1 (telemetria), Inc 5 (evidências ricas de
    trade-off). **Riscos:** validade das inferências (calibrar com
    pré/pós-teste).

**Incremento 8 --- Painel do Professor**

-   **Objetivo:** valor para o docente.

-   **Funcionalidades:** dashboards, relatórios, progresso por
    competência, recomendações da IA, missões BNCC, alertas.

-   **Requisitos:** RF-061--067/077; Modelagem §11.

-   **Critérios de aceitação:** professor cria missão BNCC e acompanha a
    turma; exporta relatório.

-   **Dependências:** Inc 7. **Riscos:** baixa adoção docente (RSK-08)
    --- co-design e onboarding.

**Incremento 9 --- Hardening e Polimento**

-   **Objetivo:** qualidade de produto para piloto em escala.

-   **Funcionalidades:** desempenho/otimização, UX, **acessibilidade
    plena** (auditoria WCAG), **PWA/offline**, LGPD (retenção,
    direitos), LTI, observabilidade pedagógica.

-   **Requisitos:** RNF-014--021/012/013; RF-009/078.

-   **Critérios de aceitação:** metas de RNF atingidas; piloto pronto.

-   **Dependências:** Inc 8. **Riscos:** dívida técnica acumulada ---
    mitigada por NFR contínuo nos incrementos anteriores.

### 4. Planejamento das sprints

Sprints de **2 semanas**. Estimativa total ≈ **35 sprints** (\~16--18
meses de desenvolvimento + validação), coerente com o cronograma da
proposta (18--24 meses). Detalham-se abaixo os primeiros incrementos; os
demais são resumidos por sprint.

### 4.1 Incremento 0 --- Fundação (2 sprints)

**Sprint 0.1 --- Setup**

-   *Objetivo:* projeto executável \"vazio\" com CI/CD.

-   *Backlog/US:* US-10 (deploy Docker/LTI --- base).

-   *Tarefas técnicas:* monorepo; Docker Compose (Postgres/Mongo/Redis);
    pipelines GitHub Actions; esqueleto
    platform-api/ai-sim-service/web-client.

-   *Tarefas pedagógicas:* consolidar matriz de rastreabilidade
    (Requisito→Competência→Evidência).

-   *Entregável:* \"hello world\" dos 3 serviços em *staging*.

**Sprint 0.2 --- Identidade & Turma**

-   *Objetivo:* autenticação e estrutura escolar mínima.

-   *US:* US-06/US-11 (professor/consentimento --- base).

-   *Técnicas:* JWT/RBAC (Spring Security); CRUD escola/turma/aluno;
    consentimento *stub* (RF-008).

-   *Pedagógicas:* validar papéis/permissões com um professor parceiro.

-   *Entregável:* login por papel + turma criada.

### 4.2 Incremento 1 --- MVP (4 sprints)

**Sprint 1.1 --- Planeta (criação):** RF-011/012; US-01. Técnicas:
modelo de domínio Planeta, endpoint POST /planets, validação de
parâmetros. Pedagógicas: revisar faixas de parâmetros com especialista.
Entregável: criar/persistir planeta. **Sprint 1.2 --- Render 3D:**
RF-051/053/055; US-01. Técnicas: cena Three.js (WebGPU→WebGL2), câmera,
HUD básico; *spike* de desempenho em Chromebook (RSK-02). Entregável:
planeta visível e navegável. **Sprint 1.3 --- Clima + tick:**
RF-013/014(subset)/021/023; US-02. Técnicas: orquestrador de *tick*,
clima simples, séries; WebSocket de *delta*. Entregável: avançar o tempo
e ver o clima mudar. **Sprint 1.4 --- Vida + feedback + salvar:**
RF-014/031/032(simpl.)/015/071(básico); US-02/US-04. Técnicas: vida
básica, salvar/carregar, **feedback causal por regras**, telemetria
mínima. Pedagógicas: **1º playtest** com alunos. Entregável: **MVP
jogável e demonstrável**.

### 4.3 Incrementos 2--9 (resumo por sprints)

  ----------------------------------------------------------------------------------------
  **Inc**        **Sprints**    **Foco das sprints**    **US principais**   **Entregável
                                                                            de validação**
  -------------- -------------- ----------------------- ------------------- --------------
  2 · Ambiental  3              Relevo/biomas;          US-03/US-07         Mundo físico
                                oceanos/recursos; 1ª                        rico +
                                intervenção+trade-off                       intervir

  3 ·            4              ABM populacional;       US-14               Ecossistema
  Ecossistemas                  cadeia trófica;                             vivo e
                                evolução/adaptação;                         emergente
                                códex                                       

  4 · Eventos    3              Catálogo de eventos;    US-14               Crises e
                                propagação; Diretor                         narrativa
                                básico                                      emergente

  5 · Trade-offs 3              Economia de ações;      US-03               Núcleo de
                                intervenções completas;                     decisão
                                balanceamento                               jogável

  6 · IA (tutor) 5              RAG; tutor LLM;         US-04               Tutor explica
                                feedback inteligente;                       causalidade
                                conselheiros; adaptação                     

  7 · Stealth    4              Pipeline de evidências; US-08/US-13         Competências
                                rede bayesiana; Perfil                      inferidas
                                Cognitivo; mapa BNCC                        

  8 · Professor  4              Missões BNCC;           US-06/US-08/US-09   Painel útil ao
                                dashboards; alertas;                        docente
                                relatórios                                  

  9 · Hardening  3              Acessibilidade;         US-05/US-12         Produto pronto
                                PWA/offline; LGPD; LTI;                     para piloto
                                otimização                                  
  ----------------------------------------------------------------------------------------

**Cronograma (macro):**

Meses: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16

Inc: \[0 \]\[ 1 (MVP) \]\[ 2 \]\[ 3 \]\[ 4 \]\[ 5 \]\[ 6 \]\[ 7 \]\[ 8
\]\[ 9 \]

Valid.: ▲playtest1 ▲pt2 ▲pt3 ▲pt4-tutor ▲pt5 ▲piloto

### 5. Priorização técnica (WSJF + MoSCoW)

**Escolha (justificativa).** Usa-se **MoSCoW** (já definido no ERS §12)
para **escopo** (o que entra no MVP) e **WSJF --- Weighted Shortest Job
First** para **ordenar** os incrementos. WSJF = **Custo de Atraso ÷
Tamanho do Job**, onde Custo de Atraso = valor ao usuário + criticidade
temporal + **redução de risco/viabilização**. É superior a MoSCoW puro
para *sequenciamento* e mais simples/objetivo que RICE para uma equipe
pequena.

  -------------------------------------------------------------------------------------------
  **Item**       **Valor**   **Criticid.**   **Redução   **Tamanho**   **WSJF**   **Ordem**
                                             de risco**                           
  -------------- ----------- --------------- ----------- ------------- ---------- -----------
  Fundação (Inc  3           5               8           3             **5,3**    1
  0)                                                                              

  MVP (Inc 1)    9           8               9           5             **5,2**    2

  Motor          6           5               5           3             **5,3**    3
  Ambiental (Inc                                                                  
  2)                                                                              

  Ecossistemas   7           4               5           5             **3,2**    4
  (Inc 3)                                                                         

  Eventos (Inc   6           3               4           3             **4,3**    5
  4)                                                                              

  Trade-offs     9           6               6           3             **7,0**    6
  (Inc 5)                                                                         

  IA/Tutor (Inc  8           5               7           8             **2,5**    7
  6)                                                                              

  Stealth (Inc   8           5               6           5             **3,8**    8
  7)                                                                              

  Professor (Inc 9           6               5           5             **4,0**    9
  8)                                                                              

  Hardening (Inc 7           7               5           3             **6,3**    10
  9)                                                                              
  -------------------------------------------------------------------------------------------

**Por que primeiro?** Fundação e MVP lideram por **altíssima redução de
risco/viabilização** (habilitam tudo e testam as hipóteses críticas) com
job pequeno-médio. Trade-offs tem WSJF alto (valor pedagógico central,
job pequeno) --- por isso a recomendação de antecipar uma versão mínima.
IA/Tutor, apesar de valioso, tem **job grande**, ficando após o estado
do mundo estar rico o suficiente para o RAG ancorar (senão, retrabalho).
*(A ordem cronológica final respeita dependências --- §6 --- que às
vezes sobrepõem-se ao WSJF puro.)*

### 6. Mapa de dependências

Consolida o mapa do ERS (§13) e o roadmap da Arquitetura (§14).

Inc0 Fundação ─► Inc1 MVP ─► Inc2 Ambiental ─► Inc3 Ecossistemas ─► Inc4
Eventos

(auth,infra) (loop+3D) (relevo/1ª (ABM/AG) (propagação)

│ intervenção) │

│ └────────────────┼──► Inc5 Trade-offs ─┐

│ │ │

telemetria(Inc1) ──────────────────────────────────┐│ │

▼▼ ▼

Inc6 IA/Tutor ◄── (estado rico) Inc7 Stealth

(RAG precisa de estado) (precisa evidências

de trade-off)

│

▼

Inc8 Professor ─► Inc9 Hardening

-   **Caminho crítico:** Inc0 → Inc1 → Inc2 → (Inc3/Inc5) → Inc6/Inc7 →
    Inc8. O núcleo RF-011→013→014 (dentro do MVP) é o gargalo-mestre:
    quase tudo depende dele.

-   **Módulos críticos:** Orquestrador de *tick* (base de toda
    simulação), pipeline de telemetria (base do stealth), RAG/estado
    (base do tutor).

-   **Gargalos/riscos de sequência:** IA/Tutor antes de estado rico →
    retrabalho (por isso vem após Inc 2--5); Stealth antes de trade-offs
    → evidências pobres (por isso após Inc 5); consentimento (RF-008)
    **bloqueia** pilotos com dados reais.

### 7. Organização dos repositórios

Decisão: monorepo poliglota, reorganizado por unidade implantável (e não
por linguagem, já que duas das três unidades compartilham TypeScript).
Ferramentas: pnpm workspaces + Turborepo (TS) e uv (Python).

ecosfera/

apps/web-client/ \# Next.js + React + TS + Three.js (SPA/PWA)

apps/platform-api/ \# NestJS: identity, education, assessment,
orchestration

services/ai-sim-service/ \# Python/FastAPI (simulation_engine, ai_engine
internos)

packages/config · api-contracts · ui · shared-types

infra/compose · infra/docker \# compose de dev e scripts de init

docs/ \# dossiê, ADRs e artefatos oficiais

apps/ concentra as unidades executáveis; services/ o serviço Python (com
simulation_engine e ai_engine como pacotes internos, promovíveis a
distribuíveis se escalarem); packages/ guarda os contratos (fonte única
de verdade); infra/ e docs/ isolam operação e documentação.

### 8. Estratégia Git

  ---------------------------------------------------------------------------
  **Fluxo**               **Aderência**               **Veredito**
  ----------------------- --------------------------- -----------------------
  **Git Flow**            Muitos branches             Pesado demais para
                          (develop/release/hotfix);   entregas contínuas
                          bom para *releases* longos  
                          e versionados               

  **GitHub Flow**         main + *feature branches*   Bom, porém sem
                          curtas + PR; simples        disciplina de *trunk*

  **Trunk-Based           *Commits* frequentes na     **Recomendado** ---
  Development (TBD)**     *trunk*, branches           casa com CI/CD e
                          curtíssimas, *feature       entregas incrementais
                          flags*                      
  ---------------------------------------------------------------------------

**Decisão: Trunk-Based Development** (com *feature branches* de vida
curta e *feature flags* para ligar subsistemas gradualmente --- coerente
com o roadmap incremental).

-   **Branches:** main (protegida, sempre implantável); feature/, fix/,
    chore/ (curtas, \<2--3 dias).

-   **Commits:** **Conventional Commits** (feat:, fix:, docs:, test:,
    refactor:) → *changelog* e versionamento automáticos.

-   **Pull Requests:** pequenos, com CI verde obrigatória, descrição
    ligada ao RF/US, *squash merge*.

-   **Code Review:** ≥1 revisor; critérios de estilo/segurança/testes;
    revisão pedagógica quando a mudança tocar avaliação/conteúdo.

-   **Releases:** *tag* semântica ao fim de cada incremento (v0.1-mvp,
    v0.2-ambiental...).

### 9. Integração contínua (CI/CD)

*Pipeline* em **GitHub Actions** (RT/infra), com *gates* de qualidade
por linguagem. Tudo open-source.

  --------------------------------------------------------------------------------
  **Estágio**         **Java                **Python             **Front
                      (backend-java)**      (backend/ai/sim)**   (frontend)**
  ------------------- --------------------- -------------------- -----------------
  **Lint/estático**   Checkstyle/Spotless   Ruff, mypy           ESLint, Prettier,
                                                                 tsc

  **Testes**          JUnit +               pytest               Vitest + Testing
                      Testcontainers                             Library

  **Cobertura**       JaCoCo                pytest-cov           c8

  **Análise**         **SonarQube CE**      idem                 idem
                      (todas as linguagens)                      

  **Build**           imagem Docker         imagem Docker        build estático +
                                                                 Docker (Nginx)

  **Deploy**          *staging* automático; idem                 idem
                      **produção com                             
                      aprovação**                                
  --------------------------------------------------------------------------------

**Fluxo:** PR dispara lint + testes + cobertura + Sonar; *merge* na main
dispara *build* de imagens e *deploy automático em* staging*;* tag *de
release dispara* deploy *de produção com aprovação manual (gate).*
Quality gates: *PR barrado se cobertura cair abaixo do limiar ou se o
Sonar acusar* bugs*/vulnerabilidades novas. Observabilidade
(Prometheus/Grafana) publicada junto ao* deploy.

### 10. Testes durante o desenvolvimento

Segue a **pirâmide de testes** (muitos unitários, menos E2E). A tabela
indica em que incremento cada tipo se torna **obrigatório**.

  -----------------------------------------------------------------------------------
  **Tipo de teste**       **O que cobre**                     **Obrigatório a partir
                                                              de**
  ----------------------- ----------------------------------- -----------------------
  **Unitários**           Regras de domínio, funções puras    Inc 0 (sempre)

  **Integração**          Serviço ↔ banco/fila                Inc 1

  **API/Contrato**        Conformidade com OpenAPI (shared/)  Inc 1

  **Simulação**           *Determinismo por* seed (RF-023),   Inc 1
                          sanidade física, conservação de     
                          massa/energia                       

  **IA (tutor)**          Fidelidade do RAG, ausência de      Inc 6
                          alucinação, *guardrails* (RF-037)   

  **IA (stealth)**        Validade das inferências vs. dados  Inc 7
                          sintéticos/esperados                

  **Pedagógicos**         *Playtests*, IVC da matriz BNCC,    Inc 1 (playtest) → Inc
                          ganho de aprendizagem               9 (piloto)

  **Desempenho**          FPS/latência em Chromebook          Inc 1
                          (RNF-001/002)                       

  **E2E**                 Fluxos completos                    Inc 3
                          (criar→simular→intervir→feedback)   

  **Acessibilidade**      WCAG (contraste, teclado, leitor)   Inc 2 (contínuo)
  -----------------------------------------------------------------------------------

**Regra:** todo incremento entrega testes proporcionais ao seu risco.
Simulação e IA exigem testes **específicos** (determinismo, ancoragem)
porque falhas ali são silenciosas e cientificamente graves (RSK-01/03).

### 11. Definition of Ready / Definition of Done

**Definition of Ready (DoR) --- geral (uma história pode entrar na
sprint quando):**

-   valor claro e ligada a um RF/US/competência; critérios de aceitação
    escritos;

-   estimável e pequena (cabe na sprint); dependências resolvidas;

-   design/UX e impacto pedagógico esclarecidos (se aplicável).

**Definition of Done (DoD) --- geral (uma funcionalidade está concluída
quando):**

-   código revisado e integrado à main; testes (unit+integração) verdes;
    cobertura ≥ limiar;

-   análise estática sem novos *bugs*/vulnerabilidades; **acessibilidade
    básica** verificada (RNF);

-   telemetria instrumentada (quando gerar evidência); documentação/ADR
    atualizada;

-   implantado em *staging* e **demonstrável**.

**DoD específico por incremento (exemplos):**

-   *MVP:* jogável e **playtestado** com alunos; ≥30 FPS em Chromebook.

-   *Simulação (Inc 2--4):* *reprodutível por* seed e aprovada em testes
    de sanidade científica.

-   *IA/Tutor (Inc 6):* explicações **ancoradas por RAG** ao estado
    real; *guardrails* ativos.

-   *Stealth (Inc 7):* inferências **validadas** contra referência;
    mapeadas à BNCC.

-   *Professor (Inc 8):* professor real cria missão BNCC e lê o
    dashboard sem ajuda.

### 12. Indicadores do projeto

  -----------------------------------------------------------------------
  **Categoria**           **Indicador**           **Meta/uso**
  ----------------------- ----------------------- -----------------------
  Ágil                    **Velocity**            Previsibilidade de
                          (pts/sprint)            planejamento

  Ágil                    **Lead/Cycle time**     Fluxo saudável (Kanban)

  Qualidade               **Cobertura de testes** ≥ limiar por serviço
                                                  (gate de CI)

  Qualidade               **Bugs / escape rate**  Defeitos que vazam para
                                                  produção ↓

  Qualidade               **Sonar rating / dívida Manutenibilidade
                          técnica**               (RNF-024)

  Desempenho              **FPS, latência p95**   RNF-001/002
                                                  (Chromebook)

  Desempenho              Latência do tutor (LLM) RNF-003

  Pedagógicos             **Engajamento**         Validação Lean
                          (sessão, retorno,       
                          conclusão)              

  Pedagógicos             **Ganho de aprendizagem Eficácia (piloto)
                          ⟨g⟩** (Hake)            

  Pedagógicos             Fidelidade do RAG /     Confiabilidade da IA
                          qualidade do feedback   
  -----------------------------------------------------------------------

Métricas técnicas via CI + Prometheus/Grafana; pedagógicas via *learning
analytics* (RF-071) e playtests.

### 13. Gestão de riscos

Consolida os riscos do ERS (RSK-01...12) e adiciona os de
desenvolvimento. *Estratégia central:* spikes*/POCs antecipados* para os
riscos técnicos de maior impacto.

  ----------------------------------------------------------------------------------
  **Risco**             **Prob.**      **Impacto**    **Mitigação**   **Quando**
  --------------------- -------------- -------------- --------------- --------------
  Desempenho da         Média          Alto           *Spike* de      **Inc 1**
  simulação/3D em                                     render +        (antecipado)
  Chromebook (RSK-02)                                 orçamento de    
                                                      FPS +           
                                                      *fallback*      
                                                      WebGL2; sim     
                                                      leve no cliente 

  Complexidade/custo da Média          Alto           Feedback por    Inc 1→6
  IA; alucinação                                      regras antes do 
  (RSK-03)                                            LLM; RAG        
                                                      ancorado; LLM   
                                                      local;          
                                                      avaliação de    
                                                      fidelidade      

  Integração entre      Média          Alto           Contratos       Inc 0→1
  módulos/subsistemas                                 OpenAPI         
  (RSK-01)                                            (*shared/*);    
                                                      testes de       
                                                      contrato e      
                                                      sanidade;       
                                                      *vertical       
                                                      slice* cedo     

  Escalabilidade        Baixa-Média    Médio          Sim no cliente; Inc 7→9
                                                      *stateless* +   
                                                      filas; testes   
                                                      de carga        

  Custo do ABM/AG       Média          Médio          Limites de      Inc 3
                                                      agentes;        
                                                      otimização;     
                                                      execução        
                                                      parcial no      
                                                      cliente         

  Balanceamento         Média          Médio          Parâmetros em   Inc 4→5
  (economia/eventos)                                  config/; A/B;   
                                                      playtests       

  Códigos BNCC          Média          Médio          Validação       Inc 7→8
  incorretos (RSK-06)                                 IVC/Delphi da   
                                                      matriz          

  Não conformidade LGPD Média          Muito alto     Consentimento   Inc 0 + Inc 9
  (RSK-05)                                            bloqueante;     
                                                      minimização;    
                                                      anonimização;   
                                                      DPO             

  Escopo excessivo      Alta           Alto           MoSCoW/WSJF     Contínuo
  (RSK-07)                                            rígidos;        
                                                      *feature        
                                                      flags*; futuro  
                                                      fora do MVP     

  Baixa adoção docente  Média          Alto           Co-design;      Inc 8
  (RSK-08)                                            onboarding;     
                                                      missão em       
                                                      minutos         
  ----------------------------------------------------------------------------------

### 14. Evolução tecnológica futura

Após o produto validado (proposta §19), a arquitetura evolutiva
(costuras já previstas) habilita:

-   **Multiplayer colaborativo** --- galáxias compartilhadas de
    planetas.

-   **Agentes inteligentes / civilizações** --- sociedades movidas por
    LLM (LangGraph).

-   **Novas disciplinas e níveis** --- do fundamental à universidade.

-   **Novos planetas / geração procedural** --- mundos e biomas
    infinitos.

-   **LLMs multimodais** --- voz e interpretação de desenhos do aluno.

-   **Realidade Virtual/Aumentada** --- WebXR/A-Frame; \"entrar\" no
    planeta.

-   **Personalização adaptativa avançada** --- trilhas guiadas pelo
    Perfil Cognitivo.

-   **Implantação em borda/offline** --- escolas de baixa conectividade.

### 15. Fundamentação e recomendações

### 15.1 Fundamentação técnica

-   **Lean Startup** (*build-measure-learn*, MVP): cada incremento é um
    experimento validado com usuários --- reduz risco de construir o que
    ninguém usa.

-   **Desenvolvimento Ágil/Incremental**: entregas pequenas, funcionais
    e testáveis; feedback frequente.

-   **CI/CD e DevOps**: integração/entrega contínuas reduzem risco de
    integração (RSK-01) e aceleram feedback.

-   **Arquitetura Evolutiva** (*fitness functions*): NFRs (desempenho,
    acessibilidade) viram *checks* automatizados no *pipeline*, evitando
    degradação.

-   **Extreme Programming (XP)**: testes desde o início, integração
    contínua, *refactoring*.

-   **Serious Games / Design-Based Research**: iteração com playtests e
    validação pedagógica a cada ciclo --- coerente com a Modelagem (§13)
    e a proposta (§17).

### 15.2 Recomendações para iniciar a implementação

54. **Executar a Sprint 0.1** (monorepo + Docker Compose + CI) --- base
    de tudo.

55. **Congelar contratos** em shared/ (OpenAPI 3.1 + JSON Schemas de
    eventos/telemetria) antes de codar em largura.

56. *Definir o contrato do* tick e a fronteira determinístico×IA
    (Arquitetura §8) --- coração técnico.

57. *Fazer o* spike *de render 3D em Chromebook já na Sprint 1.2* ---
    ataca o maior risco (RSK-02) cedo.

58. **Alinhar o esquema de telemetria à Matriz de Evidências**
    (Modelagem §8) desde o MVP.

59. **Implementar o consentimento (RF-008)** antes de qualquer coleta
    real de dados de menor.

60. **Agendar o 1º playtest ao fim do MVP** (Sprint 1.4) com
    professores/alunos parceiros.

61. **Manter a matriz de rastreabilidade**
    Requisito→Competência→Evidência→Componente→Teste como artefato vivo.

Avaliação de viabilidade (síntese do consultor)

  -----------------------------------------------------------------------
  **Dimensão**                        **Nível**
  ----------------------------------- -----------------------------------
  Viabilidade técnica                 **Média-Alta** (stack madura e
                                      open-source; risco concentrado em
                                      desempenho 3D e IA)

  Viabilidade financeira              **Média-Alta** (open-source; LLM
                                      local reduz custo recorrente)

  Complexidade de desenvolvimento     **Alta** (simulação acoplada + IA +
                                      avaliação + jogo)

  Potencial de impacto educacional    **Alto** (interdisciplinaridade
                                      sistêmica alinhada à BNCC)

  Potencial de inovação               **Alto** (stealth assessment + IA
                                      explicável + simulação Gaia
                                      jogável)
  -----------------------------------------------------------------------

*Fim do Plano de Desenvolvimento Incremental. Roteiro ágil pronto para
iniciar a implementação, em consistência com a proposta, o ERS, a
Modelagem Pedagógica, o GDD e a Arquitetura --- priorizando entregas
pequenas, demonstráveis e validáveis com professores e alunos.*

# PARTE VII — Pesquisa, Validação e Encerramento


## 12 Metodologia de Pesquisa

Adota-se uma metodologia mista, combinando três referenciais
complementares:

-   **Design Science Research (DSR)** --- para a construção e avaliação
    rigorosa de um **artefato** (o jogo) que resolve um problema real,
    com ciclos de relevância, projeto e rigor.

-   **Design-Based Research (DBR)** --- para a **iteração pedagógica**
    em contexto real de sala de aula, refinando o design a partir de
    dados de aprendizagem.

-   **Desenho instrucional (ADDIE / Backward Design)** e
    **desenvolvimento incremental ágil (Scrum/Kanban)** para a execução.

**Fases metodológicas:**

62. **Levantamento de requisitos** --- funcionais, pedagógicos (BNCC),
    técnicos e não-funcionais (acessibilidade, LGPD, *offline*);
    entrevistas com professores.

63. **Pesquisa bibliográfica** --- AIED, *serious games*, sistemas
    complexos, ABM, algoritmos evolucionários.

64. **Modelagem pedagógica** --- objetivos de aprendizagem (Bloom/BNCC),
    trilhas por nível, matriz de competências e evidências (para o
    *stealth assessment*).

65. **Game design** --- *core loop*, mecânicas de *trade-off*, economia
    de ações, curva de dificuldade, narrativa das eras.

66. **Arquitetura** --- detalhamento dos módulos, contratos de API,
    modelo de dados.

67. **Desenvolvimento incremental** --- MVP (planeta + clima + vida
    básica) → subsistemas → IA → painel do professor.

68. **Implementação da IA** --- AG, ABM, eventos, tutor LLM+RAG,
    avaliação bayesiana; rastreio com MLflow/W&B.

69. **Desenvolvimento gráfico** --- renderização do planeta, atmosfera,
    oceanos, biomas, desastres; acessibilidade.

70. **Integração** --- cliente-servidor, WebSocket, LMS (LTI).

71. **Testes** --- unitários, integração, desempenho (GPU/latência),
    *playtesting* pedagógico.

72. **Validação com estudantes** --- estudo quase-experimental (grupo
    tratamento × controle) com pré/pós-teste; coleta de *learning
    analytics*; aprovação ética (CEP) e consentimento (TCLE/TALE).

73. **Implantação** --- piloto em escolas parceiras; documentação;
    liberação open-source.

## 13 Equipe Multidisciplinar

  -------------------------------------------------------------------------------
  **Papel**                 **Responsabilidade**    **Perfil**
  ------------------------- ----------------------- -----------------------------
  Coordenador/pesquisador   Direção científica,     Pós-graduação em
                            metodologia,            Computação/Educação
                            publicações             

  Eng. de software backend  Plataforma Java/Spring, Java/Spring, SQL
                            APIs, LTI, dados        

  Dev front-end / 3D        React/Next,             TS, WebGL/WebGPU
                            Three.js/R3F, shaders,  
                            UX técnica              

  Eng. de IA/ML             AG, ABM, RL, LLM+RAG,   Python, PyTorch, LangChain
                            MLOps                   

  Cientista de dados /      *Stealth assessment*,   Estatística/psicometria
  psicometrista             TRI/IRT, *learning      
                            analytics*              

  Game designer             *Core loop*,            Design de jogos
                            balanceamento,          
                            *trade-offs*, eventos   

  Designer instrucional /   Objetivos, trilhas      Educação/Ensino de Ciências
  pedagogo                  BNCC, avaliação         
                            formativa               

  Especialista de conteúdo  Validação científica    Física/Química/Biologia/Geo
  (Ciências)                dos modelos             

  UX/UI designer            Interface,              Design digital
                            acessibilidade (DUA)    

  Artista/técnico 3D        Assets, materiais,      Arte técnica
                            estética do planeta     

  Professores parceiros     Cocriação e validação   Docentes de escolas piloto
                            em sala                 

  QA / DevOps               Testes, CI/CD,          Docker, GitHub Actions
                            infraestrutura          
  -------------------------------------------------------------------------------

Em equipe enxuta, papéis se acumulam (o desenvolvedor-pesquisador pode
cobrir backend + IA + coordenação técnica).

## 14 Avaliação e Métricas de Pesquisa

Avaliação em duas frentes: **do artefato** (usabilidade, desempenho) e
**da aprendizagem** (eficácia educacional), com desenho
quase-experimental.

  -------------------------------------------------------------------------------
  **Dimensão**                **Instrumento / métrica**   **Como se mede**
  --------------------------- --------------------------- -----------------------
  **Aprendizagem**            Pré/pós-teste + inventário  Testes validados;
                              conceitual; **ganho         *stealth assessment*
                              normalizado de Hake ⟨g⟩**;  bayesiano/IRT no jogo
                              comparação com grupo        
                              controle                    

  **Engajamento**             Tempo de sessão,            Telemetria +
                              frequência, taxa de         autorrelato
                              conclusão de desafios,      
                              interações; escala de       
                              engajamento                 

  **Retenção**                Pós-teste diferido (2--4    Reaplicação de teste
                              semanas); curva de          
                              esquecimento                

  **Motivação**               **IMI** (Intrinsic          Questionários validados
                              Motivation Inventory);      
                              modelo **ARCS**; escala de  
                              fluxo                       

  **Tomada de decisão**       Qualidade dos *trade-offs*, *Process data* /
                              revisão de estratégia,      rubricas
                              hipóteses testadas          

  **Pensamento científico**   Ciclo investigativo         Rubricas + *learning
                              (hipótese→teste→revisão);   analytics*
                              qualidade de argumentação   

  **Interdisciplinaridade**   Tarefas de transferência;   Análise de
                              mapas conceituais           mapas/tarefas
                              conectando domínios         

  **Usabilidade**             **SUS** (System Usability   Questionário +
                              Scale); acessibilidade      auditoria
                              (WCAG/DUA)                  

  **Modelos de IA**           Métricas do tutor           MLflow/W&B; validação
                              (fidelidade do RAG,         humana
                              satisfação), do assessment  
                              (acurácia preditiva), do    
                              balanceamento               
  -------------------------------------------------------------------------------

Uso de **A/B testing** de mecânicas, *dashboards* de *learning
analytics* para o professor, e --- respeitada a ética --- liberação de
um **dataset aberto** para pesquisa.

## 15 Trabalhos Futuros

-   **Multiplayer colaborativo** --- turmas compartilhando uma galáxia;
    planetas que interagem (comércio, migração, diplomacia); *co-op*
    pedagógico.

-   **Realidade Virtual (WebXR/A-Frame ou Godot XR)** --- \"caminhar\"
    pelo próprio planeta e observar ecossistemas de dentro.

-   **Realidade Aumentada** --- projetar o planeta sobre a mesa da sala
    de aula.

-   **Agentes autônomos / civilizações inteligentes** --- sociedades
    movidas por LLMs (LangGraph) que desenvolvem tecnologia, cultura e
    políticas emergentes (árvores tecnológicas).

-   **Geração procedural** --- galáxias inteiras de planetas, biomas e
    criaturas geradas proceduralmente.

-   **Exploração espacial** --- viagens interplanetárias, colonização,
    *panspermia* entre mundos dos alunos.

-   **LLMs multimodais** --- o aluno desenha uma criatura ou bioma e a
    IA a interpreta e integra à simulação; interação por voz.

-   **Personalização adaptativa baseada em IA** --- trilhas de
    aprendizagem individualizadas guiadas pelo modelo de conhecimento do
    estudante (*stealth assessment* → recomendação).

-   **Implantação em borda/offline** --- pacote leve para escolas de
    baixa conectividade (SQLite + LLM local via Ollama).

-   **Ecossistema aberto de conteúdos** --- professores criam e
    compartilham \"cenários\" e desafios.

# PARTE VIII — Referências, Glossário e Apêndices


## 16 Referências, Glossário e Siglas

Referências Bibliográficas

Bibliografia consolidada (união deduplicada das referências técnicas,
pedagógicas e de game design). Formato autor-data (ABNT simplificado);
recomenda-se revisão final conforme a norma exigida pelo edital ou
veículo.

-   ABT, C. Serious Games. New York: Viking Press, 1970.

-   ANDERSON, L. W.; KRATHWOHL, D. R. A Taxonomy for Learning, Teaching,
    and Assessing. New York: Longman, 2001.

-   BERTALANFFY, L. von. General System Theory. New York: Braziller,
    1968.

-   BLACK, P.; WILIAM, D. Assessment and classroom learning. Assessment
    in Education, 1998.

-   BOGOST, I. Persuasive Games: The Expressive Power of Videogames.
    Cambridge: MIT Press, 2007.

-   BRASIL. Base Nacional Comum Curricular (BNCC). Brasília: MEC, 2018;
    Complemento de Computação, 2022.

-   BRUNER, J. The Process of Education. Cambridge: Harvard University
    Press, 1960.

-   CLARK, D. B.; TANNER-SMITH, E. E.; KILLINGSWORTH, S. S. Digital
    games, design, and learning: a systematic review and meta-analysis.
    Review of Educational Research, v. 86, n. 1, 2016.

-   CORBETT, A.; ANDERSON, J. Knowledge tracing. User Modeling and
    User-Adapted Interaction, 1995.

-   CSIKSZENTMIHALYI, M. Flow: The Psychology of Optimal Experience. New
    York: Harper & Row, 1990.

-   DARWIN, C. On the Origin of Species. London: John Murray, 1859.

-   DECI, E.; RYAN, R. Self-determination theory. Psychological Inquiry,
    2000.

-   de FREITAS, S. Are games effective learning tools? Educational
    Technology & Society, 2018.

-   DEWEY, J. Experience and Education. New York: Macmillan, 1938.

-   EPSTEIN, J. M.; AXTELL, R. Growing Artificial Societies. Cambridge:
    MIT Press/Brookings, 1996.

-   GEE, J. P. What Video Games Have to Teach Us About Learning and
    Literacy. New York: Palgrave Macmillan, 2003.

-   GOLDBERG, D. E. Genetic Algorithms in Search, Optimization, and
    Machine Learning. Addison-Wesley, 1989.

-   HAKE, R. R. Interactive-engagement versus traditional methods.
    American Journal of Physics, v. 66, n. 1, 1998.

-   HATTIE, J.; TIMPERLEY, H. The power of feedback. Review of
    Educational Research, 2007.

-   HOLLAND, J. H. Adaptation in Natural and Artificial Systems. Ann
    Arbor: Univ. Michigan Press, 1975 (MIT Press, 1992).

-   HOLLAND, J. H. Emergence: From Chaos to Order. Reading:
    Addison-Wesley, 1998.

-   HOLMES, W.; BIALIK, M.; FADEL, C. Artificial Intelligence in
    Education. CCR, 2019.

-   HUNICKE, R.; LeBLANC, M.; ZUBEK, R. MDA: A Formal Approach to Game
    Design and Game Research. AAAI Workshop, 2004.

-   KELLER, J. M. Motivational Design for Learning and Performance: The
    ARCS Model. New York: Springer, 2010.

-   KOLB, D. A. Experiential Learning: Experience as the Source of
    Learning and Development. Englewood Cliffs: Prentice Hall, 1984.

-   KOSTER, R. A Theory of Fun for Game Design. 2. ed. O\'Reilly, 2013.

-   LOVELOCK, J. Gaia: A New Look at Life on Earth. Oxford: Oxford
    University Press, 1979.

-   LUCKIN, R. et al. Intelligence Unleashed: An Argument for AI in
    Education. London: Pearson, 2016.

-   MALONE, T. W. Toward a theory of intrinsically motivating
    instruction. Cognitive Science, v. 5, n. 4, 1981.

-   MALONE, T.; LEPPER, M. Making learning fun. In: Aptitude, Learning
    and Instruction, 1987.

-   MEADOWS, D. H. Thinking in Systems: A Primer. White River Junction:
    Chelsea Green, 2008.

-   MICHAEL, D.; CHEN, S. Serious Games: Games That Educate, Train, and
    Inform. Boston: Thomson, 2006.

-   MISHRA, P.; KOEHLER, M. J. Technological Pedagogical Content
    Knowledge (TPACK). Teachers College Record, v. 108, n. 6, 2006.

-   MISLEVY, R.; STEINBERG, L.; ALMOND, R. On the structure of
    educational assessments. Measurement, 2003.

-   MITCHELL, M. Complexity: A Guided Tour. Oxford: Oxford University
    Press, 2009.

-   ODUM, E. P. Fundamentals of Ecology. Philadelphia: Saunders, 1971.

-   PAPERT, S. Mindstorms: Children, Computers, and Powerful Ideas. New
    York: Basic Books, 1980.

-   PAPERT, S.; HAREL, I. (Eds.). Constructionism. Norwood: Ablex, 1991.

-   PIAGET, J. The Psychology of Intelligence. London: Routledge, 1950.

-   PLASS, J. L.; HOMER, B. D.; KINZER, C. K. Foundations of game-based
    learning. Educational Psychologist, v. 50, n. 4, 2015.

-   PRENSKY, M. Digital Game-Based Learning. New York: McGraw-Hill,
    2001.

-   REYNOLDS, C. W. Flocks, herds and schools: a distributed behavioral
    model. SIGGRAPH Computer Graphics, v. 21, n. 4, 1987.

-   RUSSELL, S.; NORVIG, P. Artificial Intelligence: A Modern
    Approach. 4. ed. Pearson, 2020.

-   RYAN, R.; RIGBY, C.; PRZYBYLSKI, A. The motivational pull of video
    games: a self-determination theory approach. Motivation and Emotion,
    2006.

-   SALEN, K.; ZIMMERMAN, E. Rules of Play: Game Design Fundamentals.
    MIT Press, 2004.

-   SCHELL, J. The Art of Game Design: A Book of Lenses. Morgan
    Kaufmann, 2008.

-   SHUTE, V. Focus on formative feedback. Review of Educational
    Research, 2008.

-   SHUTE, V. J. Stealth assessment in computer-based games to support
    learning. In: TOBIAS, S.; FLETCHER, J. D. (Eds.). Computer Games and
    Instruction. Charlotte: IAP, 2011.

-   SHUTE, V.; VENTURA, M. Stealth Assessment: Measuring and Supporting
    Learning in Video Games. Cambridge: MIT Press, 2013.

-   SIEMENS, G.; LONG, P. Penetrating the fog: analytics in learning and
    education. EDUCAUSE Review, 2011.

-   SQUIRE, K. Video Games and Learning. New York: Teachers College
    Press, 2011.

-   SUTTON, R. S.; BARTO, A. G. Reinforcement Learning: An
    Introduction. 2. ed. Cambridge: MIT Press, 2018.

-   SWEETSER, P.; WYETH, P. GameFlow: a model for evaluating player
    enjoyment in games. ACM Computers in Entertainment, 2005.

-   SWELLER, J. Cognitive load during problem solving. Cognitive
    Science, 1988.

-   VANLEHN, K. The relative effectiveness of human tutoring,
    intelligent tutoring systems, and other tutoring systems.
    Educational Psychologist, v. 46, n. 4, 2011.

-   VYGOTSKY, L. S. Mind in Society. Cambridge: Harvard University
    Press, 1978.

-   WILENSKY, U.; RAND, W. An Introduction to Agent-Based Modeling.
    Cambridge: MIT Press, 2015.

-   WOOLF, B. P. Building Intelligent Interactive Tutors. Burlington:
    Morgan Kaufmann, 2009.

-   WOUTERS, P. et al. A meta-analysis of the cognitive and motivational
    effects of serious games. Journal of Educational Psychology, v.
    105, n. 2, 2013.

Glossário

-   Aprendizagem experiencial: modelo (Kolb) em que se aprende pelo
    ciclo experiência, observação, conceituação e experimentação --- o
    núcleo do ciclo de jogo.

-   Construcionismo: teoria (Papert) segundo a qual se aprende melhor
    construindo um artefato significativo --- aqui, o planeta.

-   Core Loop: ciclo central de jogabilidade repetido continuamente pelo
    jogador.

-   Evidence-Centered Design (ECD): arcabouço de avaliação (modelos de
    competência, evidência e tarefa) que fundamenta o stealth
    assessment.

-   Micromundo: ambiente formal, manipulável e transparente onde ideias
    abstratas se tornam objetos de pensamento.

-   Progressão por competência (mastery): avanço condicionado ao domínio
    demonstrado, não ao tempo de jogo.

-   RAG (Retrieval-Augmented Generation): técnica que ancora respostas
    de um LLM em dados recuperados (estado da simulação e currículo),
    reduzindo alucinação.

-   Retórica procedural: ideia (Bogost) de que o argumento ou ensino de
    um jogo está em suas regras, não em textos.

-   Serious Game: jogo cujo propósito primário é a aprendizagem, não o
    entretenimento.

-   Stealth Assessment: avaliação embutida e contínua que infere
    competências a partir das ações no jogo, sem interromper a
    experiência.

-   Trade-off: decisão em que todo ganho implica um custo --- núcleo do
    pensamento crítico no jogo.

-   Zona de Desenvolvimento Proximal (ZDP): faixa (Vygotsky) entre o que
    o aluno faz sozinho e com apoio; alvo do scaffolding da IA.

Lista de Siglas

  -----------------------------------------------------------------------
  **Sigla**                           **Significado**
  ----------------------------------- -----------------------------------
  ABM                                 Agent-Based Modeling (Modelagem
                                      Baseada em Agentes)

  AG                                  Algoritmo Genético ou Evolucionário

  AIED                                Artificial Intelligence in
                                      Education

  BKT                                 Bayesian Knowledge Tracing

  BNCC                                Base Nacional Comum Curricular

  CI/CD                               Continuous Integration / Continuous
                                      Delivery

  DDD                                 Domain-Driven Design

  DoR / DoD                           Definition of Ready / Definition of
                                      Done

  ECD                                 Evidence-Centered Design

  EDA                                 Event-Driven Architecture

  ERS                                 Especificação de Requisitos de
                                      Software

  GBL                                 Game-Based Learning

  IBL / PBL                           Inquiry-/Problem-Based Learning

  IRT / TRI                           Item Response Theory (Teoria de
                                      Resposta ao Item)

  LGPD                                Lei Geral de Proteção de Dados

  LLM                                 Large Language Model

  LTI                                 Learning Tools Interoperability

  MVP                                 Minimum Viable Product

  PWA                                 Progressive Web App

  RAG                                 Retrieval-Augmented Generation

  RBAC                                Role-Based Access Control

  RF / RNF / RT / RP                  Requisito Funcional / Não Funcional
                                      / Técnico / Pedagógico

  WSJF                                Weighted Shortest Job First
  -----------------------------------------------------------------------

## 17 Apêndice A --- Sugestões de Nome

**Lista (25 candidatos):** Ecosfera · Bioverso · Terraforma · Gaia ·
Gênesis · Éden · Aeon · Semente (WorldSeed) · Cosmogênese · Planeta Vivo
· EvoMundo · Biogênese · Pangeia · Orbis · Simbiose · Kósmos · Aurora ·
Demiurgo · Xenobiota · Mundo Semente · EvoGaia · Nova Terra · Panspermia
· Criador de Mundos (WorldForge) · Vivário.

**Os 5 melhores (com justificativa):**

74. **ECOSFERA** --- cientificamente preciso (*ecosphere* = a biosfera
    como sistema); captura a essência **sistêmica e interdisciplinar**;
    sonoro e memorável em pt-BR. **(Recomendado)**

75. **Bioverso** --- neologismo *bio + universo*; distintivo,
    \"brandável\", evoca vida em escala cósmica; ótimo para identidade
    visual.

76. **Terraforma** --- nomeia diretamente a **mecânica central** (moldar
    um mundo); evocativo e orientado à ação.

77. **Gaia** --- ancorado na **hipótese Gaia** (planeta como sistema
    autorregulado), casa perfeitamente com a proposta científica; curto
    e forte.

78. **Gênesis** --- metáfora universal de **criação**; imediatamente
    compreensível e memorável para estudantes.

Histórico de Atualizações (v1.0 → v2.0)

Registro das alterações desta consolidação, com a decisão que motivou
cada uma.

  -------- ----------------------------------------------- ------------------------- -------------------
  **\#**   **Alteração**                                   **Decisão motivadora**    **Seções**

  **1**    Java/Spring Boot → Node.js/NestJS na plataforma Equipe recomposta, agora  Arq §2.1, §12.1;
                                                           TypeScript-cêntrica       ERS §7.2--7.4,
                                                                                     RT-002; Plano §7

  **2**    Spring Data JPA/Hibernate → TypeORM             Adoção efetiva; baseline  Arq §2.1, §9; ERS
                                                           de 18 tabelas aplicada    §7.4

  **3**    Spring Security → Passport + guards NestJS +    Manter maturidade de      Arq §2.1
           OIDC externo                                    segurança pós-migração    

  **4**    Gradle/Maven → pnpm + Turborepo + uv            Unificação da cadeia de   Plano §7
                                                           ferramentas               

  **5**    Repositório reorganizado por unidade            Duas unidades passaram a  Plano §7
           implantável                                     compartilhar TypeScript   

  **6**    PostgreSQL separado em schemas platform e rag   Isolar migrações TypeORM  Arq §9; ERS §7.4
                                                           × Alembic sem duplicar    
                                                           servidor                  

  **7**    Barramento: Redis Streams (MVP) → NATS (Inc 7+) Resolver ambiguidade      Arq §9; ERS §7.4
                                                           Dossiê×backlog; evitar    
                                                           over-engineering          

  **8**    Bounded contexts explicitados                   Consolidação no           Arq §2.1
           (identity/education/assessment/orchestration)   scaffolding do monorepo   

  **9**    Nova seção: Estado Atual da Implementação       Distinguir o construído   §17 (nova)
                                                           do planejado              

  **10**   Registro do feedback causal por regras antes do Hipótese pedagógica       §17 (nova)
           LLM                                             testável no MVP; LLM no   
                                                           Inc 6                     

  **11**   Nova seção: Marcos do Projeto (M0--M8)          Pontos formais de decisão §18 (nova)

  **12**   Nova seção: Registro de ADRs + pendência de     Implementa recomendação   §19 (nova)
           numeração                                       do próprio dossiê         

  **13**   Superação formal da recomendação de Prisma      Divergência entre         §19; ERS §7.4
                                                           relatório de migração e   
                                                           implementação             
  -------- ----------------------------------------------- ------------------------- -------------------

Histórico de Atualizações (v2.0 → v3.0)

  --------------------------------------------------------------------------
  **#**    **Mudança**                                    **Motivação**
  -------- ---------------------------------------------- -------------------
  **1**    Adoção da Arquitetura de Engines (ADR-ARCH-    Tratar o sistema
           0001): módulos in-process, três camadas, dois  como plataforma de
           canais de comunicação                          simulação científica
                                                          composta por domínios
                                                          independentes

  **2**    Superação formal do AG de fitness global por   Fidelidade científica
           evolução emergente (RF-031)                    (evolução não
                                                          teleológica) e eventos
                                                          causais legíveis

  **3**    Nova seção 10.5: Observabilidade por Design    Plataforma educacional
           (ADR-ARCH-0002): quatro pilares, Event Store,  exige ser explicável,
           explicabilidade como schema                    auditável e depurável;
                                                          Tutor consome eventos

  **4**    Resolução da pendência de numeração de ADRs    Ambiguidade eliminada
           por escopo (ADR-ARCH- / série de serviço)      sem fusão indevida

  **5**    Correção do Sumário: hierarquia de títulos     Sumário automático
           reconstruída em estilos reais de cabeçalho     falhara na v2 por
                                                          títulos sem estilo
  -------- ---------------------------------------------- -------------------
