# Relatório de desempenho

## Resumo

- **Não foi possível medir em um Chromebook real.** Todas as medidas são em Chromium headless com WebGL por software (SwiftShader), em uma máquina de 4 núcleos sem GPU. Isso é um **piso pessimista**: mede o pior caso de preenchimento de pixels na CPU. Não representa um Chromebook, que tem GPU integrada.
- Com a **qualidade automática**, em 1366×768, o planeta estabiliza em **30,9 FPS** (p95 de 50 ms por quadro). Com a CPU limitada em 4×, fica em **28,8 FPS** (p95 de 50 ms). Para isso o governador desce ao nível baixo e reduz a resolução interna para 699×393.
- Sem a queda automática, em resolução cheia, o WebGL por software fica entre 5 e 20 FPS conforme o nível e a vista.
- Latência da ação ao feedback (RNF-002): a ondulação no ponto é disparada no mesmo instante do gesto (0,5 ms) e aparece na tela em **192 ms no p95**, no mesmo ambiente.
- **Confiança:** alta de que o piso é este; baixa sobre o número em hardware real. A meta de 30 FPS em Chromebook continua **não verificada**.

## Método

- Script: `apps/web-client/scripts/perf.mjs`, contra o build de produção (`next start`).
- Página: `/lab/planeta?preset=terra`, com o tempo correndo a 1 ano por segundo.
- Medida: intervalo entre quadros (`requestAnimationFrame`) por 6 s, depois de 2,5 s de aquecimento. Limitação de CPU pelo protocolo do Chrome (`Emulation.setCPUThrottlingRate`).
- Caso automático: começa no nível médio, espera 25 s para o governador agir e então mede.
- A limitação de CPU não desacelera o rasterizador por software na mesma proporção (ele usa todos os núcleos), então o caso 4× subestima um pouco o efeito em CPU fraca.

## Medidas

A tabela completa, gerada pelo script, está em `desempenho-medidas.md`. Extrato (1366×768):

| Qualidade | CPU | Vista | Quadro médio | FPS | p95 |
|---|---|---|---|---|---|
| automática (chega a baixa, buffer 699×393) | 1× | planeta inteiro | 32,3 ms | 30,9 | 50 ms |
| automática (chega a baixa, buffer 699×393) | 4× | planeta inteiro | 34,8 ms | 28,8 | 50 ms |
| baixa, resolução cheia | 1× | planeta inteiro | 66 ms | 15 | 83 ms |
| baixa, resolução cheia | 1× | camada de temperatura | 52 ms | 19 | 83 ms |
| baixa, resolução cheia | 4× | planeta inteiro | 83 ms | 12 | 100 ms |
| média, resolução cheia | 1× | planeta inteiro | 119 ms | 8,4 | 383 ms |
| alta, resolução cheia | 1× | planeta inteiro | 148 ms | 6,8 | 667 ms |
| baixa, 683×384 | 1× | planeta inteiro | 23 ms | 44 | 33 ms |

Leitura:

1. **O custo está nos pixels.** Dividir os pixels por quatro triplica o FPS no nível baixo. Por isso o primeiro passo do governador é a resolução.
2. **Níveis médio e alto têm picos** (p95 muito acima da mediana). Eles coincidem com a chegada de um estado novo: o worker de dados e o rasterizador por software disputam os mesmos núcleos. Em GPU real o rasterizador não usa a CPU; a expectativa é que os picos caiam, mas isso não foi medido.
3. **Zoom com organismos** custa mais (mais ruído por pixel e instâncias). O nível baixo tem um orçamento pequeno de organismos (160).
4. As demais linhas da tabela são da medição anterior à inclusão de organismos no nível baixo; a tabela gerada em `desempenho-medidas.md` é a mais recente.

## O que foi feito para o orçamento

- Aparência calculada só quando o estado muda; fusão entre estados feita na GPU; nenhum trabalho por quadro na CPU além de uniformes.
- O laço por quadro do planeta (`PlanetBody`) não aloca: usa valores pré-alocados e funções de módulo. A distribuição de organismos aloca estruturas pequenas, mas roda no máximo a cada 350 ms e só em zoom. Geometrias de organismos, efeitos e céu não são liberadas ao desmontar (pendência menor).
- Geração de dados em Web Worker.
- Atributos reenviados só quando o canal mudou.
- Shaders pulam por ramificação lava, ondas, rachaduras e filetes de erosão onde não se aplicam; a casca da atmosfera tem só o tamanho que o brilho precisa.
- Três níveis de qualidade e resolução dinâmica (ADR FE-0003).
- Durante a medição apareceu e foi corrigido um defeito: a resolução dinâmica era desfeita a cada atualização do planeta.

## Uso de memória e chamadas de desenho

Vista do planeta inteiro, nível médio: 6 a 9 chamadas de desenho (superfície, nuvens, atmosfera, 2 auroras, estrelas, estrela, luas), cerca de 20 mil triângulos na superfície, 1,5 MiB de atributos, 2 texturas de 256×1. O painel de desempenho do console de laboratório mostra esses números ao vivo.

## Tamanho do pacote

Medido por `scripts/size.mjs` (bytes comprimidos transferidos na primeira carga, build de produção). Limites definidos nesta entrega:

| Rota | JS + CSS medido | Limite |
|---|---|---|
| `/jogo` | 469 KiB | 520 KiB |
| `/jogo/dados` | 577 KiB | 620 KiB |
| `/professor` | 219 KiB | 330 KiB |
| `/` (inclui a pré-carga do jogo) | 499 KiB | 640 KiB |

Fontes: 69 a 109 KiB conforme os pesos usados. O limite do jogo é dominado por Three.js, React e Next.js. A biblioteca de gráficos é carregada sob demanda no jogo.

## O que falta

1. Medir em Chromebook real (ARM e Intel de entrada), com a escola ligada à rede típica.
2. Calibrar os limiares do governador com esses dados.
3. Medir memória em sessão longa (1 h) e o consumo de bateria.
4. Testar Firefox e Safari (RNF-023): só o Chromium foi exercitado.
