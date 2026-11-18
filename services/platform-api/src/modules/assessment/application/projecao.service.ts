import {
  Inject,
  Injectable,
  type OnApplicationBootstrap,
  type BeforeApplicationShutdown,
} from '@nestjs/common';
import type { Logger } from 'pino';
import { DataSource, type EntityManager } from 'typeorm';

import {
  CONFIGURACAO,
  type Configuracao,
} from '../../../shared/config/configuracao';
import type { Json } from '../../../shared/database/colunas';
import { EventoProcessadoEntity } from '../../../shared/eventos/eventos.entity';
import {
  ASSESSMENT_EVENT_SOURCE,
  type AssessmentEventSource,
  type ResultadoDoTratamento,
} from '../../../shared/eventos/portas';
import { LOGGER } from '../../../shared/observabilidade/logger';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import { ConsentimentoEntity } from '../../identity/infrastructure/persistencia/consentimento.entity';
import { UsuarioEntity } from '../../identity/infrastructure/persistencia/usuario.entity';
import {
  CompetenciaEntity,
  HabilidadeBnccEntity,
} from '../../education/infrastructure/persistencia/curriculo.entity';
import { PlanetaMetaEntity } from '../../orchestration/infrastructure/persistencia/planeta.entity';
import {
  DadosCompetenciaAtualizada,
  DadosEvidenciaGerada,
  DadosRubricaAvaliada,
  EnvelopeConsumido,
} from '../domain/eventos';
import {
  AvaliacaoEntity,
  EvidenciaEntity,
  PerfilCognitivoEntity,
} from '../infrastructure/persistencia/avaliacao.entity';

/**
 * Projeção de EvidênciaGerada / CompetênciaAtualizada / RubricaAvaliada no modelo de leitura
 * (ADR 0013). Idempotente por eventId. Respeita o consentimento `learning_assessment`.
 */
