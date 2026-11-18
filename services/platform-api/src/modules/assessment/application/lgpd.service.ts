import {
  Inject,
  Injectable,
  type OnApplicationBootstrap,
  type OnApplicationShutdown,
} from '@nestjs/common';
import type { Logger } from 'pino';
import { DataSource, In, IsNull, LessThan } from 'typeorm';

import {
  OBJECT_STORAGE,
  type ObjectStorage,
} from '../../../shared/armazenamento/portas';
import { Auditoria } from '../../../shared/auditoria/auditoria';
import { carregarFatosDoAlvo } from '../../../shared/autorizacao/fatos';
import {
  CONFIGURACAO,
  type Configuracao,
} from '../../../shared/config/configuracao';
import { registrarNoOutbox } from '../../../shared/eventos/eventos';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import {
  ErroAcessoNegado,
  ErroNaoEncontrado,
} from '../../../shared/kernel/erros';
import { RELOGIO, type Relogio } from '../../../shared/kernel/relogio';
import {
  VINCULOS_ESCOLARES,
  type VinculosEscolares,
} from '../../../shared/kernel/vinculos';
import { LOGGER } from '../../../shared/observabilidade/logger';
import { Cifrador } from '../../../shared/seguranca/cifrador';
import { Pseudonimizador } from '../../../shared/seguranca/pseudonimizador';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import {
  ARMAZEM_DE_SESSOES,
  type ArmazemDeSessoes,
} from '../../identity/domain/portas';
import {
  PedidoDeTitularEntity,
  PoliticaDeRetencaoEntity,
} from '../../identity/infrastructure/persistencia/lgpd.entity';
import { UsuarioEntity } from '../../identity/infrastructure/persistencia/usuario.entity';
import { VinculoResponsavelEntity } from '../../identity/infrastructure/persistencia/vinculo-responsavel.entity';
import { MatriculaEntity } from '../../education/infrastructure/persistencia/turma.entity';
import { PlanetaMetaEntity } from '../../orchestration/infrastructure/persistencia/planeta.entity';
import {
  AvaliacaoEntity,
  EvidenciaEntity,
  FeedbackEntity,
  PerfilCognitivoEntity,
  RegistroDeExportacaoEntity,
} from '../infrastructure/persistencia/avaliacao.entity';

