# Astronomy Engine

Abre a ordem do tick. É o porte do subsystem `physics` para a moldura — não é
ciência nova, é a mesma física com dono (ADR 0013).

Existe porque a `AstronomySlice` foi criada no M0 e ficou **órfã de escritor**:
sem ela, `solar_flux` e as coordenadas orbitais não teriam Engine algum depois da
aposentadoria do adaptador, e o clima recairia numa constante de referência.
Estações e excentricidade morreriam em silêncio — daí o teste anti-regressão
`test_solar_flux_has_writer`.

## Documentação científica

### Integração orbital — por que velocity Verlet

```
x(t+dt) = x + v·dt + ½·a·dt²
v(t+dt) = v + ½·(a + a')·dt
```

Velocity Verlet é um integrador **simplético**: preserva a estrutura do espaço de
fase e, com isso, a energia orbital ao longo de milhares de passos. Euler
explícito não preserva — a órbita decairia para a estrela ou escaparia, e a
simulação deixaria de ser estável em escala de eras.

A conservação de energia é verificada em teste, não assumida.

### Irradiância incidente

```
S = L / r²
```

Lei do inverso do quadrado. É a **entrada de energia** de tudo o que vem abaixo:
o Climate a consome no balanço radiativo, o Resource a converte em energia
biologicamente útil. Por isso este Engine abre o tick.

O cálculo é 100% determinístico — **não consome o RNG**. Uma órbita é condição de
contorno externa, não resposta ao planeta.

### Excentricidade

Com `eccentricity_kick = 0` a órbita é circular e a insolação é constante: o
evento `InsolationShift` nunca dispara. Com `kick > 0` a órbita vira elipse, a
distância à estrela oscila e as estações aparecem. O parâmetro é o botão
pedagógico de "por que existem estações".

## Documentação técnica

| Item | Valor |
| --- | --- |
| `engine_id` | `astronomy` |
| escreve | `AstronomySlice` (`orbital_x`, `orbital_y`, `orbital_vx`, `orbital_vy`, `solar_flux`) |
| lê (mesmo tick) | — |
| lê (defasado) | — |
| eventos | `InsolationShift` — `ORBITAL_ECCENTRICITY` |
| parâmetros | `params.yaml` (versionado) |

**Não lê ninguém.** É o único Engine com `reads` vazio, e isso é a afirmação
física de que a órbita não responde ao planeta. Se um dia ler algo, é sinal de
que uma retroalimentação indevida entrou no modelo.

**Invariante:** energia orbital constante dentro da tolerância do integrador.

O evento compara variação **relativa**, não absoluta: a insolação de um planeta
distante é pequena em termos absolutos, e a estação dele não é menos estação por
isso. O zero de abertura não conta como travessia — é ausência de medida.
