import { type DataSource, In } from 'typeorm';

import { ErroNaoEncontrado } from '../../../shared/kernel/erros';
import type {
  FatosDaMissao,
  FatosDaTurma,
  Missao,
  Nivel,
  Turma,
} from '../domain/educacao';
import type {
  CompetenciaDoCatalogo,
  HabilidadeDoCatalogo,
  RepositorioDeEducacao,
} from '../domain/portas';
import {
  CompetenciaEntity,
  HabilidadeBnccEntity,
} from './persistencia/curriculo.entity';
import { EscolaEntity } from './persistencia/escola.entity';
import {
  MissaoEntity,
  MissaoHabilidadeEntity,
  PublicacaoDeMissaoEntity,
} from './persistencia/missao.entity';
import {
  MatriculaEntity,
  TrilhaEntity,
  TurmaEntity,
} from './persistencia/turma.entity';

export class RepositorioDeEducacaoTypeorm implements RepositorioDeEducacao {
  private trilhas?: Map<string, Nivel>;

  constructor(private readonly ds: DataSource) {}

  async criarEscola(nome: string) {
    const e = await this.ds.getRepository(EscolaEntity).save({ name: nome });
    return { id: e.id, nome: e.name };
  }

  async escola(id: string) {
    const e = await this.ds.getRepository(EscolaEntity).findOneBy({ id });
    return e ? { id: e.id, nome: e.name } : null;
  }

  private async mapaDeTrilhas(): Promise<Map<string, Nivel>> {
    if (!this.trilhas) {
      const ts = await this.ds.getRepository(TrilhaEntity).find();
      this.trilhas = new Map(
        ts.filter((t) => t.level).map((t) => [t.id, t.level as Nivel]),
      );
    }
    return this.trilhas;
  }

  async idDaTrilha(nivel: Nivel): Promise<string> {
    for (const [id, n] of await this.mapaDeTrilhas())
      if (n === nivel) return id;
    throw new ErroNaoEncontrado('Trilha');
  }

  private async paraTurma(e: TurmaEntity): Promise<Turma> {
    const trilhas = await this.mapaDeTrilhas();
    return {
      id: e.id,
      escolaId: e.schoolId,
      professorId: e.teacherUserId,
      nome: e.name,
      ano: e.year,
      nivel: e.trackId ? (trilhas.get(e.trackId) ?? null) : null,
    };
  }

  async criarTurma(t: Omit<Turma, 'id'>): Promise<Turma> {
    const e = await this.ds.getRepository(TurmaEntity).save({
      schoolId: t.escolaId,
      teacherUserId: t.professorId,
      name: t.nome,
      year: t.ano,
      trackId: t.nivel ? await this.idDaTrilha(t.nivel) : null,
    });
    return this.paraTurma(e);
  }

  async turma(id: string) {
    const e = await this.ds.getRepository(TurmaEntity).findOneBy({ id });
    return e ? this.paraTurma(e) : null;
  }

  async atualizarNivelDaTurma(id: string, nivel: Nivel) {
    await this.ds
      .getRepository(TurmaEntity)
      .update(
        { id },
        { trackId: await this.idDaTrilha(nivel), updatedAt: new Date() },
      );
  }

  async turmasDoProfessor(professorId: string) {
    const es = await this.ds
      .getRepository(TurmaEntity)
      .find({ where: { teacherUserId: professorId }, order: { name: 'ASC' } });
    return Promise.all(es.map((e) => this.paraTurma(e)));
  }

  async turmasDoAluno(alunoId: string) {
    const es = await this.ds
      .getRepository(TurmaEntity)
      .createQueryBuilder('c')
      .innerJoin(MatriculaEntity, 'e', 'e.class_id = c.id')
      .where('e.student_user_id = :alunoId', { alunoId })
      .orderBy('c.name', 'ASC')
      .getMany();
    return Promise.all(es.map((e) => this.paraTurma(e)));
  }

  async turmasDaEscola(escolaId: string) {
    const es = await this.ds
      .getRepository(TurmaEntity)
      .find({ where: { schoolId: escolaId }, order: { name: 'ASC' } });
    return Promise.all(es.map((e) => this.paraTurma(e)));
  }

  async matricular(turmaId: string, alunosIds: string[]) {
    const repo = this.ds.getRepository(MatriculaEntity);
    const existentes = new Set(
      (
        await repo.findBy({ classId: turmaId, studentUserId: In(alunosIds) })
      ).map((m) => m.studentUserId),
    );
    const novos = alunosIds.filter((a) => !existentes.has(a));
    if (novos.length > 0) {
      await repo
        .createQueryBuilder()
        .insert()
        .values(novos.map((a) => ({ classId: turmaId, studentUserId: a })))
        .orIgnore()
        .execute();
    }
    return { novos, jaMatriculados: [...existentes] };
  }

  async desmatricular(turmaId: string, alunoId: string) {
    const r = await this.ds
      .getRepository(MatriculaEntity)
      .delete({ classId: turmaId, studentUserId: alunoId });
    return (r.affected ?? 0) > 0;
  }

