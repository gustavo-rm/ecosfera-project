# Decisões do frontend onde a documentação não respondia

Cada item diz o que foi decidido e por quê. Decisões de arquitetura maiores estão nos ADRs em `adr/`.

| # | Decisão | Motivo |
|---|---|---|
| D-01 | A ordem das células segue a subdivisão do icosaedro com vértices novos anexados ao fim (`cellOrder.ts`). | A Especificação não está no repositório. Esta ordem dá a propriedade de prefixo, útil para LOD. É a hipótese a confirmar com o motor. |
| D-02 | `parent` de uma célula nova é o vértice de menor índice da aresta que a criou. | O briefing só diz "índice no nível anterior". |
| D-03 | Rotas em português (`/jogo`, `/professor`, `/coordenacao`, `/responsavel`, `/lab`). | São visíveis ao usuário. Identificadores de código seguem em inglês. |
| D-04 | i18n com módulo próprio de 40 linhas, sem biblioteca. | Um idioma, sem regras de plural complexas. Trocar por uma biblioteca é mudança localizada em `src/i18n/`. |
| D-05 | Os rótulos do Apêndice A ficam em `core/state/catalogs.ts`, não nos arquivos de mensagens. | São texto normativo de domínio; não devem ser reescritos por quem traduz a interface. |
| D-06 | O estudante vê "ano N" contado do início do planeta. Velocidades: 1 mês/s, 1 ano/s, 10 anos/s e avanço até o fim da era. | "Eras e anos, nunca ticks." Estações só aparecem a 1 mês/s; acima disso a fonte entrega médias anuais para não piscar. |
| D-07 | A linha do tempo só rola pelo passado já visitado. | Evita revelar o futuro do roteiro e combina com "o que já aconteceu". |
| D-08 | "Comparar antes e depois" fixa um instante e mostra uma tabela de diferenças, com troca entre os dois instantes. | Dois canvases 3D simultâneos custariam o dobro em hardware modesto. |
| D-09 | A estrela fica fixa na cena e o eixo inclinado gira em torno dela ao longo do ano. | As estações ficam fisicamente orientadas e o lado iluminado não some da câmera inicial. |
| D-10 | Rotação do planeta em ritmo estilizado (um dia de 24 h leva 60 s) e só enquanto o tempo corre. | Com 1 tick = 1 mês não há dia real para mostrar. Está dito na legenda. |
| D-11 | Exagero de relevo padrão de cerca de 56 vezes, com controle visível. | Relevo real é invisível na escala do raio. |
| D-12 | Varredura revela uma região de 28° de raio. As quatro camadas do GDD não exigem varredura. | Progressive disclosure sem bloquear o primeiro contato. |
| D-13 | Balanceamento de custos, recargas e pontos de pesquisa é provisório. | O GDD diz que é parametrizável por trilha e nível. |
| D-14 | O nível do jogador é calculado no cliente por uma regra simples e marcado como simulado. | Em produção vem da avaliação; o estudante só o vê. |
| D-15 | Pandemia e espécie invasora existem como eventos abstratos de interface, sem efeito de doença modelado. | O motor não os cobre (§26). Ver `DIVERGENCIAS.md`. |
| D-16 | Miniaturas de planetas no painel do professor são desenhadas em canvas 2D pela mesma função de aparência, com botão "Abrir em 3D". | Vários contextos WebGL lado a lado pesam em hardware modesto. |
| D-17 | PDF gerado por um escritor mínimo próprio (texto, A4). | Evita uma dependência pesada para um relatório simples. |
| D-18 | Guarda de rota por papel é um componente local (`RoleGate`), declarado provisório na própria tela. | Não há autenticação nesta tarefa. |
| D-19 | A flag de desenvolvimento liga com `?dev=1` (fica salva) e vem ligada em `next dev`. | O console de laboratório e o seletor de papel precisam ser alcançáveis no build de produção para revisão. |
| D-20 | Fontes via pacotes `@fontsource-variable/*` (licença OFL), servidas pelo próprio app. | Nada de CDN em tempo de execução, e o build não depende de rede externa. |
| D-21 | Telemetria do Next.js desligada em `next.config.ts`. | Regra do projeto: nenhuma telemetria de terceiros. |
| D-22 | Paleta escura das séries usa cinco matizes e um cinza claro na sexta posição. | A simulação de daltonismo mostrou laranja e verde confundíveis; azul e violeta também. |
| D-23 | As regras de jogo só avançam no tempo. Ao rolar a linha do tempo para o passado, nada é reposto, nenhum aviso se repete e não é possível agir. | A revisão independente mostrou que cruzar uma fronteira de era várias vezes repunha pontos de ação. Agir no passado reescreveria a história com previsões já registradas. |
| D-24 | Um salto longo no tempo (retomada, ou link que abre um instante posterior) atualiza o estado de jogo sem recompensa de era e sem avisos acumulados. | Evita ganhos e ruído que não vieram de jogar. |
| D-25 | Um evento suprimido perde 85% da intensidade, da mortalidade e do pulso de extinção. | Antes, a supressão só mudava a imagem. Valor provisório. |
| D-26 | Linhagem introduzida e linhagem separada por barreira vivem em torno do ponto escolhido (raios de 38° e 30°). | A interface exige um alvo; o alvo precisa ter efeito. Valores provisórios. |
| D-27 | O service worker guarda só a casca, os arquivos de build com hash e as fixtures; nunca respostas de dados. | Quando houver backend, respostas autenticadas não podem ficar em aparelho compartilhado da escola. |
| D-28 | Os parâmetros de URL (`?dev=1`, `?papel=`, `?cenario=`, `?tick=`) funcionam para qualquer pessoa. | São atalhos de demonstração e de teste sem autenticação real. **Precisam sair ou ser protegidos antes de qualquer uso com alunos.** |
