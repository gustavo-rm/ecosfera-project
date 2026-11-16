import { Inject, Injectable } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import { registrarNoOutbox } from '../../../shared/eventos/eventos';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroAcessoNegado, ErroDeConflito, ErroDeValidacao, ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { ServicoDeUsuarios } from '../../identity/application/usuarios.service';
import type { Usuario } from '../../identity/domain/usuario';
import { EscolaEntity } from '../infrastructure/persistencia/escola.entity';
import {
  decidirAcessoAMissao,
  decidirAcessoATurma,
  type Missao,
  type Nivel,
  type Turma,
  validarAncoragem,
  validarParametros,
} from '../domain/educacao';
import { type HabilidadeDoCatalogo, REPOSITORIO_DE_EDUCACAO, type RepositorioDeEducacao } from '../domain/portas';

@Injectable()
export class ServicoDeEducacao {
  constructor(
    @Inject(REPOSITORIO_DE_EDUCACAO) private readonly repo: RepositorioDeEducacao,
    private readonly usuarios: ServicoDeUsuarios,
    private readonly auditoria: Auditoria,
    private readonly ds: DataSource,
  ) {}

  // ── Escolas (RF-001) ─────────────────────────────────────────────────────
  async criarEscola(ator: AtorUsuario, nome: string, admin: { name: string; email: string; password?: string }) {
    if (ator.papel !== 'platform_admin') throw new ErroAcessoNegado();
    const escola = await this.repo.criarEscola(nome.trim());
    let adminInicial: Usuario;
    try {
      adminInicial = await this.usuarios.criar(ator, { ...admin, role: 'admin', schoolId: escola.id });
    } catch (e) {
      await this.ds.getRepository(EscolaEntity).delete({ id: escola.id }); // compensação
      throw e;
    }
    await this.auditoria.registrar({ acao: 'school.created', entidade: 'school', entidadeId: escola.id, escolaId: escola.id, dados: { initialAdminId: adminInicial.id } });
    return { escola, admin: adminInicial };
  }

  async escola(ator: AtorUsuario, id: string) {
    if (ator.papel !== 'platform_admin' && ator.escolaId !== id) throw new ErroNaoEncontrado('Escola');
    const e = await this.repo.escola(id);
    if (!e) throw new ErroNaoEncontrado('Escola');
    return e;
  }

  // ── Turmas (RF-005, RF-061) ──────────────────────────────────────────────
  async exigirTurma(ator: AtorUsuario, turmaId: string, intencao: 'ler' | 'gerir'): Promise<Turma> {
    const f = await this.repo.fatosDaTurma(turmaId, ator.papel === 'student' ? ator.usuarioId : undefined);
    const d = decidirAcessoATurma(ator, f, intencao);
    if (d === 'inexistente') throw new ErroNaoEncontrado('Turma');
    if (d === 'negado') throw new ErroAcessoNegado();
    const t = await this.repo.turma(turmaId);
    if (!t) throw new ErroNaoEncontrado('Turma');
    return t;
  }

  async criarTurma(ator: AtorUsuario, d: { name: string; year?: number; trackLevel?: Nivel; teacherUserId?: string }) {
    if (!ator.escolaId) throw new ErroAcessoNegado();
    let professorId = ator.usuarioId;
    if (ator.papel !== 'teacher') {
      if (!d.teacherUserId) throw new ErroDeValidacao('Informe o professor da turma', [{ campo: 'body.teacherUserId', mensagem: 'obrigatório' }]);
      professorId = d.teacherUserId;
    } else if (d.teacherUserId && d.teacherUserId !== ator.usuarioId) {
      throw new ErroAcessoNegado('Professor só cria turmas para si');
    }
    const [prof] = await this.repo.usuariosDaEscola([professorId]);
    if (!prof || prof.papel !== 'teacher' || prof.escolaId !== ator.escolaId) throw new ErroNaoEncontrado('Professor');
    const t = await this.repo.criarTurma({ escolaId: ator.escolaId, professorId, nome: d.name.trim(), ano: d.year ?? null, nivel: d.trackLevel ?? null });
    await this.auditoria.registrar({ acao: 'class.created', entidade: 'class', entidadeId: t.id, escolaId: t.escolaId, dados: { teacherUserId: professorId } });
    return t;
  }

  async turmas(ator: AtorUsuario): Promise<Turma[]> {
    if (!ator.escolaId) return [];
    if (ator.papel === 'teacher') return this.repo.turmasDoProfessor(ator.usuarioId);
    if (ator.papel === 'student') return this.repo.turmasDoAluno(ator.usuarioId);
    if (ator.papel === 'admin' || ator.papel === 'coordinator') return this.repo.turmasDaEscola(ator.escolaId);
    throw new ErroAcessoNegado();
  }

  async matricular(ator: AtorUsuario, turmaId: string, alunosIds: string[]) {
    const t = await this.exigirTurma(ator, turmaId, 'gerir');
    const unicos = [...new Set(alunosIds)];
    const us = await this.repo.usuariosDaEscola(unicos);
    // Isolamento por escola: aluno de outra escola é tratado como inexistente.
    const invalidos = unicos.filter((id) => {
      const u = us.find((x) => x.id === id);
      return !u || u.papel !== 'student' || u.escolaId !== t.escolaId || u.situacao !== 'active';
    });
    if (invalidos.length > 0) {
      throw new ErroDeValidacao('Há alunos inexistentes ou de outra escola', invalidos.map((i) => ({ campo: 'body.studentIds', mensagem: `aluno não encontrado: ${i}` })));
    }
    const r = await this.repo.matricular(turmaId, unicos);
    await this.auditoria.registrar({ acao: 'class.students_enrolled', entidade: 'class', entidadeId: turmaId, escolaId: t.escolaId, dados: { enrolled: r.novos } });
    return r;
  }