  async alunosDaTurma(turmaId: string) {
    const r: { id: string; name: string; is_minor: boolean }[] =
      await this.ds.query(
        `SELECT u.id, u.name, u.is_minor FROM platform.enrollment e JOIN platform.app_user u ON u.id = e.student_user_id
       WHERE e.class_id = $1 AND u.status <> 'pseudonymized' ORDER BY u.name, u.id`,
        [turmaId],
      );
    return r.map((x) => ({ id: x.id, nome: x.name, menor: x.is_minor }));
  }

  async usuariosDaEscola(ids: string[]) {
    if (ids.length === 0) return [];
    const r: {
      id: string;
      role: string;
      school_id: string | null;
      status: string;
    }[] = await this.ds.query(
      `SELECT id, role, school_id, status FROM platform.app_user WHERE id = ANY($1::uuid[])`,
      [ids],
    );
    return r.map((x) => ({
      id: x.id,
      papel: x.role,
      escolaId: x.school_id,
      situacao: x.status,
    }));
  }

  async fatosDaTurma(turmaId: string, alunoId?: string): Promise<FatosDaTurma> {
    const t = await this.ds
      .getRepository(TurmaEntity)
      .findOneBy({ id: turmaId });
    if (!t)
      return {
        existe: false,
        escolaId: null,
        professorId: null,
        alunoMatriculado: false,
      };
    const matriculado = alunoId
      ? (await this.ds
          .getRepository(MatriculaEntity)
          .countBy({ classId: turmaId, studentUserId: alunoId })) > 0
      : false;
    return {
      existe: true,
      escolaId: t.schoolId,
      professorId: t.teacherUserId,
      alunoMatriculado: matriculado,
    };
  }

  async codigosAtivosDoCatalogo(codigos: string[]) {
    const hs = await this.ds.getRepository(HabilidadeBnccEntity).find({
      where: {
        code: In(codigos.map((c) => c.trim().toUpperCase())),
        active: true,
      },
      select: { code: true },
    });
    return new Set(hs.map((h) => h.code));
  }

  async criarMissao(m: Omit<Missao, 'id' | 'turmas'>): Promise<Missao> {
    return this.ds.transaction(async (em) => {
      const trilha = await this.idDaTrilha(m.nivel);
      const e = await em.getRepository(MissaoEntity).save({
        trackId: trilha,
        title: m.titulo,
        description: m.descricao,
        objective: m.objetivo,
        schoolId: m.escolaId,
        createdByUserId: m.autorId,
        parameters: m.parametros,
        status: m.situacao,
      });
      const hs = await em
        .getRepository(HabilidadeBnccEntity)
        .findBy({ code: In(m.habilidades) });
      await em
        .getRepository(MissaoHabilidadeEntity)
        .insert(hs.map((h) => ({ missionId: e.id, bnccSkillId: h.id })));
      return { ...m, id: e.id, turmas: [] };
    });
  }

  async missao(id: string): Promise<Missao | null> {
    const e = await this.ds.getRepository(MissaoEntity).findOneBy({ id });
    if (!e) return null;
    return (await this.paraMissoes([e]))[0] ?? null;
  }

  private async paraMissoes(es: MissaoEntity[]): Promise<Missao[]> {
    if (es.length === 0) return [];
    const ids = es.map((e) => e.id);
    const hs: { mission_id: string; code: string }[] = await this.ds.query(
      `SELECT mb.mission_id, s.code FROM platform.mission_bncc mb JOIN platform.bncc_skill s ON s.id = mb.bncc_skill_id
       WHERE mb.mission_id = ANY($1::uuid[]) ORDER BY s.code`,
      [ids],
    );
    const ps = await this.ds
      .getRepository(PublicacaoDeMissaoEntity)
      .findBy({ missionId: In(ids) });
    const trilhas = await this.mapaDeTrilhas();
    return es.map((e) => ({
      id: e.id,
      escolaId: e.schoolId,
      autorId: e.createdByUserId,
      titulo: e.title,
      descricao: e.description,
      objetivo: e.objective,
      nivel: trilhas.get(e.trackId) ?? 'fundamental_ii',
      parametros: e.parameters,
      situacao: e.status,
      habilidades: hs.filter((h) => h.mission_id === e.id).map((h) => h.code),
      turmas: ps.filter((p) => p.missionId === e.id).map((p) => p.classId),
    }));
  }

  async publicarMissao(missaoId: string, turmasIds: string[], autorId: string) {
    await this.ds.transaction(async (em) => {
      await em
        .getRepository(PublicacaoDeMissaoEntity)
        .createQueryBuilder()
        .insert()
        .values(
          turmasIds.map((c) => ({
            missionId: missaoId,
            classId: c,
            assignedByUserId: autorId,
          })),
        )
        .orIgnore()
        .execute();
      await em
        .getRepository(MissaoEntity)
        .update(
          { id: missaoId },
          { status: 'published', updatedAt: new Date() },
        );
    });
  }

