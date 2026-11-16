/**
 * Fatos de vínculo escolar (turma, matrícula, responsável), consultados por vários contextos.
 * Porta implementada pelo contexto education (e responsável, pelo identity).
 */
export interface VinculosEscolares {
  /** O professor dá aula em alguma turma em que o aluno está matriculado? */
  professorLecionaParaAluno(professorId: string, alunoId: string): Promise<boolean>;
  /** O usuário é responsável vinculado ao aluno? */
  responsavelPeloAluno(responsavelId: string, alunoId: string): Promise<boolean>;
  /** Escola do usuário (null se não existir ou não tiver escola). */
  escolaDoUsuario(usuarioId: string): Promise<{ existe: boolean; escolaId: string | null; papel: string | null }>;
}
export const VINCULOS_ESCOLARES = Symbol('VinculosEscolares');
