import { Inject, Injectable } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroAcessoNegado, ErroConsentimentoAusente, ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { decidirAcessoAoUsuario } from '../../../shared/kernel/politica-de-acesso';
import { RELOGIO, type Relogio } from '../../../shared/kernel/relogio';
import { VINCULOS_ESCOLARES, type VinculosEscolares } from '../../../shared/kernel/vinculos';
import { carregarFatosDoAlvo } from '../../../shared/autorizacao/fatos';
import { Cifrador } from '../../../shared/seguranca/cifrador';
import { ServicoDeEducacao } from '../../education/application/educacao.service';
import { CompetenciaEntity } from '../../education/infrastructure/persistencia/curriculo.entity';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import { calcularAlertas, CONFIGURACAO_PADRAO, type ConfiguracaoDeAlerta } from '../domain/alertas';
import { ConsultasDeAvaliacao } from '../infrastructure/consultas';
import { AvaliacaoEntity, ConfiguracaoDeAlertaEntity, FeedbackEntity } from '../infrastructure/persistencia/avaliacao.entity';

/**
 * Lado de leitura da avaliação e painel do professor/coordenação.
 * RP-004: o aluno NÃO vê pontuação. RP-007: tudo aqui é informação para o professor decidir.
 */
@Injectable()
export class ServicoDePainel {
  constructor(
    private readonly ds: DataSource,
    private readonly consultas: ConsultasDeAvaliacao,
    private readonly educacao: ServicoDeEducacao,
    private readonly consentimento: ServicoDeConsentimento,
    private readonly auditoria: Auditoria,
    private readonly cifrador: Cifrador,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    @Inject(RELOGIO) private readonly relogio: Relogio,
  ) {}

  /** Defesa em profundidade + consentimento do titular + auditoria do acesso a dado de menor. */
  private async exigirAluno(ator: AtorUsuario, alunoId: string, escopo: string): Promise<string> {
    const fatos = await carregarFatosDoAlvo(this.vinculos, ator, alunoId);
    const d = decidirAcessoAoUsuario(ator, fatos, 'ler-pedagogico');
    if (d === 'inexistente') throw new ErroNaoEncontrado('Aluno');
    if (d === 'negado') throw new ErroAcessoNegado();
    if (!(await this.consentimento.permite(alunoId, 'learning_assessment'))) throw new ErroConsentimentoAusente('learning_assessment');
    await this.auditoria.registrar({ acao: 'minor_data.accessed', entidade: 'user', entidadeId: alunoId, escolaId: fatos.escolaId, dados: { scope: escopo } });
    return fatos.escolaId!;
  }

  async perfil(ator: AtorUsuario, alunoId: string) {
    const escola = await this.exigirAluno(ator, alunoId, 'assessment.profile');
    const linhas = await this.consultas.perfil(alunoId, escola);
    return {
      studentId: alunoId,
      competencies: linhas.map((l) => ({
        ...l,
        evidenceRef: `/platform/api/v1/assessment/students/${alunoId}/evidence?competency=${l.code}`,
      })),
      disclaimer: 'Estimativas calculadas pelo serviço de avaliação. Apoiam, não substituem, o julgamento do professor.',
    };
  }

  async evidencias(ator: AtorUsuario, alunoId: string, competencia: string | undefined, pagina: number, tamanho: number) {
    const escola = await this.exigirAluno(ator, alunoId, 'assessment.evidence');
    const r = await this.consultas.evidencias(alunoId, escola, competencia, pagina, tamanho);
    return { items: r.itens, page: pagina, pageSize: tamanho, total: r.total };
  }

  async bncc(ator: AtorUsuario, alunoId: string) {
    const escola = await this.exigirAluno(ator, alunoId, 'assessment.bncc');
    return { studentId: alunoId, skills: await this.consultas.mapaBncc(alunoId, escola) };
  }

  private async alunosComConsentimento(alunos: { id: string }[]) {
    const permitidos: string[] = [];
    for (const a of alunos) if (await this.consentimento.permite(a.id, 'learning_assessment')) permitidos.push(a.id);
    return permitidos;
  }

  async visaoDaTurma(ator: AtorUsuario, turmaId: string) {
    const turma = await this.educacao.exigirTurma(ator, turmaId, 'gerir');
    const alunos = await this.consultas.alunosDaTurma(turmaId, turma.escolaId);
    const situacoes = await Promise.all(alunos.map((a) => this.consentimento.situacaoSemChecagem(a.id)));
    const comAvaliacao = new Set(await this.alunosComConsentimento(alunos));
    return {
      classId: turmaId,
      students: alunos.map((a, i) => {
        const pend = situacoes[i]!.purposes.filter((p) => p.status === 'pending' || p.status === 'revoked').map((p) => p.purpose);
        const permitido = comAvaliacao.has(a.id);
        return {
          id: a.id,
          name: a.name,
          consentPending: pend,
          planets: a.planets,
          // Sem consentimento de avaliação, o painel não mostra dados pedagógicos do aluno.
          evidenceCount: permitido ? a.evidenceCount : null,
          lastActivity: permitido ? a.lastActivity : null,
        };
      }),
      totals: {
        students: alunos.length,
        consentPending: situacoes.filter((s) => s.purposes.some((p) => p.purpose === 'platform_use' && (p.status === 'pending' || p.status === 'revoked'))).length,
        withAssessmentConsent: comAvaliacao.size,
      },
    };
  }