  async missoesDaTurma(turmaId: string, somentePublicadas: boolean) {
    const qb = this.ds
      .getRepository(MissaoEntity)
      .createQueryBuilder('m')
      .innerJoin(PublicacaoDeMissaoEntity, 'a', 'a.mission_id = m.id')
      .where('a.class_id = :turmaId', { turmaId })
      .orderBy('m.order_index', 'ASC')
      .addOrderBy('m.created_at', 'ASC');
    if (somentePublicadas) qb.andWhere(`m.status = 'published'`);
    return this.paraMissoes(await qb.getMany());
  }

  async fatosDaMissao(
    missaoId: string,
    ator: { id: string; papel: string },
  ): Promise<FatosDaMissao> {
    const e = await this.ds
      .getRepository(MissaoEntity)
      .findOneBy({ id: missaoId });
    if (!e)
      return {
        existe: false,
        escolaId: null,
        autorId: null,
        publicadaParaTurmaDoAluno: false,
        publicadaParaTurmaDoProfessor: false,
      };
    let aluno = false;
    let professor = false;
    if (ator.papel === 'student') {
      const r: unknown[] = await this.ds.query(
        `SELECT 1 FROM platform.mission_assignment a JOIN platform.enrollment en ON en.class_id = a.class_id
         JOIN platform.mission m ON m.id = a.mission_id
         WHERE a.mission_id = $1 AND en.student_user_id = $2 AND m.status = 'published' LIMIT 1`,
        [missaoId, ator.id],
      );
      aluno = r.length > 0;
    }
    if (ator.papel === 'teacher') {
      const r: unknown[] = await this.ds.query(
        `SELECT 1 FROM platform.mission_assignment a JOIN platform.class c ON c.id = a.class_id
         WHERE a.mission_id = $1 AND c.teacher_user_id = $2 LIMIT 1`,
        [missaoId, ator.id],
      );
      professor = r.length > 0;
    }
    return {
      existe: true,
      escolaId: e.schoolId,
      autorId: e.createdByUserId,
      publicadaParaTurmaDoAluno: aluno,
      publicadaParaTurmaDoProfessor: professor,
    };
  }

  async competencias(): Promise<CompetenciaDoCatalogo[]> {
    const cs = await this.ds
      .getRepository(CompetenciaEntity)
      .find({ order: { code: 'ASC' } });
    return cs
      .filter((c) => c.code)
      .map((c) => ({
        code: c.code!,
        name: c.name,
        description: c.description,
        generalCompetencies: c.generalCompetencies,
        validationStatus: c.validationStatus,
        catalogVersion: c.catalogVersion,
      }));
  }

  async habilidades(f: {
    stage?: string;
    competencyCode?: string;
    incluirInativas?: boolean;
  }) {
    const qb = this.ds
      .getRepository(HabilidadeBnccEntity)
      .createQueryBuilder('s')
      .leftJoin(CompetenciaEntity, 'c', 'c.id = s.competency_id')
      .select([
        's.code AS code',
        's.description AS description',
        's.component AS component',
        's.theme AS theme',
        's.stage AS stage',
        'c.code AS "competencyCode"',
        's.validation_status AS "validationStatus"',
        's.catalog_version AS "catalogVersion"',
        's.active AS active',
      ])
      .orderBy('s.code', 'ASC');
    if (!f.incluirInativas) qb.andWhere('s.active = true');
    if (f.stage) qb.andWhere('s.stage = :stage', { stage: f.stage });
    if (f.competencyCode) qb.andWhere('c.code = :cc', { cc: f.competencyCode });
    return qb.getRawMany<HabilidadeDoCatalogo>();
  }

  async salvarHabilidade(
    h: Partial<HabilidadeDoCatalogo> & { code: string },
    criar: boolean,
  ) {
    const repo = this.ds.getRepository(HabilidadeBnccEntity);
    const competencia = h.competencyCode
      ? await this.ds
          .getRepository(CompetenciaEntity)
          .findOneBy({ code: h.competencyCode })
      : undefined;
    if (h.competencyCode && !competencia)
      throw new ErroNaoEncontrado('Competência');
    const campos = {
      ...(h.description !== undefined ? { description: h.description } : {}),
      ...(h.component !== undefined ? { component: h.component } : {}),
      ...(h.theme !== undefined ? { theme: h.theme } : {}),
      ...(h.stage !== undefined
        ? { stage: h.stage as HabilidadeBnccEntity['stage'] }
        : {}),
      ...(h.validationStatus !== undefined
        ? {
            validationStatus:
              h.validationStatus as HabilidadeBnccEntity['validationStatus'],
          }
        : {}),
      ...(h.catalogVersion !== undefined
        ? { catalogVersion: h.catalogVersion }
        : {}),
      ...(h.active !== undefined ? { active: h.active } : {}),
      ...(competencia ? { competencyId: competencia.id } : {}),
      updatedAt: new Date(),
    };
    if (criar) {
      await repo.insert({
        code: h.code,
        description: h.description ?? '',
        ...campos,
      });
    } else {
      const r = await repo.update({ code: h.code }, campos);
      if ((r.affected ?? 0) === 0) return null;
    }
    return (
      (await this.habilidades({ incluirInativas: true })).find(
        (x) => x.code === h.code,
      ) ?? null
    );
  }
}
