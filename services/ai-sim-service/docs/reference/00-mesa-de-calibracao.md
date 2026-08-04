# Mesa de Calibração Científica — `ai-sim-service`

> **Proveniência.** Espinha factual EXTRAÍDA do commit `7d80534` por
> `scripts/generate_reference.py` (módulo `ast` + `yaml`, sem execução do código auditado).
> Nomes de chave e **valores atuais** desta página vêm da extração, não de memória.
> A prosa das colunas *o que controla*, *efeito de aumentar/diminuir* e *invariante/risco*
> é **curada** a partir do código e dos ADRs; onde o código não sustenta uma afirmação,
> está escrito **"a confirmar"** em vez de estimativa.
>
> Re-gerar a espinha factual:
> ```bash
> cd services/ai-sim-service
> uv run python scripts/generate_reference.py -o reference.json
> ```
>
> Índice do guia: [`README.md`](README.md)

Esta é a página de trabalho de quem calibra. Ela reúne **todo parâmetro que altera o
comportamento científico do sistema** — os `params.yaml` de cada Engine, o catálogo de
eventos, as condições iniciais e as constantes de módulo que funcionam como botão.

Três leituras rápidas antes de mexer em qualquer coisa:

1. **Limiar de evento ≠ parâmetro de física.** Metade das linhas abaixo controla o que é
   NARRADO (Canal B), não o que ACONTECE (Canal A). Mexer num limiar de evento não muda a
   trajetória do planeta — muda o que o Tutor consegue explicar.
2. **Alguns parâmetros estão acoplados por igualdade, não por fórmula.** `reference_co2`
   aparece em dois Engines e na condição inicial; `reference_ocean_carbon` precisa casar com
   `initial_state.ocean_carbon`. Mover um só dos lados põe o planeta a nascer fora de
   equilíbrio — o defeito medido no ADR 0012 §7.