  async competenciasDaTurma(ator: AtorUsuario, turmaId: string) {
    const turma = await this.educacao.exigirTurma(ator, turmaId, 'gerir');
    const alunos = await this.consultas.alunosDaTurma(turmaId, turma.escolaId);
    const permitidos = await this.alunosComConsentimento(alunos);
    const est = await this.consultas.estimativasDosAlunos(permitidos, turma.escolaId);
    const porCompetencia = new Map<string, number[]>();
    for (const e of est) (porCompetencia.get(e.competencia) ?? porCompetencia.set(e.competencia, []).get(e.competencia)!).push(e.probabilidade);
    const competencias = await this.ds.getRepository(CompetenciaEntity).find({ order: { code: 'ASC' } });
    return {
      classId: turmaId,
      studentsIncluded: permitidos.length,
      studentsExcludedForConsent: alunos.length - permitidos.length,
      competencies: competencias
        .filter((c) => c.code)
        .map((c) => {
          const v = porCompetencia.get(c.code!) ?? [];
          return {
            code: c.code!,
            name: c.name,
            students: v.length,
            avgMastery: v.length ? Math.round((v.reduce((a, b) => a + b, 0) / v.length) * 10000) / 10000 : null,
            distribution: { low: v.filter((x) => x < 0.4).length, medium: v.filter((x) => x >= 0.4 && x < 0.7).length, high: v.filter((x) => x >= 0.7).length },
          };
        }),
      synthetic: est.some((e) => e.sintetico),
    };
  }

  async configuracaoDeAlerta(escolaId: string): Promise<ConfiguracaoDeAlerta> {
    const c = await this.ds.getRepository(ConfiguracaoDeAlertaEntity).findOneBy({ schoolId: escolaId });
    if (!c) return CONFIGURACAO_PADRAO;
    return { limiarDeDominio: c.masteryThreshold, incertezaMaxima: c.maxUncertainty, minimoDeEvidencias: c.minEvidence, diasDeInatividade: c.inactivityDays, situacaoDaRevisao: c.reviewStatus };
  }

  async definirConfiguracaoDeAlerta(ator: AtorUsuario, escolaId: string, c: Omit<ConfiguracaoDeAlerta, 'situacaoDaRevisao'>) {
    if (ator.escolaId !== escolaId || !['coordinator', 'admin'].includes(ator.papel)) throw new ErroNaoEncontrado('Escola');
    await this.ds
      .getRepository(ConfiguracaoDeAlertaEntity)
      .upsert({ schoolId: escolaId, masteryThreshold: c.limiarDeDominio, maxUncertainty: c.incertezaMaxima, minEvidence: c.minimoDeEvidencias, inactivityDays: c.diasDeInatividade, updatedAt: new Date() }, ['schoolId']);
    await this.auditoria.registrar({ acao: 'alert_config.updated', entidade: 'school', entidadeId: escolaId, escolaId, dados: { ...c } });
    return this.configuracaoDeAlerta(escolaId);
  }

  async alertas(ator: AtorUsuario, turmaId: string) {
    const turma = await this.educacao.exigirTurma(ator, turmaId, 'gerir');
    const alunos = await this.consultas.alunosDaTurma(turmaId, turma.escolaId);
    const permitidos = new Set(await this.alunosComConsentimento(alunos));
    const est = await this.consultas.estimativasDosAlunos([...permitidos], turma.escolaId);
    const config = await this.configuracaoDeAlerta(turma.escolaId);
    const atividade = new Map(alunos.filter((a) => permitidos.has(a.id)).map((a) => [a.id, a.lastActivity ? new Date(a.lastActivity) : null]));
    const alertas = calcularAlertas(est, atividade, config, this.relogio.agora());
    return {
      classId: turmaId,
      thresholds: { ...config, reviewStatus: config.situacaoDaRevisao },
      alerts: alertas.map((a) => ({
        ...a,
        evidenceRef: a.competencyCode ? `/platform/api/v1/assessment/students/${a.studentId}/evidence?competency=${a.competencyCode}` : null,
      })),
      notice: 'Alertas são indícios para o professor avaliar; nenhuma ação automática é tomada.',
    };
  }

  /** RF-068: professor vê o status de consentimento da turma. */
  async consentimentosDaTurma(ator: AtorUsuario, turmaId: string) {
    const turma = await this.educacao.exigirTurma(ator, turmaId, 'gerir');
    const alunos = await this.consultas.alunosDaTurma(turmaId, turma.escolaId);
    const s = await Promise.all(alunos.map((a) => this.consentimento.situacaoSemChecagem(a.id)));
    return { classId: turmaId, students: alunos.map((a, i) => ({ id: a.id, name: a.name, isMinor: a.isMinor, purposes: s[i]!.purposes.map((p) => ({ purpose: p.purpose, status: p.status })) })) };
  }

