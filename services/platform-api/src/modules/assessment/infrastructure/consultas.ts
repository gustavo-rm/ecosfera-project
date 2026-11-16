import type { DataSource } from 'typeorm';

/** Consultas do modelo de leitura da avaliação. Todas recebem a escola e filtram por ela (RNF-013). */
export class ConsultasDeAvaliacao {
  constructor(private readonly ds: DataSource) {}

  async perfil(alunoId: string, escolaId: string) {
    return (await this.ds.query(
      `SELECT c.code, c.name, e.probability::float AS probability, e.uncertainty::float AS uncertainty,
              e.evidence_count AS "evidenceCount", e.updated_at AS "updatedAt", e.synthetic, e.last_event_id AS "lastEventId"
       FROM platform.cognitive_profile p
       JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id
       JOIN platform.competency c ON c.id = e.competency_id
       WHERE p.student_user_id = $1 AND p.school_id = $2
       ORDER BY c.code`,
      [alunoId, escolaId],
    )) as { code: string; name: string; probability: number; uncertainty: number | null; evidenceCount: number; updatedAt: Date; synthetic: boolean; lastEventId: string | null }[];
  }

  async evidencias(alunoId: string, escolaId: string, competencia: string | undefined, pagina: number, tamanho: number) {
    const params: unknown[] = [alunoId, escolaId];
    let filtro = '';
    if (competencia) {
      params.push(competencia);
      filtro = `AND c.code = $${params.length}`;
    }
    const total: { n: number }[] = await this.ds.query(
      `SELECT count(*)::int AS n FROM platform.evidence ev LEFT JOIN platform.competency c ON c.id = ev.competency_id
       WHERE ev.student_user_id = $1 AND ev.school_id = $2 ${filtro}`,
      params,
    );
    params.push(tamanho, (pagina - 1) * tamanho);
    const itens = (await this.ds.query(
      `SELECT ev.id, ev.event_id AS "eventId", c.code AS "competencyCode", s.code AS "bnccCode", ev.type, ev.payload,
              ev.planet_id AS "planetId", ev.occurred_at AS "occurredAt", ev.synthetic, ev.source
       FROM platform.evidence ev
       LEFT JOIN platform.competency c ON c.id = ev.competency_id
       LEFT JOIN platform.bncc_skill s ON s.id = ev.bncc_skill_id
       WHERE ev.student_user_id = $1 AND ev.school_id = $2 ${filtro}
       ORDER BY ev.occurred_at DESC, ev.id
       LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params,
    )) as Record<string, unknown>[];
    return { itens, total: total[0]!.n };
  }

  /** Domínio mapeado à BNCC (RF-076): habilidade → competência → estimativa do aluno. */
  async mapaBncc(alunoId: string, escolaId: string) {
    return (await this.ds.query(
      `SELECT s.code, s.theme, s.component, s.validation_status AS "validationStatus", c.code AS "competencyCode",
              e.probability::float AS mastery, e.uncertainty::float AS uncertainty, COALESCE(e.evidence_count, 0) AS "evidenceCount"
       FROM platform.bncc_skill s
       JOIN platform.competency c ON c.id = s.competency_id
       LEFT JOIN platform.cognitive_profile p ON p.student_user_id = $1 AND p.school_id = $2
       LEFT JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id AND e.competency_id = c.id
       WHERE s.active = true
       ORDER BY s.code`,
      [alunoId, escolaId],
    )) as { code: string; theme: string | null; component: string | null; validationStatus: string; competencyCode: string; mastery: number | null; uncertainty: number | null; evidenceCount: number }[];
  }

  async alunosDaTurma(turmaId: string, escolaId: string) {
    return (await this.ds.query(
      `SELECT u.id, u.name, u.is_minor AS "isMinor",
         (SELECT count(*)::int FROM platform.planet_meta pm WHERE pm.owner_user_id = u.id) AS planets,
         (SELECT count(*)::int FROM platform.evidence ev WHERE ev.student_user_id = u.id) AS "evidenceCount",
         (SELECT max(ev.occurred_at) FROM platform.evidence ev WHERE ev.student_user_id = u.id) AS "lastActivity"
       FROM platform.enrollment en
       JOIN platform.class cl ON cl.id = en.class_id
       JOIN platform.app_user u ON u.id = en.student_user_id
       WHERE en.class_id = $1 AND cl.school_id = $2 AND u.status = 'active'
       ORDER BY u.name, u.id`,
      [turmaId, escolaId],
    )) as { id: string; name: string; isMinor: boolean; planets: number; evidenceCount: number; lastActivity: Date | null }[];
  }

  async estimativasDosAlunos(alunosIds: string[], escolaId: string) {
    if (alunosIds.length === 0) return [];
    return (await this.ds.query(
      `SELECT p.student_user_id AS "alunoId", c.code AS competencia, e.probability::float AS probabilidade,
              e.uncertainty::float AS incerteza, e.evidence_count AS evidencias, e.synthetic AS sintetico
       FROM platform.cognitive_profile p
       JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id
       JOIN platform.competency c ON c.id = e.competency_id
       WHERE p.student_user_id = ANY($1::uuid[]) AND p.school_id = $2`,
      [alunosIds, escolaId],
    )) as { alunoId: string; competencia: string; probabilidade: number; incerteza: number | null; evidencias: number; sintetico: boolean }[];
  }

  /** Agregado por turma e competência na escola (US-09, coordenação). */
  async agregadoDaEscola(escolaId: string, alunosPermitidos: string[]) {
    if (alunosPermitidos.length === 0) return [];
    return (await this.ds.query(
      `SELECT cl.id AS "classId", cl.name AS "className", c.code AS "competencyCode",
              count(DISTINCT p.student_user_id)::int AS students, avg(e.probability)::float AS "avgMastery"
       FROM platform.class cl
       JOIN platform.enrollment en ON en.class_id = cl.id
       JOIN platform.cognitive_profile p ON p.student_user_id = en.student_user_id AND p.school_id = cl.school_id
       JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id
       JOIN platform.competency c ON c.id = e.competency_id
       WHERE cl.school_id = $1 AND en.student_user_id = ANY($2::uuid[])
       GROUP BY cl.id, cl.name, c.code
       ORDER BY cl.name, c.code`,
      [escolaId, alunosPermitidos],
    )) as { classId: string; className: string; competencyCode: string; students: number; avgMastery: number }[];
  }

  async alunosDaEscola(escolaId: string) {
    return (await this.ds.query(`SELECT id FROM platform.app_user WHERE school_id = $1 AND role = 'student' AND status = 'active'`, [escolaId])) as { id: string }[];
  }

  /** Linhas para o dataset de pesquisa: só alunos com consentimento `research` CONCEDIDO explicitamente. */
  async linhasDePesquisa(escolaId: string | null) {
    return (await this.ds.query(
      `SELECT p.student_user_id AS "alunoId", p.school_id AS "escolaId",
              (SELECT t.level FROM platform.enrollment en JOIN platform.class cl ON cl.id = en.class_id
                 LEFT JOIN platform.track t ON t.id = cl.track_id
               WHERE en.student_user_id = p.student_user_id ORDER BY en.created_at LIMIT 1) AS nivel,
              c.code AS competencia, e.probability::float AS probabilidade, e.uncertainty::float AS incerteza,
              e.evidence_count AS evidencias, e.updated_at AS "atualizadoEm", e.synthetic AS sintetico
       FROM platform.cognitive_profile p
       JOIN platform.competency_estimate e ON e.cognitive_profile_id = p.id
       JOIN platform.competency c ON c.id = e.competency_id
       JOIN platform.consent cs ON cs.student_user_id = p.student_user_id AND cs.purpose = 'research' AND cs.status = 'granted'
       JOIN platform.consent ca ON ca.student_user_id = p.student_user_id AND ca.purpose = 'learning_assessment' AND ca.status = 'granted'
       WHERE ($1::uuid IS NULL OR p.school_id = $1)`,
      [escolaId],
    )) as { alunoId: string; escolaId: string; nivel: string | null; competencia: string; probabilidade: number; incerteza: number | null; evidencias: number; atualizadoEm: Date; sintetico: boolean }[];
  }
}
