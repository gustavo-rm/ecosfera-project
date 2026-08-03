# ADR 0020 — Instabilidade de carbono em horizonte longo (dívida HERDADA)

## Status
**Aberto. Dívida herdada, sem dono de marco.** Descoberto durante o M4, mas
**anterior a ele**. Não bloqueia desenvolvimento; **bloqueia sessões longas e
pilotos**. Referências: ADR-ARCH-0001 (fidelidade científica), ADR 0012 (ciclos
fechados), ADR 0019 §7, Walker/Hays/Kasting (1981).

## O quê

**Não existe equilíbrio de CO₂ em nenhuma versão do simulador.** O carbono
atmosférico cresce sem freio em horizonte longo, e em parte das sementes a
biosfera colapsa e não retorna.

Medições em planeta-quieto (Diretor mudo, sem eventos), 3000 ticks:

| versão / semente | bio em t=2999 | ticks sem vida (t>1000) | deriva do CO₂ na cauda |
| --- | --- | --- | --- |
| M3 semente 2027 | 0,00 | 875 | +41,8 |
| M3 semente 99 | 0,00 | 1770 | +22,8 |
| M4 (Q11) semente 2027 | 0,00 | 1536 | +53,7 |
| M4 (Q11) semente 99 | **21,84** | **0** | +16,4 |

Reconfirmação independente no fechamento do M4 (terceira medição, três sementes):

| semente | CO₂ em t=2999 | deriva da cauda (média 2500–3000 − média 2000–2500) |
| --- | --- | --- |
| 2027 | 870,4 ppm | **+53,75** |
| 99 | 792,4 ppm | **+16,39** |
| 11 | 882,8 ppm | **+35,53** |

A deriva é **positiva em toda semente medida** e ainda positiva no último
intervalo: o CO₂ passa de 870 ppm e continua subindo em t=3000. Não é uma
excursão que retorna — é rampa.

## O que NÃO é

**Não é causado pelo M4.** O M3 é igual ou pior: colapso da biosfera em duas
sementes de duas, com 875 e 1770 ticks sem vida.

**Não é causado pela Q11.** A capacidade eltoniana em todos os níveis
(ADR 0019 §6) *melhora* estritamente a semente 99 — a vida sobrevive (21,84) onde
o M3 a matou (0,00), e a deriva cai de +22,8 para +16,4. Atribuí-la à Q11 seria
factualmente errado e faria a próxima pessoa desfazer uma correção científica
correta.

## Por que ficou invisível até agora

**Nenhum teste rodava além de ~600 ticks.** A suíte é forte em correção POR TICK
— conservação de água, contabilidade de carbono sem dupla contagem, invariantes
de fatia, cadeia causal — e essas verificações passam perfeitamente enquanto o
sistema derrapa, porque cada passo está certo. O que faltava é uma classe
diferente: **teste de TRAJETÓRIA LONGA**, que pergunta para onde o sistema vai, e
não se cada passo é legal.

É a lacuna que este ADR nomeia. Um sistema pode ser correto passo a passo e não
ter atrator nenhum.

## Hipótese de causa (a investigar — NÃO neste marco)

**Falta o termostato de carbono de longo prazo.** Na Terra, o intemperismo de
silicatos fecha um laço NEGATIVO:

```
mais CO₂ → mais calor → mais intemperismo → menos CO₂
```

> Walker, J.C.G., Hays, P.B., Kasting, J.F. (1981). *A negative feedback
> mechanism for the long-term stabilization of Earth's surface temperature.*

O modelo tem intemperismo (`weathering_coeff` no Atmosphere), mas ele é
proporcional apenas ao ESTOQUE de CO₂ — não à TEMPERATURA. Sem a dependência
térmica, o laço não se fecha: o sumidouro não acelera quando o planeta esquenta,
e a desgaseificação vulcânica ganha a corrida no longo prazo.

Isto é **hipótese**, coerente com os dados e com a literatura, e **não foi
verificada**. Verificá-la e corrigi-la é um marco científico próprio.

## Consequência de produto

**O horizonte de jogo cientificamente válido hoje é de ~500 ticks.**

Medido no fechamento do M4, janela assentada (metade final), quatro sementes:

| horizonte | amplitude do CO₂ na janela | veredito |
| --- | --- | --- |
| 400 | 13–65 ppm | estável |
| **500** | **18–59 ppm** | **estável — limite adotado** |
| 600 | 38–93 ppm | **já rompe** (93,2 na semente 2027) |
| 800 | 103–192 ppm | francamente instável |

Note que 500 é MENOR que a estimativa de ~600 que circulou antes: a estimativa
vinha de uma única semente, e a medição em quatro mostra 600 rompendo. O número
adotado é o medido.

Além disso, **nenhuma garantia**: a trajetória segue determinística e replayável,
mas deixa de ser cientificamente defensável como "planeta em equilíbrio".

## Como a dívida fica visível

1. `test_baseline_planet_is_quasi_stationary` afirma quase-estacionariedade **até
   o horizonte válido**, em várias sementes — verdadeiro, e verificado.
2. `test_carbon_stable_long_horizon` é **`xfail` ANOTADO**, apontando para este
   ADR. A árvore fica verde e a dívida aparece no relatório de teste a cada
   execução, como `xfailed`. Um `skip` silencioso a apagaria; deletar o teste
   apagaria a descoberta.

Quando o termostato for implementado, o `xfail` vira `xpass` e o relatório avisa
sozinho — o teste é o marcador da dívida e o sinal da correção.
