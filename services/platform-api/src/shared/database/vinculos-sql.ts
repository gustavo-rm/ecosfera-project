import type { DataSource } from 'typeorm';

import type { VinculosEscolares } from '../kernel/vinculos';

/**
 * Consultas de leitura sobre vínculos (turma, matrícula, responsável), usadas pelas
 * regras de posse de vários contextos. Só SELECT, sempre por chave (índices dedicados).
 */
export class VinculosEscolaresSql implements VinculosEscolares {
  constructor(private readonly ds: DataSource) {}

  async professorLecionaParaAluno(
    professorId: string,
    alunoId: string,
  ): Promise<boolean> {
    const r: unknown[] = await this.ds.query(
      `SELECT 1 FROM platform.enrollment e JOIN platform.class c ON c.id = e.class_id
       WHERE e.student_user_id = $1 AND c.teacher_user_id = $2 LIMIT 1`,
      [alunoId, professorId],
    );
    return r.length > 0;
  }

  async responsavelPeloAluno(
    responsavelId: string,
    alunoId: string,
  ): Promise<boolean> {
    const r: unknown[] = await this.ds.query(
      `SELECT 1 FROM platform.guardian WHERE guardian_user_id = $1 AND student_user_id = $2 LIMIT 1`,
      [responsavelId, alunoId],
    );
    return r.length > 0;
  }

  async escolaDoUsuario(usuarioId: string) {
    const r: { school_id: string | null; role: string }[] = await this.ds.query(
      `SELECT school_id, role FROM platform.app_user WHERE id = $1 AND status <> 'pseudonymized'`,
      [usuarioId],
    );
    const l = r[0];
    return l
      ? { existe: true, escolaId: l.school_id, papel: l.role }
      : { existe: false, escolaId: null, papel: null };
  }
}
