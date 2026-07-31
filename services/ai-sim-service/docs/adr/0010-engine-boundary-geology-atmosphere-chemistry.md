# ADR 0010 — Onde mora o carbono: a fronteira geology / atmosphere / chemistry

## Status
Aceito. Implementa o M1 (fatia vertical) da Spec do Framework, sob
**ADR-ARCH-0001** e **ADR-ARCH-0002**. Referências: Dossiê v3 §9/§10.4,
RF-013/014, RF-023.

## Contexto

O M1 pede três Engines — Geology, Atmosphere, Climate — com o acoplamento
`vulcanismo → CO₂ → forçamento → temperatura` cruzando fronteiras apenas pelo
Canal A. O plano original mantinha `chemistry` e `ocean` no adaptador legado até
o M2.

A inspeção do código mostrou que esse corte **não existia**. O CO₂ não estava
"embutido em climate/chemistry" como duas peças separáveis: era uma única
expressão misturando a física de três Engines diferentes
(`subsystems/chemistry.py:49`):

```python
d_co2 = outgassing - uptake - weathering
#       ↑geologia    ↑biota   ↑litosfera/oceano
#       (M1)         (M3)     (M2)
```

Extrair só a parte do M1 partiria a expressão no meio. E com `chemistry`
permanecendo no adaptador, o CO₂ passaria a ter **dois donos** — `LegacySlice` e
`AtmosphereSlice`. O validador de grafo do M0 não pegaria isso: ele barra dois
Engines escrevendo a mesma *fatia*, mas aqui seriam fatias diferentes com a mesma
*grandeza*. Divergência silenciosa.

Três acoplamentos estavam na mesma situação: `temperature` era escrita por
`climate` **e** por `ocean` (sequestro de calor); `ice_cover` era escrita por
`chemistry` e lida por `climate`; `solar_flux` vinha de `physics`.

## Decisão

### 1. O ciclo do carbono inteiro vai para o Atmosphere Engine

Fonte, intemperismo e absorção biótica passam a viver num só lugar. A geologia
publica apenas o **fluxo** emitido (`GeologySlice.co2_flux`); a atmosfera integra
o estoque. Um dono, uma expressão, nenhuma duplicação.

### 2. O sequestro de calor oceânico vai para o Climate Engine

`temperature` precisa de escritor único. O `ocean` legado continua dono de
salinidade e circulação; o Climate lê a circulação e aplica o fluxo de calor. A
física é a mesma — mudou a autoria.

### 3. A `LegacySlice` PERDE os campos migrados

Não basta parar de escrevê-los: `temperature`, `energy`, `co2`, `relief` e
`volcanism` saem do tipo. Assim a dupla autoria fica impossível por construção —
`apply_delta` rejeita campo inexistente, então um delta legado que tentasse mexer
em temperatura falharia no ato, em vez de divergir em silêncio.

### 4. A ciência migrada é zerada NA ORIGEM, não mascarada no fim

`reduced_params` zera os termos de carbono do `chemistry` e o `heat_uptake` do
`ocean` antes de montar o orquestrador legado. Descartar o resultado no fim do
tick não bastaria: o `life` legado roda depois do `chemistry` no mesmo
orquestrador e leria um CO₂ fantasma, já somado e ainda não descartado.

### 5. O forçamento radiativo passa a ser logarítmico

`ΔF = 5,35 · ln(C/C₀)` (Myhre et al. 1998) substitui `coeficiente × CO₂`. As
bandas de absorção do CO₂ saturam: cada duplicação acrescenta aproximadamente o
mesmo forçamento, não o dobro. O modelo linear ensinaria uma resposta climática
que a física não tem — inaceitável numa plataforma cujo produto é explicar
ciência.

### 6. A ordem do tick passa a ser geology → atmosphere → climate

Elimina a defasagem de um tick entre desgaseificação e estoque, deliberada no
núcleo antigo. O feedback passa a ser observável **dentro do mesmo tick**, que é
o que o M1 precisa demonstrar.

## Consequência que precisa ser dita com todas as letras

**Paridade determinística entre o caminho legado e a moldura deixou de existir.**
As decisões 5 e 6 mudam números por construção; exigir paridade seria exigir que
a ciência não melhorasse. Medido em 100 ticks sob a semente 2027, só a reordenação
já move a temperatura em +0,072 °C e o CO₂ em −0,46 ppm — e a troca linear→log
move muito mais em estoques altos.

O que substitui a paridade como rede de proteção:

- cada caminho é **individualmente determinístico** e reprodutível por semente;
- o novo caminho tem **sanidade científica testada** (monotonicidade, saturação,
  estoque não-negativo, conservação de carbono, planeta habitável);
- o replay bit-a-bit vale **dentro** do novo caminho (RF-023);
- os contratos HTTP permanecem intactos, verificados em teste.

## Alternativas consideradas

- **Manter o CO₂ no `chemistry` legado e a atmosfera só com o forçamento.**
  Rejeitado: o forçamento depende do estoque, então a atmosfera teria de ler CO₂
  da `LegacySlice` e o carbono continuaria sem dono claro — adiando o problema
  com uma fronteira falsa.
- **Preservar a relação linear para manter paridade.** Rejeitado: congelaria um
  erro conceitual no produto para proteger uma métrica de regressão.
- **Migrar o núcleo inteiro de uma vez (absorvendo o M2).** Rejeitado: dobraria o
  escopo do marco e tiraria da fatia vertical justamente o papel de validar a
  moldura com risco pequeno.

## Consequências

+ O carbono tem um dono só, e o tipo do world-state impede que volte a ter dois.
+ Cada seta do acoplamento cruza fronteira só pelo Canal A, verificado por teste
  de isolamento e por `import-linter`.
+ A resposta climática passa a saturar como a real satura.
− `chemistry` e `ocean` ficaram parcialmente esvaziados até o M2; quem os ler sem
  contexto pode estranhar os termos zerados. Mitigado por `reduced_params` ser
  explícito e documentado.
− A `LegacySlice` ainda existe. Ela é dívida declarada e deve encolher a cada
  marco; se parar de encolher, virou permanente.
