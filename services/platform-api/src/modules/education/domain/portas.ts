import type { FatosDaMissao, FatosDaTurma, Missao, Nivel, Turma } from './educacao';

export interface HabilidadeDoCatalogo {
  code: string;
  description: string;
  component: string | null;
  theme: string | null;
  stage: string | null;
  competencyCode: string | null;
  validationStatus: string;
  catalogVersion: string;
  active: boolean;
}

export interface CompetenciaDoCatalogo {
  code: string;
  name: string;
  description: string | null;
  generalCompetencies: string[];
  validationStatus: string;
  catalogVersion: string;
}

/** Persistência do contexto education (implementada com TypeORM na infraestrutura). */
export interface RepositorioDeEducacao {
  criarEscola(nome: string): Promise<{ id: string; nome: string }>;
  escola(id: string): Promise<{ id: string; nome: string } | null>;

  idDaTrilha(nivel: Nivel): Promise<string>;
  criarTurma(t: Omit<Turma, 'id'>): Promise<Turma>;
  turma(id: string): Promise<Turma | null>;
  atualizarNivelDaTurma(id: string, nivel: Nivel): Promise<void>;
  turmasDoProfessor(professorId: string): Promise<Turma[]>;
  turmasDoAluno(alunoId: string): Promise<Turma[]>;
  turmasDaEscola(escolaId: string): Promise<Turma[]>;
  matricular(turmaId: string, alunosIds: string[]): Promise<{ novos: string[]; jaMatriculados: string[] }>;
  desmatricular(turmaId: string, alunoId: string): Promise<boolean>;
  alunosDaTurma(turmaId: string): Promise<{ id: string; nome: string; menor: boolean }[]>;
  usuariosDaEscola(ids: string[]): Promise<{ id: string; papel: string; escolaId: string | null; situacao: string }[]>;
  fatosDaTurma(turmaId: string, alunoId?: string): Promise<FatosDaTurma>;

  codigosAtivosDoCatalogo(codigos: string[]): Promise<Set<string>>;
  criarMissao(m: Omit<Missao, 'id' | 'turmas'>): Promise<Missao>;
  missao(id: string): Promise<Missao | null>;
  publicarMissao(missaoId: string, turmasIds: string[], autorId: string): Promise<void>;
  missoesDaTurma(turmaId: string, somentePublicadas: boolean): Promise<Missao[]>;
  fatosDaMissao(missaoId: string, ator: { id: string; papel: string }): Promise<FatosDaMissao>;

  competencias(): Promise<CompetenciaDoCatalogo[]>;
  habilidades(filtro: { stage?: string; competencyCode?: string; incluirInativas?: boolean }): Promise<HabilidadeDoCatalogo[]>;
  salvarHabilidade(h: Partial<HabilidadeDoCatalogo> & { code: string }, criar: boolean): Promise<HabilidadeDoCatalogo | null>;
}
export const REPOSITORIO_DE_EDUCACAO = Symbol('RepositorioDeEducacao');