  async desmatricular(ator: AtorUsuario, turmaId: string, alunoId: string) {
    const t = await this.exigirTurma(ator, turmaId, 'gerir');
    if (!(await this.repo.desmatricular(turmaId, alunoId))) throw new ErroNaoEncontrado('Matrícula');
    await this.auditoria.registrar({ acao: 'class.student_removed', entidade: 'class', entidadeId: turmaId, escolaId: t.escolaId, dados: { studentId: alunoId } });
  }

  async alunos(ator: AtorUsuario, turmaId: string) {
    await this.exigirTurma(ator, turmaId, 'gerir');
    return this.repo.alunosDaTurma(turmaId);
  }

  async definirTrilha(ator: AtorUsuario, turmaId: string, nivel: Nivel) {
    const t = await this.exigirTurma(ator, turmaId, 'gerir');
    await this.repo.atualizarNivelDaTurma(turmaId, nivel);
    return { ...t, nivel };
  }

  // ── Missões (RF-062, RP-001) ─────────────────────────────────────────────
  async exigirMissao(ator: AtorUsuario, id: string, intencao: 'ler' | 'gerir'): Promise<Missao> {
    const f = await this.repo.fatosDaMissao(id, { id: ator.usuarioId, papel: ator.papel });
    const d = decidirAcessoAMissao(ator, f, intencao);
    if (d === 'inexistente') throw new ErroNaoEncontrado('Missão');
    if (d === 'negado') throw new ErroAcessoNegado();
    const m = await this.repo.missao(id);
    if (!m) throw new ErroNaoEncontrado('Missão');
    return m;
  }

  async criarMissao(
    ator: AtorUsuario,
    d: { title: string; description?: string; objective: string; trackLevel: Nivel; bnccCodes: string[]; parameters?: Record<string, unknown>; classIds?: string[] },
  ): Promise<Missao> {
    if (!ator.escolaId || !['teacher', 'coordinator', 'admin'].includes(ator.papel)) throw new ErroAcessoNegado();
    const codigos = [...new Set(d.bnccCodes.map((c) => c.trim().toUpperCase()))];
    validarAncoragem(codigos, await this.repo.codigosAtivosDoCatalogo(codigos));
    validarParametros(d.parameters ?? {});
    for (const turmaId of d.classIds ?? []) await this.exigirTurma(ator, turmaId, 'gerir');
    const m = await this.repo.criarMissao({
      escolaId: ator.escolaId,
      autorId: ator.usuarioId,
      titulo: d.title.trim(),
      descricao: d.description ?? null,
      objetivo: d.objective,
      nivel: d.trackLevel,
      parametros: d.parameters ?? {},
      situacao: 'draft',
      habilidades: codigos,
    });
    await this.auditoria.registrar({ acao: 'mission.created', entidade: 'mission', entidadeId: m.id, escolaId: m.escolaId, dados: { bnccCodes: codigos } });
    if (d.classIds && d.classIds.length > 0) return this.publicar(ator, m.id, d.classIds);
    return m;
  }

  async publicar(ator: AtorUsuario, missaoId: string, turmasIds: string[]): Promise<Missao> {
    const m = await this.exigirMissao(ator, missaoId, 'gerir');
    if (m.situacao === 'archived') throw new ErroDeConflito('Missão arquivada não pode ser publicada');
    for (const turmaId of turmasIds) await this.exigirTurma(ator, turmaId, 'gerir');
    await this.repo.publicarMissao(missaoId, [...new Set(turmasIds)], ator.usuarioId);
    await this.ds.transaction((em) => registrarNoOutbox(em, 'MissaoPublicada', missaoId, { missionId: missaoId, classIds: turmasIds, bnccCodes: m.habilidades }));
    await this.auditoria.registrar({ acao: 'mission.published', entidade: 'mission', entidadeId: missaoId, escolaId: m.escolaId, dados: { classIds: turmasIds } });
    return (await this.repo.missao(missaoId))!;
  }

  async missoesDaTurma(ator: AtorUsuario, turmaId: string): Promise<Missao[]> {
    await this.exigirTurma(ator, turmaId, 'ler');
    return this.repo.missoesDaTurma(turmaId, ator.papel === 'student');
  }

  // ── Catálogo curricular (RSK-06: dado versionado, revisável sem deploy) ──
  competencias() {
    return this.repo.competencias();
  }

  habilidades(f: { stage?: string; competencyCode?: string }) {
    return this.repo.habilidades(f);
  }

  async revisarHabilidade(ator: AtorUsuario, codigo: string, mudanca: Partial<HabilidadeDoCatalogo>, criar: boolean) {
    if (ator.papel !== 'platform_admin') throw new ErroAcessoNegado('Só o responsável pelo catálogo revisa habilidades');
    const code = codigo.trim().toUpperCase();
    let h: HabilidadeDoCatalogo | null;
    try {
      h = await this.repo.salvarHabilidade({ ...mudanca, code }, criar);
    } catch (e) {
      if ((e as { code?: string }).code === '23505') throw new ErroDeConflito('Habilidade já existe');
      throw e;
    }
    if (!h) throw new ErroNaoEncontrado('Habilidade');
    await this.auditoria.registrar({ acao: criar ? 'curriculum.skill_created' : 'curriculum.skill_reviewed', entidade: 'bncc_skill', entidadeId: code, escolaId: null, dados: { ...mudanca } });
    return h;
  }
}