@Injectable()
export class ProjecaoDeAvaliacao
  implements OnApplicationBootstrap, BeforeApplicationShutdown
{
  constructor(
    private readonly ds: DataSource,
    private readonly consentimento: ServicoDeConsentimento,
    @Inject(ASSESSMENT_EVENT_SOURCE)
    private readonly fonte: AssessmentEventSource,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(LOGGER) private readonly logger: Logger,
  ) {}

  async onApplicationBootstrap(): Promise<void> {
    if (this.config.EVENTS_CONSUMER_ENABLED)
      await this.fonte.iniciar((e) => this.tratar(e));
  }

  /** Antes do fechamento das conexões: termina o evento em curso e para de ler o stream. */
  async beforeApplicationShutdown(): Promise<void> {
    await this.fonte.parar();
  }

  async tratar(bruto: unknown): Promise<ResultadoDoTratamento> {
    const env = EnvelopeConsumido.safeParse(bruto);
    if (!env.success) {
      this.logger.warn(
        { issues: env.error.issues.length },
        'evento de avaliação com formato inválido; ignorado',
      );
      return 'ignored';
    }
    const e = env.data;
    const studentId = (e.data as { studentId?: unknown }).studentId;
    if (typeof studentId !== 'string') return 'ignored';
    const aluno = await this.ds.getRepository(UsuarioEntity).findOne({
      where: { id: studentId },
      select: {
        id: true,
        schoolId: true,
        role: true,
        status: true,
        isMinor: true,
      },
    });

    return this.ds.transaction(async (em) => {
      const registro = async (outcome: ResultadoDoTratamento) => {
        const r = await em
          .createQueryBuilder()
          .insert()
          .into(EventoProcessadoEntity)
          .values({
            eventId: e.eventId,
            eventType: e.type,
            stream: this.config.EVENTS_STREAM_ASSESSMENT,
            outcome,
          })
          .orIgnore()
          .returning(['event_id'])
          .execute();
        return (r.raw as unknown[]).length > 0;
      };
      if (!aluno || aluno.role !== 'student' || aluno.status !== 'active') {
        return (await registro('ignored')) ? 'ignored' : 'duplicate';
      }
      // Sem consentimento, sem coleta: não grava nada além do registro de que o evento foi descartado.
      if (
        !(await this.consentimento.permite(aluno.id, 'learning_assessment'))
      ) {
        return (await registro('skipped_no_consent'))
          ? 'skipped_no_consent'
          : 'duplicate';
      }
      const quando = new Date(e.occurredAt);
      if (aluno.isMinor) {
        // Evento anterior à concessão não pode ser projetado (revisão, achado 14).
        const c = await em.getRepository(ConsentimentoEntity).findOne({
          where: { studentUserId: aluno.id, purpose: 'learning_assessment' },
          select: { grantedAt: true },
        });
        if (!c?.grantedAt || quando < c.grantedAt) {
          return (await registro('skipped_no_consent'))
            ? 'skipped_no_consent'
            : 'duplicate';
        }
      }
      if (!(await registro('processed'))) return 'duplicate';
      if (e.type === 'EvidenciaGerada')
        await this.evidencia(
          em,
          e.eventId,
          aluno.schoolId,
          quando,
          DadosEvidenciaGerada.parse(e.data),
        );
      else if (e.type === 'CompetenciaAtualizada')
        await this.estimativa(
          em,
          e.eventId,
          aluno.schoolId,
          quando,
          DadosCompetenciaAtualizada.parse(e.data),
        );
      else
        await this.rubrica(
          em,
          aluno.schoolId,
          DadosRubricaAvaliada.parse(e.data),
        );
      return 'processed';
    });
  }

  private async competencia(
    em: EntityManager,
    codigo: string,
  ): Promise<string | null> {
    return (
      (
        await em
          .getRepository(CompetenciaEntity)
          .findOne({ where: { code: codigo }, select: { id: true } })
      )?.id ?? null
    );
  }

  private async evidencia(
    em: EntityManager,
    eventId: string,
    escola: string | null,
    quando: Date,
    d: ReturnType<typeof DadosEvidenciaGerada.parse>,
  ) {
    const competencyId = await this.competencia(em, d.competencyCode);
    const habilidade = d.bnccCode
      ? await em
          .getRepository(HabilidadeBnccEntity)
          .findOne({ where: { code: d.bnccCode }, select: { id: true } })
      : null;
    const planeta = d.planetId
      ? await em.getRepository(PlanetaMetaEntity).findOne({
          where: { id: d.planetId, ownerUserId: d.studentId },
          select: { id: true },
        })
      : null;
    await em.insert(EvidenciaEntity, {
      studentUserId: d.studentId,
      competencyId,
      type: d.type,
      payload: d.payload as Json,
      eventId,
      schoolId: escola,
      planetId: planeta?.id ?? null,
      bnccSkillId: habilidade?.id ?? null,
      source: d.synthetic ? 'synthetic' : 'ai-sim-service',
      synthetic: d.synthetic,
      occurredAt: quando,
    });
  }

  private async perfil(
    em: EntityManager,
    alunoId: string,
    escola: string | null,
  ): Promise<string> {
    await em
      .createQueryBuilder()
      .insert()
      .into(PerfilCognitivoEntity)
      .values({ studentUserId: alunoId, schoolId: escola })
      .orIgnore()
      .execute();
    return (
      await em
        .getRepository(PerfilCognitivoEntity)
        .findOneByOrFail({ studentUserId: alunoId })
    ).id;
  }

  private async estimativa(
    em: EntityManager,
    eventId: string,
    escola: string | null,
    quando: Date,
    d: ReturnType<typeof DadosCompetenciaAtualizada.parse>,
  ) {
    const competencyId = await this.competencia(em, d.competencyCode);
    if (!competencyId) return;
    const perfilId = await this.perfil(em, d.studentId, escola);
    const evidencias: { n: number }[] = await em.query(
      `SELECT count(*)::int AS n FROM platform.evidence WHERE student_user_id = $1 AND competency_id = $2`,
      [d.studentId, competencyId],
    );
    // Upsert que só avança: evento mais antigo que o já projetado não sobrescreve (ordem de chegada não importa).
    await em.query(
      `INSERT INTO platform.competency_estimate
         (cognitive_profile_id, competency_id, probability, uncertainty, evidence_count, last_event_id, last_event_at, synthetic, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
       ON CONFLICT (cognitive_profile_id, competency_id) DO UPDATE SET
         probability = EXCLUDED.probability, uncertainty = EXCLUDED.uncertainty, evidence_count = EXCLUDED.evidence_count,
         last_event_id = EXCLUDED.last_event_id, last_event_at = EXCLUDED.last_event_at, synthetic = EXCLUDED.synthetic, updated_at = now()
       WHERE platform.competency_estimate.last_event_at IS NULL OR platform.competency_estimate.last_event_at <= EXCLUDED.last_event_at`,
      [
        perfilId,
        competencyId,
        d.probability,
        d.uncertainty ?? null,
        evidencias[0].n,
        eventId,
        quando,
        d.synthetic,
      ],
    );
    await em.update(
      PerfilCognitivoEntity,
      { id: perfilId },
      { updatedAt: new Date() },
    );
  }

  private async rubrica(
    em: EntityManager,
    escola: string | null,
    d: ReturnType<typeof DadosRubricaAvaliada.parse>,
  ) {
    await em.insert(AvaliacaoEntity, {
      studentUserId: d.studentId,
      schoolId: escola,
      kind: 'rubric',
      score: d.score,
      missionId: d.missionId ?? null,
      competencyId: d.competencyCode
        ? await this.competencia(em, d.competencyCode)
        : null,
      details: d.details as Json,
    });
  }
}