3. **Há dívidas já mapeadas.** Não calibre contra elas: veja
   [Dívidas conhecidas](#dívidas-conhecidas-não-calibre-contra-elas) antes.

---

## Sumário desta página

- [Astronomia — entrada de energia](#astronomia--entrada-de-energia)
- [Geologia — fonte de carbono e relevo](#geologia--fonte-de-carbono-e-relevo)
- [Química — carbono não-atmosférico, N/P/S e pH](#química--carbono-não-atmosférico-nps-e-ph)
- [Atmosfera — estoque de carbono e forçamento](#atmosfera--estoque-de-carbono-e-forçamento)
- [Clima — balanço de energia](#clima--balanço-de-energia)
- [Hidrologia — ciclo da água e circulação](#hidrologia--ciclo-da-água-e-circulação)
- [Recurso — orçamento biológico](#recurso--orçamento-biológico)
- [Evolução — seleção emergente](#evolução--seleção-emergente)
- [Ecologia — dinâmica trófica](#ecologia--dinâmica-trófica)
- [Eventos — o Diretor e o catálogo](#eventos--o-diretor-e-o-catálogo)
- [Núcleo — condições iniciais, eras e orçamento](#núcleo--condições-iniciais-eras-e-orçamento)
- [Constantes de módulo que funcionam como botão](#constantes-de-módulo-que-funcionam-como-botão)
- [Invariantes que a calibração NÃO pode violar](#invariantes-que-a-calibração-não-pode-violar)
- [Índice reverso — quero calibrar X, vá para](#índice-reverso--quero-calibrar-x-vá-para)
- [Dívidas conhecidas — não calibre contra elas](#dívidas-conhecidas-não-calibre-contra-elas)

---

## Astronomia — entrada de energia

Abre o tick e não lê ninguém: a órbita é condição de contorno externa. É a alavanca mais
global do sistema — tudo abaixo consome a irradiância que ela publica.

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `gravitational_parameter` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`gravitational_parameter` | GM da estrela no integrador de Verlet; junto com `orbital_radius` fixa o período orbital. | `1.0` | adimensional (UA³/tick²); >0 | Órbita mais rápida e mais apertada; o período cai e as estações se comprimem. | Órbita mais lenta; no limite a velocidade circular inicial não fecha a órbita. | A velocidade circular inicial é derivada daqui em `simulation_engine/params.initial_state`; mudar só um dos dois cria condição inicial incoerente com a gravidade. Conservação de energia orbital é testada. |
| `timestep` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`timestep` | dt de integração por tick. Com GM=1 e raio=1, o período é 2π, logo ~126 ticks por volta. | `0.05` | tick⁻¹; >0 | Menos ticks por volta (estação mais curta) e maior erro de integração. | Órbita mais suave e mais cara em ticks por volta. | Velocity Verlet é simplético mas não incondicionalmente estável: dt grande demais degrada a conservação de energia orbital, que é invariante testada. |
| `luminosity` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`luminosity` | Irradiância a 1 UA. Entra em `solar_flux = L/r²`, a entrada de energia de todo o resto. | `1.0` | normalizada; ≥0 | Planeta mais quente por toda a cadeia (clima, evaporação, energia biológica). | Planeta mais frio; abaixo de certo ponto a habitabilidade zera e não há abiogênese. | Alavanca mais global do sistema: toca clima, hidrologia, recurso e evolução ao mesmo tempo. Calibrar isto invalida a comparação com corridas anteriores. |
| `orbital_radius` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`orbital_radius` | Raio da órbita circular inicial; define a irradiância de partida. | `1.0` | UA; >0 | Menos irradiância (lei do inverso do quadrado) — planeta mais frio. | Mais irradiância — planeta mais quente. | Mesma advertência de `luminosity`; os dois são redundantes em efeito e mexer nos dois ao mesmo tempo confunde a atribuição. |
| `eccentricity_kick` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`eccentricity_kick` | Perturbação da velocidade inicial: 0 = órbita circular, >0 = elipse (estações marcadas). | `0.0` | fração da velocidade circular; ≥0 | Estações mais fortes; a variação de insolação passa a cruzar o limiar de evento com frequência. | Órbita circular: a insolação vira praticamente constante e `InsolationShift` nunca é emitido. | Só é lido na CONSTRUÇÃO do estado inicial (`simulation_engine/params.initial_state`); mudá-lo não afeta planetas já criados. |
| `insolation_shift_threshold` | `src/ecosfera_ai/engines/astronomy/params.yaml`<br>`insolation_shift_threshold` | Variação RELATIVA de insolação que caracteriza uma estação notável (Canal B). | `0.02` | fração; ≥0 | Menos eventos `InsolationShift` — só as estações mais marcadas viram trilha. | Mais eventos; abaixo do ruído numérico o Canal B vira log de debug. | É limiar de OBSERVABILIDADE, não de física: não altera a trajetória, só a trilha. `_EPS` protege a divisão quando `solar_flux` é zero. |

---

## Geologia — fonte de carbono e relevo

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `tectonic_activity` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`tectonic_activity` | Desvio-padrão do pulso tectônico gaussiano por tick (RNG semeado). | `0.05` | mesma unidade de `volcanism`; ≥0 | Vulcanismo mais errático, mais erupções e mais desgaseificação média (o pulso entra em módulo). | Vulcanismo quase determinístico, relaxando à linha de base. | O pulso entra em `abs()`: aumentar a variância aumenta a MÉDIA do vulcanismo, não só a dispersão. É uma das entradas da dívida de carbono (ADR 0020). |
| `volcanism_baseline` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`volcanism_baseline` | Nível de repouso para o qual o vulcanismo relaxa. | `1.0` | adimensional; ≥0 | Mais desgaseificação basal — CO₂ e temperatura sobem em regime. | Menos carbono entrando; no limite o intemperismo esvazia a atmosfera. | Junto com `tectonic_activity` fixa o vulcanismo de equilíbrio (~1,4), que é o que dá sentido a `eruption_threshold`. |
| `volcanism_decay` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`volcanism_decay` | Taxa de relaxação do vulcanismo para a linha de base. | `0.1` | fração por tick; (0,1] | Pulsos morrem rápido: erupções viram picos isolados. | Pulsos persistem e se acumulam; o vulcanismo médio sobe acima da base. | Amortecimento; valores muito baixos deixam o vulcanismo derivar sem retorno. |
| `uplift_coeff` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`uplift_coeff` | Soerguimento do relevo por unidade de vulcanismo. | `0.004` | relevo·vulcanismo⁻¹·tick⁻¹; ≥0 | Relevo maior → mais intemperismo → mais nutriente e mais remoção de carbono. | Relevo se aplaina; o intemperismo (fonte de N/P/S) seca. | `relief` é recortado a [0,1] por `BoundedFraction`: um coeficiente alto satura no teto e o excedente vira violação de invariante registrada. |
| `erosion_coeff` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`erosion_coeff` | Desgaste do relevo por unidade de água líquida × relevo. | `0.01` | tick⁻¹; ≥0 | Relevo cai mais rápido; menos intemperismo, menos nutriente. | Relevo persiste alto e o intemperismo domina. | Acoplado à hidrologia por leitura DEFASADA (a Hydrology roda depois da Geology). |
| `outgassing_base` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`outgassing_base` | Fluxo de CO₂ desgaseificado por tick na ausência de vulcanismo. | `1.5` | ppm/tick; ≥0 | Rampa de CO₂ mais íngreme — agrava a dívida de longo prazo do ADR 0020. | Menos carbono no sistema; no limite o planeta congela por perda de estufa. | **Fonte única do carbono vulcânico do mundo.** O supervulcanismo multiplica ESTE termo — não existe um segundo caminho (ADR 0018). |
| `volcanism_sensitivity` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`volcanism_sensitivity` | Quanto o vulcanismo amplifica a desgaseificação sobre a base. | `0.5` | adimensional; ≥0 | Erupções passam a mover o CO₂ visivelmente. | Desgaseificação vira quase constante, desacoplada da geologia. | É a seta vulcanismo→CO₂ que a regra causal `R-VOLC-CO2` narra ao aluno; zerá-la torna a explicação falsa. |
| `eruption_threshold` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`eruption_threshold` | Vulcanismo acima do qual o tick conta como erupção notável (Canal B). | `1.5` | mesma unidade de `volcanism` | Erupções raras — a trilha fica limpa mas pode perder a causa de um pico de CO₂. | Quase todo tick vira erupção: o Event Store deixa de ser trilha e vira log. | Limiar de observabilidade, não de física. Calibrado acima do vulcanismo de equilíbrio (~1,4) de propósito. |
| `supervolcanic_multiplier` | `src/ecosfera_ai/engines/geology/params.yaml`<br>`supervolcanic_multiplier` | Quanto o supervulcanismo multiplica a desgaseificação basal no pico do evento. | `9.0` | adimensional; ≥0 | Supererupção domina o ciclo do carbono por dezenas de ticks. | Supervulcão vira um tick ruim em vez de um evento de escala geológica. | É o único ponto onde a `EventSlice` toca o carbono. Somar um pulso de CO₂ direto na atmosfera criaria dupla contagem (ADR 0018). |

---

## Química — carbono não-atmosférico, N/P/S e pH

Dona do carbono OCEÂNICO e do sedimento; o carbono atmosférico é da Atmosphere (ADR 0010).

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `solubility` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`solubility` | Coeficiente de Henry linearizado: velocidade da troca ar↔oceano. | `0.02` | fração por tick; ≥0 | Oceano tampona o CO₂ mais rápido; excursões atmosféricas ficam curtas. | Oceano vira espectador; o CO₂ atmosférico oscila mais. | O MESMO número é somado ao oceano e subtraído da atmosfera. Recalibrar aqui sem revisar `test_carbon_is_not_double_counted` arrisca a contabilidade do ADR 0012. |
| `reference_co2` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`reference_co2` | pCO₂ de referência para a pressão parcial oceânica. | `280.0` | ppm; >0 | O gradiente de Henry passa a ver o oceano como mais sub-saturado. | Inverte o sentido do fluxo mais cedo. | **Precisa continuar igual** ao `reference_co2` da Atmosphere e ao `initial_state.co2`: é isso que faz o planeta partir com gradiente zero e forçamento zero. |
| `ocean_carbon_capacity` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`ocean_carbon_capacity` | Capacidade do reservatório oceânico; satura a absorção. | `3000.0` | ppm-equivalente; >0 | Oceano absorve por muito mais tempo antes de saturar. | Satura cedo e devolve carbono à atmosfera — acelera a rampa do ADR 0020. | Sem saturação o oceano seria sumidouro infinito e o CO₂ atmosférico desapareceria. |
| `burial_coeff` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`burial_coeff` | Sequestro de carbono oceânico para o sedimento — a ÚNICA saída do sistema acoplado. | `0.0008` | fração por tick; ≥0 | Sumidouro permanente maior: é o candidato mais direto a termostato de longo prazo (P-02). | Carbono se acumula no par ar+oceano sem escapatória. | O soterrado vai para `soil_carbon`, não some — é o que torna o balanço de carbono verificável. |
| `weathering_nutrient_yield` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`weathering_nutrient_yield` | Nutriente liberado por unidade de relevo × vulcanismo. | `0.02` | nutriente·tick⁻¹; ≥0 | Mais nutriente → maior capacidade de suporte → abiogênese mais cedo. | Nutriente vira limitante e a habitabilidade despenca. | Entra na lei do mínimo do Resource junto de N/P/S; o mais escasso é que governa. |
| `nutrient_recycling` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`nutrient_recycling` | Dreno proporcional do estoque de nutrientes. | `0.01` | fração por tick; ≥0 | Estoque de nutriente estabiliza mais baixo. | Nutriente acumula sem limite. | Junto com o yield fixa o nutriente de equilíbrio: `yield·relevo·vulcanismo / recycling`. |
| `nitrogen_yield` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`nitrogen_yield` | Liberação de N pelo intemperismo. | `0.01` | N·tick⁻¹; ≥0 | N deixa de ser limitante. | N vira o elemento de Liebig e trava a capacidade. | Comparar sempre com `nitrogen_demand` do Resource: o que importa é a RAZÃO estoque/demanda. |
| `phosphorus_yield` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`phosphorus_yield` | Liberação de P pelo intemperismo. | `0.004` | P·tick⁻¹; ≥0 | P deixa de ser limitante. | P vira o limitante — o caso típico e cientificamente desejável (razão de Redfield). | É o limitante que a lei do mínimo deve ENSINAR; zerá-lo como limitante apaga a lição. |
| `sulfur_yield` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`sulfur_yield` | Liberação de S pelo intemperismo. | `0.006` | S·tick⁻¹; ≥0 | S deixa de ser limitante. | S vira o limitante. | Idem: comparar com `sulfur_demand`. |
| `element_burial` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`element_burial` | Soterramento de N/P/S (dreno comum aos três). | `0.005` | fração por tick; ≥0 | Todos os elementos estabilizam mais baixo — capacidade menor. | Elementos acumulam; a lei do mínimo deixa de morder. | Um dreno só para os três: mexer aqui muda o limitante de todos ao mesmo tempo. |
| `reference_ph` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`reference_ph` | pH oceânico na concentração de referência. | `8.2` | unidade de pH | Todo o eixo de pH sobe (oceano mais básico). | Todo o eixo desce. | Deslocamento rígido: mexer aqui exige revisar `acidification_threshold` junto. |
| `ph_sensitivity` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`ph_sensitivity` | Queda de pH por década de carbono dissolvido (relação log₁₀). | `0.9` | pH/década; ≥0 | Acidificação mais dramática por unidade de carbono. | pH quase insensível ao carbono — a acidificação deixa de ser narrável. | É a ciência de Sabine et al. (2004); alterá-la muda o que o Tutor pode afirmar. |
| `reference_ocean_carbon` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`reference_ocean_carbon` | Carbono oceânico cuja pressão parcial iguala `reference_co2`. | `300.0` | ppm-equivalente; >0 | O oceano parte como sumidouro (sub-saturado) em vez de tampão. | O oceano parte devolvendo carbono. | **Precisa casar com `initial_state.ocean_carbon`** (`configs/simulation_params.yaml`), senão o planeta nasce fora do equilíbrio de Henry — o defeito medido no ADR 0012 §7. |
| `acidification_threshold` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`acidification_threshold` | pH cuja travessia para baixo emite `OceanAcidification`. | `7.9` | unidade de pH | Evento dispara mais cedo. | Evento pode nunca disparar. | Travessia (antes ≥ limiar > depois), não estado — por isso o zero de abertura não conta. |
| `nutrient_depletion_threshold` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`nutrient_depletion_threshold` | Estoque de nutriente cuja travessia para baixo emite `NutrientDepletion`. | `0.15` | mesma unidade de `nutrients` | Evento dispara mais cedo. | Evento silencia. | Também é travessia; testar o valor corrente emitiria o evento em todo tick de todo planeta. |
| `carbon_tolerance` | `src/ecosfera_ai/engines/chemistry/params.yaml`<br>`carbon_tolerance` | Tolerância declarada da conservação de carbono (Spec §3). | `1e-09` | ppm; ≥0 | Deriva de carbono deixa de ser reportada. | Ruído de ponto flutuante vira `DiagnosticEvent`. | **Carregado mas não consumido por nenhuma invariante** — ver *Achados* nº 5. A conservação de carbono é verificada em teste de integração, não por invariante de fatia. |

---

## Atmosfera — estoque de carbono e forçamento

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `reference_co2` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`reference_co2` | C₀ do forçamento de Myhre: na referência o forçamento é ZERO por definição. | `280.0` | ppm; >0 | O mesmo CO₂ passa a produzir forçamento NEGATIVO — planeta esfria. | O mesmo CO₂ produz forçamento positivo — planeta aquece. | Mexer aqui desloca todo o equilíbrio climático e exige recalibrar `equilibrium_offset` do Climate na mesma operação. |
| `weathering_coeff` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`weathering_coeff` | Remoção de CO₂ por intemperismo, proporcional ao próprio estoque. | `0.002` | fração por tick; ≥0 | Termostato carbonato-silicato mais forte: é o botão mais direto contra a rampa do ADR 0020. | Carbono se acumula sem freio. | É o único sumidouro atmosférico que existe sem biomassa. Aumentar demais leva o planeta a um CO₂ de equilíbrio abaixo da referência (esfriamento). |
| `carbon_uptake_coeff` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`carbon_uptake_coeff` | Absorção biótica de CO₂, proporcional à biomassa. | `0.02` | ppm por unidade de biomassa por tick; ≥0 | A vida passa a governar o clima: mais biomassa, menos CO₂, retroalimentação forte. | Biosfera deixa de influenciar o carbono — o acoplamento vida→planeta some. | É a única seta vida→física do modelo. Zerá-la desfaz a lição de que a vida muda o planeta. |
| `forcing_coefficient` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`forcing_coefficient` | α em `ΔF = α·ln(C/C₀)` (Myhre et al. 1998). | `5.35` | W/m²; >0 | Cada duplicação de CO₂ vale mais W/m² — sensibilidade climática efetiva sobe. | Efeito estufa vira desprezível. | É ciência publicada (5,35 W/m²). Alterá-la é declarar outra física; a forma LOGARÍTMICA é o ponto (ADR 0010), não o valor. |
| `base_pressure` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`base_pressure` | Pressão atmosférica de base. | `1.0` | normalizada; ≥0 | Pressão publicada sobe uniformemente. | Pressão cai. | `pressure` é publicada e não é lida por nenhum Engine — é diagnóstico. |
| `co2_to_pressure` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`co2_to_pressure` | Contribuição parcial do CO₂ na pressão. | `0.0002` | pressão/ppm; ≥0 | Pressão passa a acompanhar o CO₂ visivelmente. | Pressão vira constante. | Idem: sem consumidor a jusante. |
| `forcing_bands` | `src/ecosfera_ai/engines/atmosphere/params.yaml`<br>`forcing_bands` | Patamares de forçamento cuja TRAVESSIA emite `GreenhouseForcingChanged`. | `[0.5, 1.85, 3.7, 5.55, 7.4]` | W/m²; crescente | Faixas mais largas/altas: menos eventos, trilha mais limpa. | Faixas estreitas: o Canal B vira ruído contínuo. | 3,7 W/m² ≈ uma duplicação de CO₂. A faixa ANTERIOR é derivada do ESTOQUE, não do forçamento gravado — robustez exigida pela borda HTTP (ADR 0011). |

---

## Clima — balanço de energia

O clima **não calcula efeito estufa**: o forçamento chega pronto da Atmosphere pelo Canal A.

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `insolation` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`insolation` | Insolação de RECUO, usada só quando `solar_flux ≤ 0`. | `1.0` | normalizada; ≥0 | Sem efeito em produção (o Astronomy sempre publica flux > 0). | Idem. | Existe para exercitar o Climate isolado em teste de unidade. Em produção é código morto benigno — ver *Achados* nº 8. |
| `base_albedo` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`base_albedo` | Refletividade planetária sem gelo. | `0.3` | fração; [0,1] | Planeta reflete mais e esfria. | Planeta absorve mais e aquece. | Com `energy_to_temp = 30`, 0,01 de albedo vale ~0,3 °C de equilíbrio. É um botão sensível. |
| `ice_albedo_coeff` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`ice_albedo_coeff` | Ganho de albedo por fração de gelo — a retroalimentação positiva clássica. | `0.4` | adimensional; ≥0 | Retroalimentação gelo-albedo mais forte: aproxima o planeta da bola de neve irreversível. | O gelo deixa de realimentar o clima e a lição de feedback positivo some. | Lê `hydrology.ice_fraction` DEFASADO. Valores altos podem produzir biestabilidade (bola de neve) — desejável cientificamente, brutal pedagogicamente. |
| `energy_to_temp` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`energy_to_temp` | Conversão de energia absorvida em °C de equilíbrio. | `30.0` | °C por unidade de energia; >0 | Planeta muito mais quente e muito mais sensível à insolação/albedo. | Clima insensível à energia; o forçamento passa a dominar sozinho. | É o ganho principal do balanço de energia. Mexer aqui exige recalibrar `equilibrium_offset` para preservar o equilíbrio de ~17,6 °C. |
| `climate_sensitivity` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`climate_sensitivity` | λ: °C de equilíbrio por W/m² de forçamento. | `0.8` | °C/(W/m²); >0 | Mais °C por duplicação de CO₂ (0,8 ≈ 3 °C, faixa central do IPCC AR6). | O CO₂ deixa de mover a temperatura de forma perceptível. | **Botão nº 1 da sensibilidade climática.** Alterá-lo muda a lição central da plataforma; documente a nova faixa IPCC equivalente. |
| `equilibrium_offset` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`equilibrium_offset` | Deslocamento de base da temperatura de equilíbrio. | `-2.2` | °C | Planeta mais quente em toda a trajetória. | Planeta mais frio. | Absorve os +2,8 °C que o termo linear de estufa dava na referência (ADR 0010). Já existe uma lacuna conhecida de ~3,6 °C entre `initial_state.temperature` (14,0) e o equilíbrio (~17,6), pinada em `KNOWN_EQUILIBRIUM_GAP_C`. |
| `thermal_inertia` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`thermal_inertia` | Fração do desvio ao equilíbrio corrigida por tick. | `0.25` | fração; (0,1] | Planeta persegue o equilíbrio rápido: transientes curtos, eventos com efeito abrupto. | Planeta lento: uma era glacial mal move a temperatura dentro da duração dela. | Acima de 1 o sistema oscila/diverge. É a constante de tempo que decide se os eventos do M4 são visíveis. |
| `weather_variability` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`weather_variability` | Desvio-padrão do ruído meteorológico por tick (RNG semeado). | `0.05` | °C; ≥0 | Mais ruído: `TemperatureShift` dispara por acaso e a trilha perde sinal. | Trajetória lisa, sem tempo — só clima. | Semeado, portanto replayável. Interage com `shift_threshold`: ruído acima do limiar produz eventos sem causa científica. |
| `ocean_heat_uptake` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`ocean_heat_uptake` | Sequestro de calor pela circulação termohalina (retroalimentação negativa). | `0.02` | fração por tick; ≥0 | Oceano amortece mais: aquecimento e resfriamento ficam lentos. | Superfície responde sem amortecimento. | Multiplica `ocean_circulation`, que a Hydrology publica — o acoplamento cruza a fronteira só pelo Canal A. |
| `ocean_reference_temperature` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`ocean_reference_temperature` | Temperatura para a qual o oceano puxa a superfície. | `14.0` | °C | Oceano passa a AQUECER o planeta frio em vez de resfriá-lo. | Oceano resfria mais. | É o ponto fixo do termo oceânico; alterá-lo desloca o equilíbrio do planeta junto. |
| `temperature_bands` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`temperature_bands` | Patamares climáticos cuja travessia emite `ClimateThresholdCrossed`. | `[0.0, 10.0, 20.0, 30.0]` | °C; crescente | Menos eventos narrativos de patamar. | Mais eventos; risco de ruído. | É a leitura que o aluno recebe como 'o planeta mudou de regime'. Observabilidade, não física. |
| `shift_threshold` | `src/ecosfera_ai/engines/climate/params.yaml`<br>`shift_threshold` | Variação de temperatura em UM tick que emite `TemperatureShift`. | `0.15` | °C; ≥0 | Só transientes fortes viram evento. | O ruído meteorológico passa a gerar eventos. | Mantenha acima de ~2σ de `weather_variability`, senão o Canal B narra acaso como fenômeno. |

---

## Hidrologia — ciclo da água e circulação

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `evaporation_coeff` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`evaporation_coeff` | Evaporação por °C acima da referência, proporcional ao oceano (Clausius–Clapeyron linearizada). | `0.004` | tick⁻¹·°C⁻¹; ≥0 | Ciclo da água mais rápido: mais vapor, mais chuva, mais água doce. | Ciclo quase parado; a criosfera domina a distribuição. | O fluxo é limitado pelo reservatório de origem (`min(ocean, …)`), o que garante não-negatividade ANTES da invariante. A soma dos quatro reservatórios é CONSERVADA — nenhum coeficiente pode criar água. |
| `evaporation_reference_temperature` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`evaporation_reference_temperature` | Temperatura abaixo da qual não há evaporação líquida. | `10.0` | °C | Planeta precisa estar mais quente para o ciclo da água ligar. | Ciclo liga mais cedo. | Abaixo dela o termo fica negativo e é recortado a 0 — não há 'evaporação reversa'. |
| `precipitation_coeff` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`precipitation_coeff` | Fração do vapor que condensa por tick. | `0.35` | fração por tick; [0,1] | Vapor curto, água doce abundante. | Vapor acumula na atmosfera. | É o termo que a SECA suprime (`drought_intensity`); a água suprimida permanece como vapor — por isso a conservação continua valendo com seca ativa. |
| `melt_coeff` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`melt_coeff` | Degelo por °C acima do limiar, proporcional ao gelo. | `0.01` | tick⁻¹·°C⁻¹; ≥0 | Criosfera derrete rápido: albedo cai e o planeta aquece (feedback). | Gelo persiste mesmo em planeta quente. | Acoplado ao Climate pelo albedo com defasagem de um tick. |
| `freeze_coeff` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`freeze_coeff` | Congelamento por °C abaixo do limiar, proporcional ao oceano. | `0.008` | tick⁻¹·°C⁻¹; ≥0 | Planeta frio congela depressa: risco de bola de neve. | Gelo mal se forma. | O congelamento é limitado a `ocean − evaporação` do mesmo tick para não retirar água que já saiu. |
| `melt_threshold` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`melt_threshold` | Temperatura acima da qual há degelo. | `0.0` | °C | Degelo só em planeta mais quente. | Degelo permanente. | Junto com `freeze_threshold` define a banda de coexistência gelo/água. |
| `freeze_threshold` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`freeze_threshold` | Temperatura abaixo da qual há congelamento. | `0.0` | °C | Congelamento em climas mais amenos. | Congelamento raro. | Idem. |
| `runoff_coeff` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`runoff_coeff` | Retorno da água doce ao oceano. | `0.25` | fração por tick; [0,1] | Água doce curta; oceano recompõe rápido. | Água doce acumula nos continentes. | A água doce é o termo que mais pesa em `water_available` do Resource (a oceânica entra só a 10%). |
| `salt_content` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`salt_content` | Massa de sal CONSERVADA, diluída na água líquida. | `0.35` | adimensional; ≥0 | Oceano mais salgado → circulação mais forte. | Oceano doce → circulação enfraquece. | É o numerador de `target_salinity = salt/oceano`; o sal não é criado nem destruído pelo modelo. |
| `salinity_relaxation` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`salinity_relaxation` | Velocidade com que a salinidade persegue o alvo. | `0.2` | fração por tick; (0,1] | Salinidade acompanha o oceano quase instantaneamente. | Salinidade fica defasada por dezenas de ticks. | Constante de tempo; >1 oscila. |
| `reference_salinity` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`reference_salinity` | Salinidade neutra para a circulação. | `0.35` | adimensional | Água atual passa a parecer 'doce' e a circulação enfraquece. | Circulação fortalece. | Deve casar com `initial_state.salinity` para o planeta nascer em equilíbrio. |
| `reference_temperature` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`reference_temperature` | Temperatura neutra para a circulação. | `14.0` | °C | O mesmo planeta passa a ser lido como frio e a circulação fortalece. | Circulação enfraquece. | Não confundir com `ocean_reference_temperature` do Climate: são termos de Engines diferentes com nomes parecidos. |
| `salinity_sensitivity` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`salinity_sensitivity` | Peso do contraste salino na circulação. | `0.5` | adimensional; ≥0 | Circulação vira função do sal. | Circulação insensível à salinidade. | `ocean_circulation` é recortada a [0,1] por `BoundedFraction`; pesos altos saturam no teto. |
| `temperature_sensitivity` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`temperature_sensitivity` | Peso do aquecimento no enfraquecimento da circulação. | `0.02` | 1/°C; ≥0 | Aquecimento desliga a circulação — desligamento termohalino torna-se alcançável. | Circulação indiferente ao calor. | Realimenta o Climate via `ocean_heat_uptake`: os dois formam um laço amortecedor. |
| `tidal_forcing` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`tidal_forcing` | Mistura mecânica constante das marés. | `0.05` | adimensional; ≥0 | Piso de circulação mais alto. | Circulação pode ir a zero. | É o termo que impede o desligamento total por construção. |
| `circulation_baseline` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`circulation_baseline` | Circulação de repouso. | `0.5` | fração; [0,1] | Oceano circula mais em regime. | Oceano estagnado. | Deve casar com `initial_state.ocean_circulation`. |
| `circulation_relaxation` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`circulation_relaxation` | Velocidade de retorno da circulação ao alvo. | `0.15` | fração por tick; (0,1] | Resposta rápida a mudanças de sal/calor. | Resposta lenta, memória longa. | Constante de tempo. |
| `circulation_variability` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`circulation_variability` | Ruído de mistura por tick (RNG semeado). | `0.005` | adimensional; ≥0 | Circulação errática. | Circulação determinística. | Semeado, portanto replayável. |
| `ice_event_threshold` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`ice_event_threshold` | Variação da fração de gelo que emite `IceSheetChanged` + `WaterBalanceShift`. | `0.02` | fração; ≥0 | Menos eventos criosféricos. | Trilha inundada por variações de rotina. | Emite DOIS eventos encadeados por vez — o segundo herda `causation_id` do primeiro. |
| `conservation_tolerance` | `src/ecosfera_ai/engines/hydrology/params.yaml`<br>`conservation_tolerance` | Tolerância da invariante `water_conservation` (Spec §3). | `1e-09` | unidade de água; ≥0 | Vazamento real de água passa despercebido. | Ruído de ponto flutuante vira `DiagnosticEvent` a cada tick. | **É lida de fato**: `build_planet_engine` a injeta em `ConservedTotal`. A invariante NÃO repara — só registra, para que o número errado fique à vista. |

---

## Recurso — orçamento biológico

Último elo determinístico: converte o ambiente resolvido em `carrying_capacity`, o **único**
acoplamento física→biologia (ADR 0006).

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `ocean_accessibility` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`ocean_accessibility` | Fração da água oceânica que conta como biologicamente utilizável. | `0.1` | fração; [0,1] | Planeta oceânico vira habitável mesmo sem água doce. | A vida passa a depender só da água doce (chuva). | É o que faz o ciclo da água importar para a biologia; em 1,0 a hidrologia deixa de ser limitante. |
| `energy_conversion` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`energy_conversion` | Fração da irradiância que vira energia biologicamente útil (eficiência fotossintética bruta). | `0.05` | fração; [0,1] | Energia deixa de ser limitante para os produtores. | Produtores passam fome mesmo com estrela forte. | Casa com `energy_reference` do Evolution e `energy_requirement` aqui — os três vivem na MESMA escala (~0,05) e devem ser movidos juntos. |
| `nitrogen_demand` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`nitrogen_demand` | Demanda de referência de N na lei do mínimo. | `0.5` | N; >0 | N vira o limitante com mais facilidade. | N deixa de limitar. | O que governa é a razão `estoque/demanda`; alterar a demanda é equivalente a alterar o yield da Chemistry na direção oposta. |
| `phosphorus_demand` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`phosphorus_demand` | Demanda de referência de P. | `0.1` | P; >0 | P vira o limitante (comportamento oceânico realista). | P deixa de limitar. | Idem. `initial_state.phosphorus` é fixado IGUAL a esta demanda de propósito: o planeta nasce exatamente não-limitado por P. |
| `sulfur_demand` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`sulfur_demand` | Demanda de referência de S. | `0.2` | S; >0 | S vira o limitante. | S deixa de limitar. | Idem. |
| `optimal_temperature` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`optimal_temperature` | Centro da gaussiana térmica da habitabilidade ambiental. | `22.0` | °C | O planeta atual passa a ser lido como frio demais. | Passa a ser lido como quente demais. | Não confundir com `Genome.temp_optimum`: este é do AMBIENTE (capacidade), aquele é da COORTE (seleção). |
| `temperature_tolerance` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`temperature_tolerance` | Largura da janela térmica do ambiente. | `15.0` | °C; >0 | Capacidade quase insensível à temperatura — o clima deixa de matar. | Janela estreita: pequenas variações climáticas colapsam a capacidade. | É o que traduz 'o planeta esquentou' em 'a capacidade caiu'. Estreitar demais torna toda extinção térmica. |
| `water_requirement` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`water_requirement` | Água em que a aptidão hídrica satura. | `0.2` | unidade de água; ≥0 | Água vira limitante com mais facilidade. | Água deixa de limitar. | Também é o denominador da ESCASSEZ (`scarcity_fraction × requirement`). |
| `nutrient_requirement` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`nutrient_requirement` | Nutriente em que a aptidão nutricional satura. | `0.3` | unidade de nutriente; ≥0 | Nutriente vira limitante. | Nutriente deixa de limitar. | Idem; casa com `initial_state.nutrients`. |
| `energy_requirement` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`energy_requirement` | Energia em que a aptidão energética satura. | `0.04` | unidade de energia; ≥0 | Energia vira limitante. | Energia deixa de limitar. | **Mesmo limiar que `energy_reference` do Evolution**, lido da mesma grandeza. Mover um sem o outro descasa ambiente e coorte. |
| `max_carrying_capacity` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`max_carrying_capacity` | Capacidade de suporte com habitabilidade plena. | `100.0` | unidades de biomassa; >0 | Planeta comporta mais vida; a abiogênese (`abiogenesis_capacity = 35`) fica mais fácil. | Capacidade nunca alcança o limiar de abiogênese e o planeta permanece estéril. | **É o único acoplamento física→biologia** (ADR 0006). Mexer aqui move implicitamente o gatilho da abiogênese, que é medido em valor ABSOLUTO de capacidade. |
| `consumption_per_biomass` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`consumption_per_biomass` | Recurso retirado por unidade de biomassa por tick. | `0.001` | recurso por biomassa por tick; ≥0 | `consumed` sobe. | `consumed` cai. | `consumed` é publicado mas não realimenta a capacidade — é diagnóstico, não dreno. Ver *Achados* nº 6. |
| `capacity_event_threshold` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`capacity_event_threshold` | Variação RELATIVA da capacidade que emite `CarryingCapacityShift`. | `0.2` | fração; ≥0 | Menos eventos de capacidade. | Trilha inundada. | A saída de ZERO é caso à parte e sempre emite: é ela que dá causa ao `LifeEmerged` (ADR 0016). |
| `scarcity_fraction` | `src/ecosfera_ai/engines/resource/params.yaml`<br>`scarcity_fraction` | Fração do requisito abaixo da qual um recurso é declarado escasso. | `0.5` | fração; [0,1] | Escassez declarada com frequência. | Escassez quase nunca declarada. | Medida em FRAÇÃO DO REQUISITO porque água/nutriente/energia vivem em escalas incomparáveis (0,2 / 0,3 / 0,04). Emite UM recurso, o mais escasso — nunca três. |

---

## Evolução — seleção emergente

Não há parâmetro de algoritmo genético aqui: nem população, nem gerações, nem torneio. A
ausência é a consequência de o fitness global ter sido superado (ADR-ARCH-0001, ADR 0016).

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `growth_rate` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`growth_rate` | Fração do excedente local convertida em variação populacional por tick. | `0.15` | tick⁻¹; ≥0 | Comunidade responde rápido: booms e colapsos mais violentos, mais `MassMortality`. | Biomassa quase congelada; a seleção deixa de se manifestar em tempo de partida. | Multiplica o excedente JÁ calculado; valores altos podem levar `Δbiomassa` a exceder a própria biomassa em um tick (o piso em 0 protege, mas o transiente é irreal). |
| `metabolism_cost` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`metabolism_cost` | Custo de manutenção por unidade de metabolismo do genoma. | `0.4` | adimensional; ≥0 | Custo de existir sobe: a comunidade só se sustenta em ambientes muito bons. | A vida sobrevive quase em qualquer lugar — a seleção perde força. | Entra em `excedente = adequação − custo − predação`. Somado a `size_cost`, define o piso de adequação para sobreviver. |
| `size_cost` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`size_cost` | Custo por unidade de tamanho corporal. | `0.05` | adimensional; ≥0 | Pressão contra corpos grandes. | Tamanho deixa de custar. | Idem; `Genome.BOUNDS['size']` vai a 100, então este coeficiente pequeno já pesa muito num genoma grande. |
| `energy_reference` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`energy_reference` | Energia de referência do PRODUTOR na adequação local. | `0.04` | unidade de energia; >0 | Produtores passam a sofrer com a mesma irradiância. | Energia deixa de limitar a coorte. | **Escala crítica:** compara-se com `resource.energy_available` (~0,05), não com `solar_flux` (~1,0). O `fitness` legado usa 0,80 contra `solar_flux` — não são o mesmo número. |
| `crowding_weight` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`crowding_weight` | Quanto a ocupação do orçamento aperta a comunidade inteira. | `1.2` | adimensional; ≥0 | Densidade-dependência mais forte: a biomassa se acomoda ABAIXO da capacidade. | A comunidade cresce além da capacidade publicada — 'capacidade' deixa de ser limite. | É a densidade-dependência EMERGENTE — não há curva logística imposta. Calibrado para o excedente cruzar zero perto de `ocupação = 1`. Com capacidade zero, `occupancy = ∞` e `crowding → 0`, que é o que impede a comunidade de crescer num mundo inabitável. |
| `predation_weight` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`predation_weight` | Peso da pressão de predação (lida da Ecology, defasada) na sobrevivência. | `0.3` | adimensional; ≥0 | Predação passa a dominar a mortalidade e a causa diagnosticada vira `PREDATION_PRESSURE`. | A pirâmide trófica deixa de realimentar a comunidade. | Único termo do laço Ecology→Evolution. Também entra em `_limiting_cause`: mexer aqui muda a CAUSA que o Tutor narra, não só o número. |
| `mutation_sigma` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`mutation_sigma` | Desvio-padrão da mutação como FRAÇÃO da amplitude de cada traço. | `0.02` | fração da faixa; ≥0 | Deriva genética rápida: mais `SpeciationOccurred` e `TraitShift`. | Genoma médio praticamente congelado — a adaptação some. | Relativo à faixa (`Genome.BOUNDS`) de propósito: um sigma absoluto moveria `metabolism` (0,05–3) e `temp_optimum` (−40–80) em escalas incomparáveis. |
| `reproduction_threshold` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`reproduction_threshold` | Excedente local acima do qual a coorte geraria descendência divergente. | `0.25` | adimensional | (sem efeito) | (sem efeito) | **Carregado mas NUNCA consumido** — nenhum código lê `params.reproduction_threshold`. Ver *Achados* nº 1. Calibrar aqui não muda nada. |
| `speciation_threshold` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`speciation_threshold` | Distância genética normalizada que caracteriza espécie nova. | `0.12` | distância [0,1]; >0 | Especiação rara: `species_richness` estagna. | Especiação a cada tick até bater em `max_species`. | A distância é normalizada por faixa (`Genome.distance`). Interage diretamente com `mutation_sigma`: os dois juntos fixam a VELOCIDADE DE ESPECIAÇÃO. |
| `extinction_population` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`extinction_population` | Biomassa abaixo da qual a comunidade é declarada extinta. | `0.01` | unidades de biomassa; ≥0 | Extinção declarada mais cedo — planetas morrem com facilidade. | A comunidade sobrevive como traço residual e pode ressuscitar. | É a travessia que emite `SpeciesExtinct` e zera `species_richness`. Também é o piso comparado em `_richness_change`. |
| `abiogenesis_capacity` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`abiogenesis_capacity` | Capacidade de suporte mínima para a primeira vida surgir. | `35.0` | unidades de biomassa; ≥0 | Abiogênese mais tarde ou nunca — planeta estéril. | Vida surge quase imediatamente e a fase pré-biótica desaparece da narrativa. | **Medida em valor ABSOLUTO de capacidade**, logo acoplada a `max_carrying_capacity` (35 de 100 ⇔ habitabilidade ≥ 0,35). Mover a capacidade máxima move este gatilho sem que a chave mude. |
| `founder_population` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`founder_population` | Biomassa com que a primeira comunidade nasce. | `1.0` | unidades de biomassa; >0 | Vida nasce grande e cresce mais rápido. | Vida nasce frágil e pode se extinguir no tick seguinte. | Comparar com `extinction_population` (0,01): um fundador abaixo dela nasceria já extinto. |
| `max_species` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`max_species` | Teto de riqueza de espécies (contenção de custo, RSK Inc 3). | `12` | contagem; ≥0 | Riqueza pode crescer mais. | Riqueza trava cedo e a especiação deixa de ter efeito visível. | É contenção, não ciência. `species_richness` é um ESCALAR — não há identidades por espécie no Engine (P-01). |
| `mass_mortality_threshold` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`mass_mortality_threshold` | Fração da biomassa perdida em UM tick que caracteriza mortandade em massa. | `0.06` | fração; (0,1] | Evento raro — choques moderados passam despercebidos. | A variação de rotina da comunidade vira evento e a trilha perde sinal. | É TRAVESSIA (antes vs. depois), não estado. Calibrado acima da variação de rotina; interage com `growth_rate`, que governa essa variação. |
| `trait_shift_threshold` | `src/ecosfera_ai/engines/evolution/params.yaml`<br>`trait_shift_threshold` | Variação de `temp_optimum` médio que emite `TraitShift`. | `0.05` | °C; ≥0 | Menos eventos de deriva de traço. | Cada mutação vira evento. | Só observa `temp_optimum` — os outros cinco traços derivam sem evento próprio. |

---

## Ecologia — dinâmica trófica

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `steps_per_tick` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`steps_per_tick` | Passos da dinâmica trófica por tick. | `1` | contagem; ≥0 | Cadeia trófica resolve mais rápido dentro do mesmo tick; predação mais intensa. | Em 0, a pirâmide congela (só a renormalização atua). | Cadência do M3 (ADR 0016): 1 passo por tick × `era_length: 10` equivale ao lote de 12 por era do modelo anterior, mas lendo ambiente ATUALIZADO. |
| `growth_rate` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`growth_rate` | Crescimento logístico intrínseco dos produtores contra a capacidade. | `0.35` | tick⁻¹; ≥0 | Produtores recuperam rápido de qualquer pastejo. | Base da pirâmide não se recompõe e a cadeia colapsa de baixo. | É o único termo com `(1 − N/K)` sobre a `carrying_capacity` cheia; os consumidores usam `consumer_capacity_share`. |
| `predation_rate` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`predation_rate` | Eficiência de captura por unidade de predador × presa (Lotka–Volterra). | `0.015` | tick⁻¹; ≥0 | **Oscilação predador-presa mais violenta**, com risco de colapso da presa. | Predadores não conseguem comer: níveis superiores nunca se estabelecem. | A captura é limitada ao estoque de presa (`min(...)`) — sem isso predadores somados comeriam mais presa do que existe e a diferença viraria biomassa do nada. |
| `conversion_efficiency` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`conversion_efficiency` | Fração da presa capturada convertida em biomassa do consumidor. | `0.3` | fração; [0,1] | Níveis superiores se sustentam mais facilmente; pirâmide mais alta. | Cadeia achata em dois níveis (predadores morrem de fome). | Entra em `viability_threshold = mortality/(conversão × predação)` — o limiar de sucessão é DERIVADO, não configurado. |
| `mortality_rate` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`mortality_rate` | Mortalidade natural dos consumidores. | `0.12` | fração por tick; [0,1] | Consumidores precisam de muito mais presa para existir (limiar de viabilidade sobe). | Consumidores acumulam e a pirâmide tende a inverter (contida por `max_consumer_share`). | Também é a taxa de decaimento do produtor quando a capacidade é zero. |
| `demographic_noise` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`demographic_noise` | Ruído demográfico multiplicativo sobre o produtor (RNG semeado). | `0.01` | fração; ≥0 | Populações erráticas; colapsos por acaso. | Dinâmica determinística. | Semeado, portanto replayável. Aplicado só ao produtor. |
| `min_viable_population` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`min_viable_population` | Piso abaixo do qual um nível é zerado. | `0.001` | biomassa; ≥0 | Níveis somem com mais facilidade — extinções tróficas frequentes. | Resíduos infinitesimais sobrevivem para sempre. | Zerar um nível é irreversível dentro do passo: a sucessão só o repõe se o nível de baixo cruzar `viability_threshold`. |
| `herbivore_share` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`herbivore_share` | Fração do produtor cedida ao herbívoro quando o nível se estabelece. | `0.25` | fração; [0,1] | Herbivoria nasce forte e pode derrubar a base. | Herbívoro nasce quase inviável e morre no primeiro passo. | O semeio acontece UMA vez por nível: se morrer, só volta quando o nível de baixo cruzar o limiar outra vez. |
| `predator_share` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`predator_share` | Fração do herbívoro cedida ao predador quando o nível se estabelece. | `0.05` | fração; [0,1] | Predadores nascem fortes. | Predadores nascem inviáveis. | Idem. |
| `max_consumer_share` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`max_consumer_share` | Teto da soma dos consumidores como fração do total, na renormalização. | `0.5` | fração; [0,1] | Pirâmide pode inverter (Elton, 1927 — cientificamente inválido). | Consumidores espremidos; a base absorve quase tudo. | **Invariante de Elton.** Sem este teto, a renormalização escala os predadores para cima quando os produtores colapsam, criando um planeta de predadores sem presa. |
| `consumer_capacity_share` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`consumer_capacity_share` | Fração da capacidade ambiental disponível a CADA nível consumidor. | `0.6` | fração; [0,1] | Consumidores crescem mais; pirâmide mais alta e mais 'cheia'. | Cadeia achata em dois níveis (medido: 0,25 matava os predadores de fome). | Q11 (validação Tássia, ADR 0019): é a MESMA `carrying_capacity` do Resource, lida por mais níveis — não uma segunda capacidade, e não há dupla contagem porque a renormalização ajusta o total. |
| `collapse_threshold` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`collapse_threshold` | Participação de um nível no total abaixo da qual ele é declarado colapsado. | `0.05` | fração; [0,1] | `TrophicCollapse` declarado com facilidade. | Colapso quase nunca narrado. | É travessia de PARTICIPAÇÃO, não de valor absoluto: um nível pode encolher sem colapsar se todos encolherem juntos. |
| `decline_threshold` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`decline_threshold` | Queda relativa de um nível que emite `PopulationDeclined`. | `0.2` | fração; [0,1] | Menos eventos de declínio. | Oscilação de rotina vira evento. | Interage com `predation_rate`: uma oscilação predador-presa forte dispara declínios em todo ciclo. |
| `max_agents` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`max_agents` | Teto de populações simuladas (contenção de custo, RSK Inc 3). | `24` | contagem | (sem efeito) | (sem efeito) | **Carregado mas não consumido** pelo Ecology Engine — ele opera sobre três agregados, não sobre agentes. Ver *Achados* nº 2. |
| `max_steps` | `src/ecosfera_ai/engines/ecology/params.yaml`<br>`max_steps` | Teto absoluto de passos por era (contenção de custo). | `50` | contagem | (sem efeito) | (sem efeito) | **Carregado mas não consumido**; quem governa a cadência é `steps_per_tick`. Ver *Achados* nº 2. |

---

## Eventos — o Diretor e o catálogo

### Ritmo e contexto

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `scheduling_probability` | `src/ecosfera_ai/engines/event/params.yaml`<br>`scheduling_probability` | Probabilidade, por tick, de o Diretor agendar um evento quando nada está pendente. | `0.017` | probabilidade; [0,1] | **Ritmo de eventos acelera** — o extraordinário vira rotina e o aluno perde a referência do normal. | Partidas inteiras sem evento algum. | Calibrado para ~1 evento a cada 60 ticks. O sorteio consome o RNG do Engine `event` a cada tick: mudar o valor muda a TRAJETÓRIA INTEIRA sob a mesma semente. |
| `quiet_ticks_after` | `src/ecosfera_ai/engines/event/params.yaml`<br>`quiet_ticks_after` | Silêncio obrigatório após o fim de um evento. | `40` | ticks; ≥0 | Mais tempo de linha de base entre catástrofes. | Catástrofes encadeiam e o planeta nunca volta ao normal. | É o contraste com a linha de base que sustenta a lição; sem ele o aluno perde a referência. |
| `max_active_events` | `src/ecosfera_ai/engines/event/params.yaml`<br>`max_active_events` | Teto declarado de eventos simultâneos. | `2` | contagem | (sem efeito) | (sem efeito) | **Carregado mas não consumido**; a `EventSlice` comporta UM evento ativo por construção (`active_kind` é escalar). Ver *Achados* nº 3. |
| `context.ice_age_max_temperature` | `src/ecosfera_ai/engines/event/params.yaml`<br>`context.ice_age_max_temperature` | Acima desta temperatura a era glacial não é sorteada. | `24.0` | °C | Era glacial passa a ser sorteável em planetas quentes (fisicamente incoerente). | Era glacial some do catálogo em planetas normais. | Não é roteiro — é recusa do absurdo. Lida do world-state do MESMO tick (o Event roda por último). |
| `context.drought_min_temperature` | `src/ecosfera_ai/engines/event/params.yaml`<br>`context.drought_min_temperature` | Abaixo desta temperatura a seca não é sorteada. | `5.0` | °C | Seca some de planetas temperados. | Seca sorteada em mundos congelados, onde a água não é o limitante. | Idem. |
| `context.wildfire_min_biomass` | `src/ecosfera_ai/engines/event/params.yaml`<br>`context.wildfire_min_biomass` | Biomassa mínima para haver incêndio. | `5.0` | unidades de biomassa; ≥0 | Incêndio só em planetas muito vivos. | Incêndio em planeta sem o que queimar. | Idem. Lê `biota.biomass` do mesmo tick. |

### Catálogo — perfis de perturbação (`engines/event/params.yaml`, chave `catalog`)

Cada coeficiente é a perturbação **no pico**; a intensidade corrente é o pico × decaimento ×
severidade sorteada (`rng.uniform(0.6, 1.0)`). `mortality > 0` marca o evento como
**catastrófico** (mata independentemente de adaptação — ADR 0019).

| Evento | `kind` | `duration` | `decay` | `dust` | `cooling` | `drought` | `impact` | `mortality` | `supervolcanic` | `forecast_lead` | `weight` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `meteor` | `1` | `40` | `0.08` | `0.55` | `4.5` | `0.0` | `1.0` | `0.45` | `0.0` | `12` | `1.0` |
| `drought` | `2` | `35` | `0.0` | `0.0` | `0.0` | `0.55` | `0.0` | `0.0` | `0.0` | `8` | `1.4` |
| `wildfire` | `3` | `10` | `0.25` | `0.12` | `0.0` | `0.1` | `0.0` | `0.18` | `0.0` | `3` | `1.2` |
| `ice_age` | `4` | `120` | `0.0` | `0.0` | `6.0` | `0.15` | `0.0` | `0.0` | `0.0` | `25` | `0.5` |
| `storm` | `5` | `6` | `0.3` | `0.03` | `0.2` | `0.0` | `0.0` | `0.05` | `0.0` | `2` | `1.6` |
| `supervolcano` | `6` | `70` | `0.05` | `0.7` | `5.5` | `0.0` | `0.0` | `0.3` | `1.0` | `15` | `0.4` |

Como ler cada coluna:

| Coeficiente | O que controla | Quem consome |
|---|---|---|
| `kind` | Índice no catálogo; viaja como float na `EventSlice` (o Canal A é de floats). | `EventKind`, telegrafia |
| `duration` | Ticks de perturbação ativa. Fora da janela a perturbação é EXATAMENTE zero. | `decay_at` |
| `decay` | Constante do decaimento exponencial; `0` = degrau (a seca dura enquanto dura). | `decay_at` |
| `dust` | Poeira em suspensão no pico. | **Ninguém** — ver *Achados* nº 7 |
| `cooling` | Forçamento radiativo negativo (W/m²) subtraído do forçamento de estufa. | Climate Engine |
| `drought` | Fração da precipitação suprimida. | Hydrology Engine |
| `impact` | Energia do impacto no tick do evento (pico, não estoque). | **Ninguém** — ver *Achados* nº 7 |
| `mortality` | Fração da biomassa removida INDEPENDENTE de adaptação, no tick do evento. | Evolution Engine (aplica) + `_limiting_cause` (atribui a causa) |
| `supervolcanic` | Intensidade que multiplica a desgaseificação basal da Geology. | Geology Engine |
| `forecast_lead` | Ticks de antecedência do aviso (RF-019/020). | `EventForecast` + `EventSlice.forecast_*` |
| `weight` | Peso relativo no sorteio entre os eventos plausíveis. | `director.decide` |

---

## Núcleo — condições iniciais, eras e orçamento

`configs/simulation_params.yaml` guarda o que **não pertence a nenhum Engine**: condições
iniciais, faixas físicas, progressão de eras e o orçamento da moldura. A ciência de cada
domínio saiu daqui no M2 (ADR 0014).

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `timeline.era_length` | `configs/simulation_params.yaml`<br>`timeline.era_length` | Ticks que fecham uma era e geram um checkpoint append-only. | `10` | ticks; >0 | Eras longas: menos checkpoints, replay mais caro, mais trabalho ecológico por era. | Eras curtas: mais checkpoints e mais I/O. | É o denominador da equivalência de cadência da Ecology (`steps_per_tick × era_length`). Também define o custo do replay, que reexecuta do último checkpoint. |
| `initial_state.temperature` | `configs/simulation_params.yaml`<br>`initial_state.temperature` | Temperatura de partida do planeta. | `14.0` | °C | Parte mais quente do equilíbrio. | Parte mais fria. | Há uma lacuna CONHECIDA de ~3,6 °C até o equilíbrio do Climate (~17,6 °C), pinada em `KNOWN_EQUILIBRIUM_GAP_C`. Fechá-la é recalibração de clima, ainda não decidida. |
| `initial_state.co2` | `configs/simulation_params.yaml`<br>`initial_state.co2` | CO₂ de partida (pré-industrial, Etheridge et al. 1996). | `280.0` | ppm; ≥0 | Planeta parte com forçamento positivo — aquece de saída. | Parte com forçamento negativo — esfria. | **Precisa continuar igual** a `reference_co2` da Atmosphere e da Chemistry: é o que faz forçamento e troca ar↔oceano partirem de zero. |
| `initial_state.ocean_carbon` | `configs/simulation_params.yaml`<br>`initial_state.ocean_carbon` | Carbono dissolvido de partida. | `300.0` | ppm-equivalente; ≥0 | Oceano parte devolvendo carbono à atmosfera. | Oceano parte como sumidouro e aspira a atmosfera (defeito medido: CO₂ de 280→234 em 60 ticks). | **Precisa continuar igual** a `reference_ocean_carbon` da Chemistry (ADR 0012 §7). Campo em branco aqui não é 'planeta jovem' — é estado que a física não admite. |
| `initial_state.nutrients` | `configs/simulation_params.yaml`<br>`initial_state.nutrients` | Nutriente agregado de partida. | `0.3` | ≥0 | Capacidade nasce mais alta e a abiogênese antecipa. | Capacidade nasce ~0 e a abiogênese atrasa (~50 ticks, medido). | Fixado igual a `nutrient_requirement` do Resource: o ponto em que o nutriente é exatamente não-limitante. |
| `initial_state.nitrogen` | `configs/simulation_params.yaml`<br>`initial_state.nitrogen` | N de partida. | `0.5` | ≥0 | N deixa de limitar por mais tempo. | N limita de saída. | Fixado igual a `nitrogen_demand`. |
| `initial_state.phosphorus` | `configs/simulation_params.yaml`<br>`initial_state.phosphorus` | P de partida (o mais escasso, razão de Redfield). | `0.1` | ≥0 | P deixa de limitar. | P limita de saída. | Fixado igual a `phosphorus_demand`. |
| `initial_state.sulfur` | `configs/simulation_params.yaml`<br>`initial_state.sulfur` | S de partida. | `0.2` | ≥0 | S deixa de limitar. | S limita de saída. | Fixado igual a `sulfur_demand`. |
| `initial_state.water` | `configs/simulation_params.yaml`<br>`initial_state.water` | Estoque relativo de água líquida de partida. | `1.0` | ≥0 | Mais água disponível, capacidade maior. | Planeta seco, habitabilidade baixa. | É AGREGADO: a ponte o reparte nos quatro reservatórios no primeiro tick, uma única vez. |
| `initial_state.ice_cover` | `configs/simulation_params.yaml`<br>`initial_state.ice_cover` | Fração congelada da hidrosfera de partida. | `0.1` | fração; [0,1] | Albedo alto de saída — risco de bola de neve. | Planeta sem gelo, albedo mínimo. | A ponte deriva o gelo por `gelo = água·cobertura/(1−cobertura)` para que a fração resultante seja exatamente esta. |
| `initial_state.relief` | `configs/simulation_params.yaml`<br>`initial_state.relief` | Relevo médio de partida. | `0.2` | fração; [0,1] | Mais intemperismo de saída (nutriente e remoção de carbono). | Planeta plano: intemperismo seca. | Recortado por `BoundedFraction`. |
| `initial_state.volcanism` | `configs/simulation_params.yaml`<br>`initial_state.volcanism` | Vulcanismo de partida. | `1.0` | ≥0 | Mais carbono de saída. | Menos carbono. | Relaxa para `volcanism_baseline` da Geology; deve casar com ele para não haver transiente artificial. |
| `initial_state.salinity` | `configs/simulation_params.yaml`<br>`initial_state.salinity` | Salinidade de partida. | `0.35` | ≥0 | Circulação parte mais forte. | Parte mais fraca. | Deve casar com `reference_salinity` da Hydrology. |
| `initial_state.ocean_circulation` | `configs/simulation_params.yaml`<br>`initial_state.ocean_circulation` | Circulação termohalina de partida. | `0.5` | fração; [0,1] | Mais amortecimento térmico de saída. | Menos. | Deve casar com `circulation_baseline` da Hydrology. |
| `initial_state.biomass` | `configs/simulation_params.yaml`<br>`initial_state.biomass` | Biomassa de partida. | `0.0` | ≥0 | Planeta nasce com vida — a abiogênese nunca acontece e `LifeEmerged` nunca é emitido. | Planeta estéril até a capacidade cruzar `abiogenesis_capacity`. | Em zero, o Evolution entra no ramo de abiogênese; qualquer valor > 0 entra no ramo de seleção. |
| `engines.budget.max_duration_s` | `configs/simulation_params.yaml`<br>`engines.budget.max_duration_s` | Teto de tempo de um tick de um Engine (Spec §6). | `0.25` | segundos; >0 | Menos `DiagnosticEvent` de orçamento. | Ruído de diagnóstico em máquina lenta. | **Estourar o teto NÃO altera a simulação** — emite diagnóstico e nada mais. Reagir a ele faria a trajetória depender da carga da máquina. |
| `engines.budget.max_events` | `configs/simulation_params.yaml`<br>`engines.budget.max_events` | Teto de domain events por Engine por tick. | `500` | contagem; >0 | Menos diagnóstico. | Mais diagnóstico. | Idem — puramente observável. |
| `engines.budget.max_entities` | `configs/simulation_params.yaml`<br>`engines.budget.max_entities` | Teto de entidades processadas por Engine por tick. | `50000` | contagem; >0 | Menos diagnóstico. | Mais diagnóstico. | Idem. Este é o ÚNICO orçamento em vigor: os blocos `budget:` dos `params.yaml` de cada Engine são carregados e não aplicados (*Achados* nº 4). |

> **Nota — camada emergente legada.** Os blocos `fitness:`, `evolution:` e `ecology:` de
> `configs/simulation_params.yaml` alimentam o **caminho B** (`simulation_engine/biology/`,
> AG com DEAP + ABM com Mesa), que está **DORMENTE** desde o M3: `biology_enabled` é `False`
> por padrão porque aquele caminho usa aptidão ESCALAR, o que a DEC-01 proíbe (ADR 0017).
> Calibrá-los não afeta o world-state. Eles estão documentados em
> [`30-nucleo-e-plataforma.md`](30-nucleo-e-plataforma.md).

### Faixas físicas (`bounds`) — as travas que as invariantes aplicam

| Faixa | Valor atual | Aplicada por |
|---|---|---|
| `ice_cover` | `[0.0, 1.0]` | `BoundedFraction` sobre `hydrology.ice_fraction` |
| `relief` | `[0.0, 1.0]` | `BoundedFraction` sobre `geology.relief` |
| `ocean_circulation` | `[0.0, 1.0]` | `BoundedFraction` sobre `hydrology.ocean_circulation` |
| `water_min` | `0.0` | `PlanetState.apply` (núcleo legado) |
| `co2_min` | `0.0` | `PlanetState.apply` |
| `biomass_min` | `0.0` | `PlanetState.apply` |
| `energy_min` | `0.0` | `PlanetState.apply` |
| `solar_flux_min` | `0.0` | `PlanetState.apply` |
| `volcanism_min` | `0.0` | `PlanetState.apply` |
| `salinity_min` | `0.0` | `PlanetState.apply` |

---

## Constantes de módulo que funcionam como botão

Não moram em YAML, mas mudam comportamento — algumas delas mudam **toda trajetória gravada**.

| Parâmetro | Onde vive (arquivo/chave) | O que controla | Valor atual | Faixa/unidade | Efeito de AUMENTAR | Efeito de DIMINUIR | Invariante/risco ao mexer |
|---|---|---|---|---|---|---|---|
| `WORLD_STATE_VERSION` | `src/ecosfera_ai/shared_kernel/world_state.py` | Versão do esquema do world-state; um checkpoint diz sob qual formato foi escrito. | `5` | inteiro | Declara esquema novo — artefatos antigos passam a ser recusados no import. | Mentira sobre o formato: import silenciosamente degradado. | Subir SEMPRE que uma fatia ganhar/perder campo. `SimulationExport.from_json` recusa versões diferentes de propósito. |
| `EXPORT_FORMAT_VERSION` | `src/ecosfera_ai/shared_kernel/portable.py` | Versão do FORMATO do artefato portável (distinta da do world-state). | `1` | inteiro | Artefatos anteriores deixam de importar. | Idem, ao contrário. | Falhar alto é deliberado: um import degradado só apareceria como divergência de replay muito depois. |
| `EVENT_NAMESPACE` | `src/ecosfera_ai/shared_kernel/events.py` | Namespace UUID5 da derivação determinística de `event_id`. | `uuid.UUID('6f9619ff-8b86-d011-b42d-00c04fc964ff')` | UUID | **Nunca mexer.** | **Nunca mexer.** | Alterá-lo invalida os ids de TODOS os eventos já gravados e quebra a comparação de replay por `event_id`. |
| `_DIGEST_BYTES` | `src/ecosfera_ai/shared_kernel/rng.py` | Bytes do resumo BLAKE2b do `engine_id` que entram na `SeedSequence`. | `8` | bytes; >0 | Muda a entropia por Engine → **toda trajetória muda** sob a mesma semente. | Idem, e aumenta a chance de colisão entre nomes de Engine. | Botão de determinismo, não de ciência. Mexer invalida todo replay gravado. |
| `_BIOLOGY_SALT` | `src/ecosfera_ai/simulation_engine/biology/engine.py` | Sal que separa o fluxo de RNG da biologia por era do fluxo determinístico. | `2832` | inteiro | Muda a trajetória biológica do caminho por era (hoje DORMENTE). | Idem. | Sem ele, biologia e clima consumiriam a mesma sequência. Afeta só o caminho B (`biology_enabled=False` por padrão). |
| `_CO2_FLOOR` | `src/ecosfera_ai/engines/atmosphere/domain.py` | Piso do estoque de CO₂ dentro do logaritmo do forçamento. | `1e-06` | ppm; >0 | Forçamento mínimo menos negativo em planetas sem carbono. | Aproxima-se de `ln(0) = −∞` — forçamento infinito em vez de 'muito frio'. | É piso NUMÉRICO, não físico — por isso mora no código e não no YAML. |
| `TROPHIC_PRODUCER` / `TROPHIC_HERBIVORE` / `TROPHIC_PREDATOR` | `src/ecosfera_ai/simulation_engine/biology/genome.py` | Níveis tróficos discretos; `energy_match` só limita quem é produtor. | `1` / `2` / `3` | inteiros | Renumerar quebra a comparação `trophic_class > TROPHIC_PRODUCER`. | Idem. | `Genome.BOUNDS['trophic_level']` vai de 1,0 a 3,0 e `trophic_class` arredonda — os três valores e a faixa precisam concordar. |
| `Genome.BOUNDS` | `src/ecosfera_ai/simulation_engine/biology/genome.py` | Faixas válidas de cada traço; base da normalização da mutação e da distância genética. | `temp_optimum (-40,80)`, `temp_tolerance (1,60)`, `water_need (0,2)`, `size (0.01,100)`, `metabolism (0.05,3)`, `trophic_level (1,3)` | por traço | Faixa maior ⇒ `mutation_sigma` (fração da faixa) move mais o traço e `distance` normaliza mais fraco: especiação fica mais lenta. | Faixa menor ⇒ mutação menor e especiação mais rápida. | **Botão oculto de velocidade de especiação.** Ele multiplica `mutation_sigma` e divide `Genome.distance` — calibrar `speciation_threshold` sem olhar aqui é calibrar às cegas. |
| `OBSERVABLE_VARIABLES` | `src/ecosfera_ai/simulation_engine/state.py` | Variáveis que viram `Observation` para o motor de regras causais. | 11 variáveis (co2, temperature, ice_cover, water, biomass, energy, solar_flux, volcanism, relief, salinity, ocean_circulation) | tupla de nomes | Mais variáveis narráveis ao aluno. | Menos. | Precisa concordar com os `cause`/`effect` de `configs/causal_rules.yaml`: uma regra sobre variável não observável nunca dispara. |
| `CARBON_CHANNELS` | `src/ecosfera_ai/shared_kernel/timeseries.py` | Séries do ciclo do carbono extraídas de uma trajetória já executada. | 7 canais (geology_outgassing, atmosphere_co2, ocean_carbon, soil_carbon, air_sea_flux, biomass, temperature) | mapa nome→extrator | Mais séries para diagnosticar a dívida de carbono. | Menos visibilidade sobre o ADR 0020. | É observação LATERAL: consome snapshots, não roda tick. Ampliar aqui é seguro. |
| `ENGINE_ORDER` | `src/ecosfera_ai/engines/composition.py` | Ordem canônica de acoplamento do tick. | `astronomy → geology → chemistry → atmosphere → climate → hydrology → resource → evolution → ecology → event` | tupla de `engine_id` | — | — | **É a única fonte da ordem** e muda o tick de verdade. Reordenar exige revisar `lagged_reads` de todo mundo: `validate_graph` recusa no boot uma leitura para trás não declarada. |

---

## Invariantes que a calibração NÃO pode violar

Estas são travas duras. Uma calibração que as viole não é uma calibração agressiva — é um
defeito, e a suíte foi escrita para acusá-lo.

| Invariante | O que afirma | Onde vive | Quem a guarda |
|---|---|---|---|
| **Conservação de água** | `ocean + ice + vapour + freshwater` não muda além da tolerância declarada. | `ConservedTotal(name='water_conservation')` em `engines/composition.planet_invariants`, tolerância de `hydrology/params.yaml:conservation_tolerance` | Invariante em produção (emite `DiagnosticEvent`, **não repara**) + testes de conservação de água. Suprimir precipitação por seca não destrói água: o que não chove permanece vapor. |
| **Contabilidade de carbono (sem dupla contagem)** | O `air_sea_flux` é somado ao oceano pela Chemistry e subtraído da atmosfera pela Atmosphere — um fluxo, dois livros, sinais opostos. O carbono vulcânico tem UMA fonte (`geology.co2_flux`). | `ADR 0012`, `ADR 0018` | `test_carbon_is_not_double_counted` (integração). **Não há invariante de fatia**: a identidade atravessa duas fatias com donos diferentes, e uma invariante por delta não a enxerga. |
| **Não-negatividade de estoques** | Nenhum estoque físico fica negativo. | `NonNegativeStocks` sobre astronomy/atmosphere/geology/climate/hydrology/chemistry/resource/biota/ecology | Invariante em produção: **recorta em zero e registra** o recorte no Canal B. |
| **Frações confinadas** | `ice_fraction`, `relief` e `ocean_circulation` vivem em [0,1] (faixas de `configs/simulation_params.yaml:bounds`). | `BoundedFraction` em `planet_invariants` | Invariante em produção: recorta e registra. |
| **Um dono por fatia** | Cada `SliceRef` tem exatamente um Engine escritor; nenhum Engine lê estado interno de outro. | `shared_kernel/engine.validate_graph` (falha no BOOT) + `PlanetEngine._assert_contract` (falha no tick) | `EngineRegistry.__post_init__` valida no boot; contratos de `import-linter` no `pyproject.toml` barram import cruzado em CI. |
| **Leitura para trás declarada** | Ler uma fatia escrita mais adiante no mesmo tick é legítimo, mas precisa estar em `lagged_reads`. | `validate_graph` | Erro de boot com mensagem explicando ciclo não resolvido. |
| **Determinismo por semente** | A mesma semente reproduz a mesma trajetória, os mesmos eventos e os mesmos `event_id`. | `shared_kernel/rng` (RNG por `(seed, engine_id, tick)`), `events.deterministic_id` (UUID5, nunca `uuid4`), `replay.verify_replay` | `ReplayReport.deterministic`; divergência bloqueia merge (Spec §7). O tick é SÍNCRONO de propósito: corrotinas introduziriam ordem de escalonamento como variável oculta. |
| **Pureza da observabilidade** | A simulação nunca depende de logs, métricas ou do Event Store. O sink é acionado pelo Planet Engine DEPOIS de compor o tick. | `shared_kernel/observability`, `PlanetEngine._publish` (última fase do tick), Diretor puro (`engines/event/director`) | `tests/unit/test_observability_purity.py`; ADR 0022 §3 afirma a pureza estruturalmente (nenhum Engine importa a plataforma, verificado por AST) e funcionalmente (com e sem sink ⇒ trajetórias bit-a-bit idênticas). |
| **Orçamento não altera resultado** | Estourar `TickBudget` emite `DiagnosticEvent` e mais nada — nunca pula um Engine. | `PlanetEngine._diagnose` | ADR-ARCH-0002. Pular um Engine lento faria o resultado depender da carga da máquina. |
| **A pirâmide de biomassa não inverte** | Consumidores somados ≤ `max_consumer_share` do total; o produtor é a base que absorve o restante (Elton, 1927). | `engines/ecology/service._renormalised` | Defeito medido: a renormalização ingênua escalava predadores para cima quando os produtores colapsavam. |
| **A Ecology reparte, não cria nem destrói** | A biomassa TOTAL é da `BiotaSlice` (Evolution); a Ecology só a distribui entre três níveis. | `_renormalised` + a catástrofe aplicada na Evolution, não na Ecology | ADR 0016/0019. Aplicar a mortalidade catastrófica na Ecology descolava a soma trófica do total. |
| **Extinção catastrófica ≠ ecológica** | `catastrophic_mortality` remove biomassa SEM olhar o genoma; a causa diagnosticada é `CATASTROPHIC_EVENT` e tem precedência sobre os limitantes ecológicos. | `engines/evolution/service._limiting_cause` (a catástrofe vem primeiro) | ADR 0019. Colapsar as duas famílias faria o Tutor narrar toda extinção como falha de adaptação — a concepção equivocada que a plataforma existe para desfazer. |
| **`cause_code` é enum, nunca prosa** | O envelope carrega causa ESTRUTURADA; a frase pedagógica é do consumidor. | `DomainEvent.__post_init__` levanta `TypeError` | ADR-ARCH-0002, Correção 1. |
| **O Canal B registra travessia, não estado** | Eventos comparam antes e depois; testar o valor corrente contra um limiar emitiria o evento em todo tick de todo planeta. | `_notable` de Chemistry, Climate, Hydrology, Resource, Evolution, Ecology | ADR-ARCH-0002, Correção 2. Os zeros de abertura não contam como travessia. |

### O que a suíte NÃO guarda (e por quê)

- **Não existe invariante de conservação de carbono.** O carbono tem fonte legítima
  (desgaseificação) e sumidouro legítimo (absorção biótica, soterramento); o que precisa
  valer é a identidade contábil da troca ar↔oceano, e ela atravessa DUAS fatias com donos
  diferentes. Uma invariante que roda por delta, sobre uma fatia, não a enxerga — e fazer o
  Planet Engine distinguir fonte de troca seria pôr ciência dentro do orquestrador, o que o
  ADR-ARCH-0001 proíbe. A verificação vive em teste de integração.
- **Nenhum teste rodava além de ~600 ticks** até o M5. A suíte é forte em correção POR TICK e
  passa perfeitamente enquanto o sistema derrapa em TRAJETÓRIA — foi assim que a dívida de
  carbono ficou invisível (ADR 0020).

---

## Índice reverso — quero calibrar X, vá para

| Quero ajustar… | Parâmetros exatos | Cuidado |
|---|---|---|
| Oscilação predador-presa (amplitude e período) | `ecology/params.yaml`: `predation_rate`, `conversion_efficiency`, `mortality_rate`, `growth_rate`, `consumer_capacity_share` | `viability_threshold = mortality/(conversão×predação)` é DERIVADO — mexer numa das três move o limiar de sucessão junto. `max_consumer_share` é a trava de Elton e não deve subir para 'deixar oscilar mais'. |
| Ritmo dos eventos extraordinários | `event/params.yaml`: `scheduling_probability`, `quiet_ticks_after`, `catalog.*.weight`, `catalog.*.duration` | `scheduling_probability` consome o RNG a cada tick: alterá-la muda a trajetória inteira sob a mesma semente, não só o ritmo. |
| Quanto um evento DÓI | `event/params.yaml`: `catalog.<evento>.cooling`, `.drought`, `.mortality`, `.supervolcanic`, `.decay`, `.duration` | `mortality > 0` marca o evento como CATASTRÓFICO (ADR 0019) e muda a CAUSA narrada. `dust` e `impact` não têm consumidor (*Achados* nº 7). |
| Velocidade de especiação | `evolution/params.yaml`: `mutation_sigma`, `speciation_threshold`, `max_species`; **e** `Genome.BOUNDS` em `simulation_engine/biology/genome.py` | As faixas do genoma normalizam tanto a mutação quanto a distância: calibrar o limiar sem olhar as faixas é calibrar às cegas. |
| Sensibilidade climática (°C por duplicação de CO₂) | `climate/params.yaml`: `climate_sensitivity`; `atmosphere/params.yaml`: `forcing_coefficient`, `reference_co2` | 3,7 W/m² ≈ uma duplicação. `climate_sensitivity = 0.8` ⇒ ~3 °C/duplicação (IPCC AR6). Mexer em `reference_co2` exige mexer também em `initial_state.co2` e no `reference_co2` da Chemistry. |
| Temperatura de equilíbrio do planeta | `climate/params.yaml`: `equilibrium_offset`, `energy_to_temp`, `base_albedo`; `astronomy/params.yaml`: `luminosity`, `orbital_radius` | Existe uma lacuna conhecida de ~3,6 °C entre a condição inicial e o equilíbrio (`KNOWN_EQUILIBRIUM_GAP_C`). Fechá-la é recalibração, não conserto de bug. |
| Rampa de CO₂ / dívida de carbono (ADR 0020, P-02) | `geology/params.yaml`: `outgassing_base`, `volcanism_baseline`, `tectonic_activity`; `atmosphere/params.yaml`: `weathering_coeff`; `chemistry/params.yaml`: `burial_coeff`, `ocean_carbon_capacity` | **Dívida já mapeada — não calibre contra ela às cegas.** Não existe equilíbrio de CO₂ em nenhuma versão: 870 ppm e subindo em t=3000, deriva positiva em toda semente medida. Instrumente com `shared_kernel/timeseries` antes de mexer. |
| Quando a vida surge (abiogênese) | `evolution/params.yaml`: `abiogenesis_capacity`, `founder_population`; `resource/params.yaml`: `max_carrying_capacity` e as quatro demandas; `configs/simulation_params.yaml`: `initial_state.nutrients/nitrogen/phosphorus/sulfur` | O gatilho é ABSOLUTO (capacidade ≥ 35 de 100). Mover `max_carrying_capacity` move o gatilho sem que a chave da abiogênese mude. |
| Quão fácil é a comunidade morrer | `evolution/params.yaml`: `extinction_population`, `metabolism_cost`, `size_cost`, `crowding_weight`, `predation_weight`; `resource/params.yaml`: `temperature_tolerance` | `_limiting_cause` decide a CAUSA narrada por comparação entre termos: mudar os pesos muda a explicação que o aluno recebe, não só a estatística. |
| Volume da trilha (Event Store) | Todos os `*_threshold`, `*_bands`, `shift_threshold`, `eruption_threshold`, `ice_event_threshold`, `decline_threshold`, `collapse_threshold` | São limiares de OBSERVABILIDADE: não alteram a trajetória, só o que é narrado. Baixá-los transforma o Event Store em log de debug. |
| Velocidade do ciclo da água | `hydrology/params.yaml`: `evaporation_coeff`, `precipitation_coeff`, `runoff_coeff`, `melt_coeff`, `freeze_coeff` | Nenhum destes pode criar água: a soma dos quatro reservatórios é invariante testada, com tolerância em `conservation_tolerance`. |
| Estações / variação de insolação | `astronomy/params.yaml`: `eccentricity_kick`, `timestep`, `orbital_radius` | `eccentricity_kick` só é lido na CRIAÇÃO do planeta — não afeta planetas já persistidos. |

---

## Dívidas conhecidas — não calibre contra elas

| Dívida | Registro | O que ela significa para quem calibra |
|---|---|---|
| **Termostato de carbono (P-02)** | `docs/adr/0020-long-horizon-carbon-instability.md`, `docs/decisions/pending.md` | Não existe equilíbrio de CO₂ em versão alguma: 870 ppm e subindo em t=3000, deriva positiva em **toda** semente medida (+53,7 / +16,4 / +35,5 ppm na cauda). Não é causado pelo M4 nem pela Q11 — o M3 é igual ou pior. Calibrar `weathering_coeff` ou `burial_coeff` "porque o CO₂ sobe" é mexer num sintoma cuja causa está registrada e ainda não diagnosticada. Instrumente com `shared_kernel/timeseries` (7 canais de carbono) antes. |
| **Oxigênio / Grande Oxigenação** | `docs/decisions/deferred.md` | `atmosphere.oxygen` foi **removido** no M5 (`WORLD_STATE_VERSION` 4→5): existia desde o M1 e nunca teve escritor. Não há parâmetro de oxigênio para calibrar — a ciência está AUSENTE, não zerada. Modelá-la exige produção acoplada à biomassa fotossintética, sumidouros e o acoplamento metano→clima. |
| **Horizonte válido ~600 ticks** | ADR 0020 | Acima disso a trajetória entra na rampa de carbono. Qualquer calibração validada só em horizonte curto pode estar compensando a rampa sem que ninguém perceba. |
| **`/species` e o que ele significa (P-01)** | `docs/decisions/pending.md` | O Evolution Engine **não tem espécies**: modela a comunidade como UM genoma médio, e `species_richness` é um escalar. `max_species` e `speciation_threshold` calibram uma CONTAGEM, não um censo de identidades. |
| **Caminho B dormente (ADR 0017)** | `docs/adr/0017-optional-biology-and-the-two-paths-debt.md` | Os blocos `fitness`/`evolution`/`ecology` de `configs/simulation_params.yaml` calibram um caminho desligado por padrão (`biology_enabled=False`), porque ele usa aptidão escalar que a DEC-01 proíbe. |
| **Lacuna de equilíbrio térmico (~3,6 °C)** | `test_baseline_is_physics.py`, `KNOWN_EQUILIBRIUM_GAP_C` | `initial_state.temperature = 14,0` mas o equilíbrio do Climate com estes parâmetros é ~17,6 °C. O planeta aquece na partida só para alcançá-lo. Está PINADO para não crescer em silêncio; fechá-lo é recalibração de clima, ainda não decidida. |
| **Rehidratação / `PlanetState` como estado persistido** | ADR 0015, `engines/bridge.py` | A borda HTTP e a persistência ainda guardam o `PlanetState`, não o `WorldStateSnapshot`. Taxas e grandezas derivadas (`co2_flux`, `greenhouse_forcing`, `pressure`) nascem em zero a cada rehidratação e são recalculadas no primeiro tick. Por isso o Atmosphere deriva a faixa anterior do ESTOQUE, e não do forçamento gravado. |

---

**Achados desta auditoria** (parâmetros carregados e não consumidos, campos sem leitor):
[`90-achados-da-auditoria.md`](90-achados-da-auditoria.md).
