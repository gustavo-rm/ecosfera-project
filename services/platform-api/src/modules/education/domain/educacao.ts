import type { ResultadoDePosse } from '../../../shared/autorizacao/portas';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroDeValidacao } from '../../../shared/kernel/erros';

/** Trilha por nível (RF-061, RP-002). */
export const NIVEIS = ['fundamental_ii', 'medio', 'tecnico'] as const;
export type Nivel = (typeof NIVEIS)[number];

export type SituacaoDaMissao = 'draft' | 'published' | 'archived';

export interface Turma {
  id: string;
  escolaId: string;
  professorId: string | null;
  nome: string;
  ano: number | null;
  nivel: Nivel | null;
}

export interface Missao {
  id: string;
  escolaId: string | null;
  autorId: string | null;
  titulo: string;
  descricao: string | null;
  objetivo: string | null;
  nivel: Nivel;
  parametros: Record<string, unknown>;
  situacao: SituacaoDaMissao;
  habilidades: string[];
  turmas: string[];
}

/** VO HabilidadeBNCC(código): formato oficial EFxxAAnn / EMxxAAAnnn. */
const CODIGO_BNCC =
  /^(EF\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2}[A-Z]?|EM\d{2}[A-Z]{3}\d{3})$/;
export function codigoBnccValido(codigo: string): boolean {
  return CODIGO_BNCC.test(codigo);
}

/**
 * RP-001: toda missão é ancorada a pelo menos uma habilidade BNCC existente e ativa no catálogo.
 * `catalogo` = códigos ativos conhecidos. Devolve os códigos inválidos (422).
 */
export function validarAncoragem(
  codigos: string[],
  catalogo: ReadonlySet<string>,
): void {
  const unicos = [...new Set(codigos.map((c) => c.trim().toUpperCase()))];
  if (unicos.length === 0) {
    throw new ErroDeValidacao(
      'A missão precisa de pelo menos uma habilidade BNCC',
      [{ campo: 'body.bnccCodes', mensagem: 'obrigatório' }],
    );
  }
  const invalidos = unicos.filter((c) => !catalogo.has(c));
  if (invalidos.length > 0) {
    throw new ErroDeValidacao(
      'Habilidade BNCC inexistente no catálogo',
      invalidos.map((c) => ({
        campo: 'body.bnccCodes',
        mensagem: `código desconhecido ou inativo: ${c}`,
      })),
    );
  }
}

/** Parâmetros da missão: objeto pequeno e plano o bastante para ir ao serviço de simulação. */
export function validarParametros(p: Record<string, unknown>): void {
  if (JSON.stringify(p).length > 8 * 1024) {
    throw new ErroDeValidacao('Parâmetros da missão grandes demais', [
      { campo: 'body.parameters', mensagem: 'máximo 8 KiB' },
    ]);
  }
}

export interface FatosDaTurma {
  existe: boolean;
  escolaId: string | null;
  professorId: string | null;
  alunoMatriculado: boolean;
}

/** Acesso a turma: professor da turma, aluno matriculado (só leitura), coordenação/admin da escola. */
export function decidirAcessoATurma(
  ator: AtorUsuario,
  f: FatosDaTurma,
  intencao: 'ler' | 'gerir',
): ResultadoDePosse {
  if (!f.existe) return 'inexistente';
  if (ator.escolaId === null || f.escolaId !== ator.escolaId)
    return 'inexistente';
  switch (ator.papel) {
    case 'admin':
    case 'coordinator':
      return 'permitido';
    case 'teacher':
      return f.professorId === ator.usuarioId ? 'permitido' : 'negado';
    case 'student':
      return intencao === 'ler' && f.alunoMatriculado ? 'permitido' : 'negado';
    default:
      return 'negado';
  }
}

export interface FatosDaMissao {
  existe: boolean;
  escolaId: string | null;
  autorId: string | null;
  publicadaParaTurmaDoAluno: boolean;
  publicadaParaTurmaDoProfessor: boolean;
}

export function decidirAcessoAMissao(
  ator: AtorUsuario,
  f: FatosDaMissao,
  intencao: 'ler' | 'gerir',
): ResultadoDePosse {
  if (!f.existe) return 'inexistente';
  if (ator.escolaId === null || f.escolaId !== ator.escolaId)
    return 'inexistente';
  switch (ator.papel) {
    case 'admin':
    case 'coordinator':
      return 'permitido';
    case 'teacher':
      if (f.autorId === ator.usuarioId) return 'permitido';
      return intencao === 'ler' ? 'permitido' : 'negado';
    case 'student':
      return intencao === 'ler' && f.publicadaParaTurmaDoAluno
        ? 'permitido'
        : 'negado';
    default:
      return 'negado';
  }
}