  /** US-09: coordenação vê agregados por competência entre turmas. */
  async agregadoDaEscola(ator: AtorUsuario, escolaId: string) {
    if (ator.escolaId !== escolaId) throw new ErroNaoEncontrado('Escola');
    const permitidos = await this.alunosComConsentimento(await this.consultas.alunosDaEscola(escolaId));
    return { schoolId: escolaId, rows: await this.consultas.agregadoDaEscola(escolaId, permitidos) };
  }

  // ── Feedback ao aluno (RF-067) ──────────────────────────────────────────
  async enviarFeedback(ator: AtorUsuario, alunoId: string, conteudo: string, avaliacaoId?: string) {
    const fatos = await carregarFatosDoAlvo(this.vinculos, ator, alunoId);
    const d = decidirAcessoAoUsuario(ator, fatos, 'ler-pedagogico');
    if (d === 'inexistente') throw new ErroNaoEncontrado('Aluno');
    if (d === 'negado' || ator.papel !== 'teacher') throw new ErroAcessoNegado('Só o professor do aluno envia feedback');
    if (!(await this.consentimento.permite(alunoId, 'platform_use'))) throw new ErroConsentimentoAusente('platform_use');
    const r = await this.ds.getRepository(FeedbackEntity).save({
      studentUserId: alunoId,
      authorUserId: ator.usuarioId,
      schoolId: fatos.escolaId,
      assessmentId: avaliacaoId ?? null,
      content: this.cifrador.cifrar(conteudo),
    });
    await this.auditoria.registrar({ acao: 'feedback.sent', entidade: 'feedback', entidadeId: r.id, escolaId: fatos.escolaId, dados: { studentId: alunoId } });
    return { id: r.id, studentId: alunoId, createdAt: r.createdAt };
  }

  async meusFeedbacks(ator: AtorUsuario) {
    if (ator.papel !== 'student') throw new ErroAcessoNegado();
    const fs = await this.ds.getRepository(FeedbackEntity).find({ where: { studentUserId: ator.usuarioId }, order: { createdAt: 'DESC' }, take: 100 });
    return {
      items: fs.map((f) => ({ id: f.id, content: this.cifrador.decifrar(f.content), authorUserId: f.authorUserId, createdAt: f.createdAt, readAt: f.readAt })),
    };
  }

  async marcarLido(ator: AtorUsuario, id: string) {
    const r = await this.ds.getRepository(FeedbackEntity).update({ id, studentUserId: ator.usuarioId }, { readAt: this.relogio.agora() });
    if ((r.affected ?? 0) === 0) throw new ErroNaoEncontrado('Feedback');
  }

  // ── Pré/pós-teste (RF-074) e rubricas (RF-075) ──────────────────────────
  async registrarAvaliacao(ator: AtorUsuario, alunoId: string, d: { kind: 'pre_test' | 'post_test' | 'rubric'; score: number; competencyCode?: string; missionId?: string; details?: Record<string, unknown> }) {
    const escola = await this.exigirAluno(ator, alunoId, 'assessment.record');
    if (ator.papel !== 'teacher') throw new ErroAcessoNegado();
    const competencia = d.competencyCode ? await this.ds.getRepository(CompetenciaEntity).findOneBy({ code: d.competencyCode }) : null;
    if (d.competencyCode && !competencia) throw new ErroNaoEncontrado('Competência');
    if (d.missionId) await this.educacao.exigirMissao(ator, d.missionId, 'ler');
    const r = await this.ds.getRepository(AvaliacaoEntity).save({
      studentUserId: alunoId,
      schoolId: escola,
      kind: d.kind,
      score: d.score,
      competencyId: competencia?.id ?? null,
      missionId: d.missionId ?? null,
      recordedByUserId: ator.usuarioId,
      details: d.details ?? {},
    });
    return this.paraAvaliacao(r, d.competencyCode ?? null);
  }

  async avaliacoes(ator: AtorUsuario, alunoId: string) {
    const escola = await this.exigirAluno(ator, alunoId, 'assessment.list');
    const rs: (AvaliacaoEntity & { code: string | null })[] = await this.ds.query(
      `SELECT a.*, c.code FROM platform.assessment a LEFT JOIN platform.competency c ON c.id = a.competency_id
       WHERE a.student_user_id = $1 AND a.school_id = $2 ORDER BY a.created_at`,
      [alunoId, escola],
    );
    return {
      items: rs.map((r) => ({
        id: r.id,
        kind: (r as unknown as { kind: string }).kind,
        score: r.score === null ? null : Number(r.score),
        competencyCode: r.code,
        missionId: (r as unknown as { mission_id: string | null }).mission_id,
        createdAt: (r as unknown as { created_at: Date }).created_at,
      })),
    };
  }

  private paraAvaliacao(r: AvaliacaoEntity, competencyCode: string | null) {
    return { id: r.id, kind: r.kind, score: r.score, competencyCode, missionId: r.missionId, createdAt: r.createdAt };
  }
}