/** Direitos do titular (RNF-012) e retenção parametrizável. */
@Injectable()
export class ServicoLgpd
  implements OnApplicationBootstrap, OnApplicationShutdown
{
  private timer?: NodeJS.Timeout;

  constructor(
    private readonly ds: DataSource,
    private readonly consentimento: ServicoDeConsentimento,
    private readonly auditoria: Auditoria,
    private readonly cifrador: Cifrador,
    private readonly pseudo: Pseudonimizador,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    @Inject(ARMAZEM_DE_SESSOES) private readonly sessoes: ArmazemDeSessoes,
    @Inject(OBJECT_STORAGE) private readonly storage: ObjectStorage,
    @Inject(RELOGIO) private readonly relogio: Relogio,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(LOGGER) private readonly logger: Logger,
  ) {}

  onApplicationBootstrap(): void {
    if (!this.config.RETENTION_JOB_ENABLED) return;
    this.timer = setInterval(
      () =>
        void this.executarRetencao().catch((e: Error) =>
          this.logger.error({ err: e.message }, 'falha na retenção'),
        ),
      6 * 3600 * 1000,
    );
    this.timer.unref();
  }
  onApplicationShutdown(): void {
    if (this.timer) clearInterval(this.timer);
  }

  /** Quem pode exercer o direito em nome do titular: o responsável vinculado ou o admin da escola. */
  private async exigirRepresentante(
    ator: AtorUsuario,
    alvoId: string,
  ): Promise<string | null> {
    const f = await carregarFatosDoAlvo(this.vinculos, ator, alvoId);
    if (!f.existe) throw new ErroNaoEncontrado('Usuário');
    const mesmaEscola = ator.escolaId !== null && ator.escolaId === f.escolaId;
    const ok =
      (ator.papel === 'guardian' && f.responsavelPeloAlvo) ||
      (ator.papel === 'admin' && mesmaEscola) ||
      (ator.usuarioId === alvoId && ator.papel !== 'student');
    if (!ok)
      throw f.escolaId === ator.escolaId || f.responsavelPeloAlvo
        ? new ErroAcessoNegado()
        : new ErroNaoEncontrado('Usuário');
    return f.escolaId;
  }

  /** Acesso: todos os dados pessoais do titular em JSON. */
  async acesso(ator: AtorUsuario, alvoId: string) {
    const escola = await this.exigirRepresentante(ator, alvoId);
    const u = await this.ds
      .getRepository(UsuarioEntity)
      .findOneByOrFail({ id: alvoId });
    const [
      consentimentos,
      matriculas,
      planetas,
      evidencias,
      feedbacks,
      avaliacoes,
    ] = await Promise.all([
      this.consentimento.situacaoSemChecagem(alvoId).catch(() => null),
      this.ds.getRepository(MatriculaEntity).findBy({ studentUserId: alvoId }),
      this.ds.getRepository(PlanetaMetaEntity).findBy({ ownerUserId: alvoId }),
      this.ds
        .getRepository(EvidenciaEntity)
        .find({ where: { studentUserId: alvoId }, take: 5000 }),
      this.ds.getRepository(FeedbackEntity).findBy({ studentUserId: alvoId }),
      this.ds.getRepository(AvaliacaoEntity).findBy({ studentUserId: alvoId }),
    ]);
    const estimativas: unknown[] = await this.ds.query(
      `SELECT c.code, e.probability::float, e.uncertainty::float, e.updated_at FROM platform.cognitive_profile p
       JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id JOIN platform.competency c ON c.id = e.competency_id
       WHERE p.student_user_id = $1`,
      [alvoId],
    );
    const pedido = await this.registrarPedido(
      ator,
      alvoId,
      escola,
      'access',
      {},
    );
    return {
      requestId: pedido,
      generatedAt: this.relogio.agora().toISOString(),
      subject: {
        id: u.id,
        name: u.name,
        email: u.email,
        role: u.role,
        schoolId: u.schoolId,
        isMinor: u.isMinor,
        preferences: u.preferences,
        createdAt: u.createdAt,
      },
      consents: consentimentos?.purposes ?? [],
      enrollments: matriculas.map((m) => ({
        classId: m.classId,
        since: m.createdAt,
      })),
      planets: planetas.map((p) => ({
        id: p.id,
        missionId: p.missionId,
        era: p.currentEra,
        createdAt: p.createdAt,
      })),
      evidence: evidencias.map((e) => ({
        id: e.id,
        type: e.type,
        payload: e.payload,
        occurredAt: e.occurredAt,
      })),
      competencyEstimates: estimativas,
      feedback: feedbacks.map((f) => ({
        id: f.id,
        content: this.cifrador.decifrar(f.content),
        createdAt: f.createdAt,
      })),
      assessments: avaliacoes.map((a) => ({
        id: a.id,
        kind: a.kind,
        score: a.score,
        createdAt: a.createdAt,
      })),
      note: 'O estado detalhado dos planetas e a telemetria bruta ficam no serviço de simulação e IA; o pedido foi encaminhado por evento.',
    };
  }

  /**
   * Exclusão: apaga dados pedagógicos e pseudonimiza a conta. O registro do usuário fica (sem PII)
   * para manter a integridade do audit_log, que é imutável.
   */
  async exclusao(ator: AtorUsuario, alvoId: string) {
    const escola = await this.exigirRepresentante(ator, alvoId);
    const pseudonimo = this.pseudo.estavel(alvoId, 'exclusao');
    const contagem = await this.ds.transaction(async (em) => {
      const ev = await em.delete(EvidenciaEntity, { studentUserId: alvoId });
      const pf = await em.delete(PerfilCognitivoEntity, {
        studentUserId: alvoId,
      });
      const fb = await em.delete(FeedbackEntity, { studentUserId: alvoId });
      const av = await em.delete(AvaliacaoEntity, { studentUserId: alvoId });
      const planetas = await em
        .getRepository(PlanetaMetaEntity)
        .findBy({ ownerUserId: alvoId });
      await em.update(
        PlanetaMetaEntity,
        { ownerUserId: alvoId },
        { status: 'archived' },
      );
      await em.delete(MatriculaEntity, { studentUserId: alvoId });
      await em.delete(VinculoResponsavelEntity, { studentUserId: alvoId });
      await em.update(
        UsuarioEntity,
        { id: alvoId },
        {
          name: '[removido]',
          email: `removido+${pseudonimo}@invalid.ecosfera`,
          passwordHash: '!',
          status: 'pseudonymized',
          preferences: {},
          pseudonymizedAt: this.relogio.agora(),
        },
      );
      await registrarNoOutbox(em, 'TitularExcluido', alvoId, {
        subjectId: alvoId,
        planetIds: planetas.map((p) => p.id),
      });
      return {
        evidence: ev.affected ?? 0,
        profiles: pf.affected ?? 0,
        feedback: fb.affected ?? 0,
        assessments: av.affected ?? 0,
        planetsArchived: planetas.length,
      };
    });
    await this.sessoes.revogarTodasDoUsuario(alvoId);
    await this.consentimento.invalidarCache(alvoId);
    const pedido = await this.registrarPedido(
      ator,
      alvoId,
      escola,
      'deletion',
      contagem,
    );
    await this.auditoria.registrar({
      acao: 'data_subject.deletion',
      entidade: 'user',
      entidadeId: alvoId,
      escolaId: escola,
      dados: contagem,
    });
    return { requestId: pedido, status: 'completed', removed: contagem };
  }

  private async registrarPedido(
    ator: AtorUsuario,
    alvoId: string,
    escola: string | null,
    kind: 'access' | 'deletion',
    details: Record<string, unknown>,
  ) {
    const r = await this.ds.getRepository(PedidoDeTitularEntity).save({
      schoolId: escola,
      subjectUserId: alvoId,
      requestedByUserId: ator.usuarioId,
      kind,
      status: 'completed',
      details,
      completedAt: this.relogio.agora(),
    });
    await this.auditoria.registrar({
      acao: `data_subject.${kind}`,
      entidade: 'data_subject_request',
      entidadeId: r.id,
      escolaId: escola,
      dados: { subjectId: alvoId },
    });
    return r.id;
  }

  async politicas() {
    return this.ds
      .getRepository(PoliticaDeRetencaoEntity)
      .find({ order: { dataCategory: 'ASC' } });
  }

  async definirPolitica(ator: AtorUsuario, categoria: string, dias: number) {
    if (ator.papel !== 'platform_admin') throw new ErroAcessoNegado();
    const r = await this.ds
      .getRepository(PoliticaDeRetencaoEntity)
      .update(
        { dataCategory: categoria },
        { retentionDays: dias, updatedAt: new Date() },
      );
    if ((r.affected ?? 0) === 0)
      throw new ErroNaoEncontrado('Categoria de retenção');
    await this.auditoria.registrar({
      acao: 'retention.policy_changed',
      entidade: 'retention_policy',
      entidadeId: categoria,
      escolaId: null,
      dados: { retentionDays: dias },
    });
    return (await this.politicas()).find((p) => p.dataCategory === categoria)!;
  }

  /** Expurgo conforme retention_policy. Idempotente; seguro para rodar várias vezes. */
  async executarRetencao(): Promise<Record<string, number>> {
    const agora = this.relogio.agora().getTime();
    const p = new Map(
      (await this.politicas()).map((x) => [x.dataCategory, x.retentionDays]),
    );
    const antes = (cat: string) =>
      new Date(agora - (p.get(cat) ?? 36500) * 86_400_000);
    const r: Record<string, number> = {};
    r.evidence =
      (
        await this.ds
          .getRepository(EvidenciaEntity)
          .delete({ occurredAt: LessThan(antes('evidence')) })
      ).affected ?? 0;
    r.feedback =
      (
        await this.ds
          .getRepository(FeedbackEntity)
          .delete({ createdAt: LessThan(antes('feedback')) })
      ).affected ?? 0;
    r.competency_estimate = Number(
      (
        await this.ds.query<[unknown, number]>(
          `DELETE FROM platform.competency_estimate WHERE updated_at < $1`,
          [antes('competency_estimate')],
        )
      )[1] ?? 0,
    );
    // Após revogação do consentimento de avaliação: o que foi projetado sai no prazo da política.
    const revogados: { student_user_id: string }[] = await this.ds.query(
      `SELECT student_user_id FROM platform.consent WHERE purpose = 'learning_assessment' AND status = 'revoked' AND revoked_at < $1`,
      [antes('assessment_after_consent_revocation')],
    );
    const ids = revogados.map((x) => x.student_user_id);
    r.assessment_after_consent_revocation = 0;
    if (ids.length > 0) {
      r.assessment_after_consent_revocation +=
        (
          await this.ds
            .getRepository(EvidenciaEntity)
            .delete({ studentUserId: In(ids) })
        ).affected ?? 0;
      r.assessment_after_consent_revocation +=
        (
          await this.ds
            .getRepository(PerfilCognitivoEntity)
            .delete({ studentUserId: In(ids) })
        ).affected ?? 0;
    }
    r.export_objects = 0;
    for (const [cat, tipo] of [
      ['export_objects', 'report'],
      ['research_dataset_objects', 'dataset'],
    ] as const) {
      const velhos = await this.ds
        .getRepository(RegistroDeExportacaoEntity)
        .findBy({
          kind: tipo,
          purgedAt: IsNull(),
          createdAt: LessThan(antes(cat)),
        });
      for (const v of velhos) {
        await this.storage.remover(v.bucket, v.objectKey);
        await this.ds
          .getRepository(RegistroDeExportacaoEntity)
          .update({ id: v.id }, { purgedAt: new Date() });
      }
      r[cat] = velhos.length;
    }
    await this.auditoria.registrar({
      acao: 'retention.executed',
      entidade: 'retention_policy',
      escolaId: null,
      dados: r,
    });
    return r;
  }
}
