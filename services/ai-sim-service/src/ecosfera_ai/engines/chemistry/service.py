"""Chemistry Engine — carbono não-atmosférico, N/P/S, nutrientes e pH (M2).

Fecha o ciclo do carbono que o M1 abriu pela metade. A Atmosphere é dona do
estoque ATMOSFÉRICO desde o ADR 0010; este Engine é dono do estoque OCEÂNICO e
do sedimento, e publica o `air_sea_flux` que liga os dois.

O sinal do fluxo é a decisão que evita dupla contagem: `air_sea_flux > 0`
significa "o oceano absorve da atmosfera". Este Engine SOMA esse número ao
próprio reservatório; a Atmosphere o SUBTRAI do dela. Um fluxo, dois livros,
sinais opostos (ADR 0012).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecosfera_ai.engines.chemistry.contracts import (
    ENGINE_ID,
    LAGGED_READS,
    READS,
    WRITES,
    ChemistryEngineParams,
    load_params,
)
from ecosfera_ai.engines.chemistry.domain import (
    air_sea_flux,
    carbon_burial,
    element_change,
    nutrient_change,
    ocean_ph,
)
from ecosfera_ai.engines.chemistry.events import (
    CARBON_FLUX_SHIFT,
    NUTRIENT_DEPLETION,
    OCEAN_ACIDIFICATION,
    ChemistryCauseCode,
)
from ecosfera_ai.shared_kernel.engine import TickContext, TickResult
from ecosfera_ai.shared_kernel.events import DomainEvent, EventEmitter
from ecosfera_ai.shared_kernel.world_state import SliceRef, StateDelta


@dataclass(slots=True)
class ChemistryEngine:
    """Implementa a porta `Engine` (Spec §5.2) para o domínio biogeoquímico."""

    params: ChemistryEngineParams = field(default_factory=load_params)
    engine_id: str = ENGINE_ID
    reads: frozenset[SliceRef] = READS
    lagged_reads: frozenset[SliceRef] = LAGGED_READS
    writes: SliceRef = WRITES

    def tick(self, ctx: TickContext) -> TickResult:
        current = ctx.snapshot.chemistry
        geology = ctx.snapshot.geology
        # Leitura DEFASADA e declarada: a Atmosphere roda depois deste Engine, e
        # o CO2 que se lê aqui é o do tick anterior. É essa defasagem de um passo
        # que quebra o ciclo chemistry<->atmosphere sem desfazer o acoplamento.
        atmospheric_co2 = ctx.snapshot.atmosphere.co2

        flux = air_sea_flux(atmospheric_co2, current.ocean_carbon, self.params)
        burial = carbon_burial(current.ocean_carbon, self.params)
        ocean_carbon = max(0.0, current.ocean_carbon + flux - burial)
        # O soterrado não desaparece: vira sedimento. Contabilizá-lo é o que
        # torna a conservação de carbono VERIFICÁVEL — sem este livro, o teste de
        # balanço confundiria sumidouro com vazamento.
        soil_carbon = current.soil_carbon + burial

        d_nutrients = nutrient_change(
            current.nutrients, geology.relief, geology.volcanism, self.params
        )
        nutrients = max(0.0, current.nutrients + d_nutrients)

        d_nitrogen = element_change(
            current.nitrogen,
            geology.relief,
            geology.volcanism,
            self.params.nitrogen_yield,
            self.params,
        )
        d_phosphorus = element_change(
            current.phosphorus,
            geology.relief,
            geology.volcanism,
            self.params.phosphorus_yield,
            self.params,
        )
        d_sulfur = element_change(
            current.sulfur,
            geology.relief,
            geology.volcanism,
            self.params.sulfur_yield,
            self.params,
        )

        ph = ocean_ph(ocean_carbon, self.params)
        events = self._notable(
            ctx,
            ph_before=current.ph,
            ph_after=ph,
            nutrients_before=current.nutrients,
            nutrients_after=nutrients,
            flux_before=current.air_sea_flux,
            flux_after=flux,
            ocean_carbon=ocean_carbon,
        )

        return TickResult(
            delta=StateDelta(
                engine_id=self.engine_id,
                tick=ctx.tick,
                writes=self.writes,
                values={
                    "ocean_carbon": ocean_carbon - current.ocean_carbon,
                    "soil_carbon": soil_carbon - current.soil_carbon,
                    "nutrients": nutrients - current.nutrients,
                    "nitrogen": d_nitrogen,
                    "phosphorus": d_phosphorus,
                    "sulfur": d_sulfur,
                    "ph": ph - current.ph,
                    # Valor do TICK, não acumulado: o delta o reposiciona
                    # substituindo o do tick anterior, como o `co2_flux` da
                    # geologia. Quem o lê (Atmosphere) lê uma taxa, não um estoque.
                    "air_sea_flux": flux - current.air_sea_flux,
                },
                caused_by=tuple(e.event_id for e in events),
            ),
            events=events,
            entities_processed=6,  # carbono oceânico, sedimento, nutrientes, N, P, S
        )

    def _notable(
        self,
        ctx: TickContext,
        *,
        ph_before: float,
        ph_after: float,
        nutrients_before: float,
        nutrients_after: float,
        flux_before: float,
        flux_after: float,
        ocean_carbon: float,
    ) -> tuple[DomainEvent, ...]:
        """Só a TRAVESSIA de patamar vira evento — nunca o estado contínuo.

        As três regras aqui comparam ANTES e DEPOIS, e não testam o valor
        corrente contra um limiar. A diferença não é estilística: uma fatia nasce
        zerada, e `nutrientes == 0` está abaixo do limiar de escassez, de modo que
        um teste sobre o valor corrente emitiria `NutrientDepletion` em TODO tick
        de TODO planeta desde o primeiro. Seria o ruído que o ADR-ARCH-0002
        (Correção 2) proíbe — o Canal B registra o que MUDOU.

        Pelo mesmo motivo, os zeros de abertura não contam como travessia: zero
        não é "ácido" nem "sem fluxo", é ausência de medida.
        """
        emitter = EventEmitter(engine_id=self.engine_id, seed=ctx.seed, tick=ctx.tick, era=ctx.era)
        events: list[DomainEvent] = []

        acid = self.params.acidification_threshold
        if ph_before > 0.0 and ph_before >= acid > ph_after:
            events.append(
                emitter.emit(
                    OCEAN_ACIDIFICATION,
                    ChemistryCauseCode.CARBON_DISSOLUTION,
                    location={"region_id": "ocean"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=["ph:low"],
                    resources=["co2"],
                    cause_detail={
                        "ph": ph_after,
                        "ph_before": ph_before,
                        "ocean_carbon": ocean_carbon,
                    },
                    # A causa vem pelo Canal A: o carbono dissolvido neste tick
                    # veio do gradiente com a atmosfera.
                    causation_id=ctx.caused_by_slice(SliceRef.ATMOSPHERE),
                )
            )

        scarce = self.params.nutrient_depletion_threshold
        if nutrients_before >= scarce > nutrients_after:
            events.append(
                emitter.emit(
                    NUTRIENT_DEPLETION,
                    ChemistryCauseCode.NUTRIENT_EXHAUSTION,
                    location={"region_id": "global"},
                    participants=[f"engine:{self.engine_id}"],
                    environmental_factors=["nutrients:low"],
                    resources=["nutrients"],
                    cause_detail={
                        "nutrients": nutrients_after,
                        "nutrients_before": nutrients_before,
                    },
                    causation_id=ctx.caused_by_slice(SliceRef.GEOLOGY),
                )
            )

        # O fluxo só é notável quando TROCA DE SENTIDO: o oceano deixa de absorver
        # e passa a devolver carbono, ou o contrário. É a inversão que muda a
        # história do planeta, não a magnitude de um tick qualquer.
        reversed_direction = flux_before != 0.0 and (flux_after > 0.0) != (flux_before > 0.0)
        if reversed_direction and flux_after != 0.0:
            absorbing = flux_after > 0.0
            events.append(
                emitter.emit(
                    CARBON_FLUX_SHIFT,
                    ChemistryCauseCode.CARBON_DISSOLUTION
                    if absorbing
                    else ChemistryCauseCode.CARBON_OUTGASSING,
                    location={"region_id": "ocean"},
                    participants=[f"engine:{self.engine_id}"],
                    resources=["co2"],
                    cause_detail={
                        "air_sea_flux": flux_after,
                        "direction": "absorbing" if absorbing else "outgassing",
                        "ocean_carbon": ocean_carbon,
                    },
                    causation_id=ctx.caused_by_slice(SliceRef.ATMOSPHERE),
                )
            )

        return tuple(events)
