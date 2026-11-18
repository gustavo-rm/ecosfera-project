import type { ResultadoDePosse } from '../../../shared/autorizacao/portas';
import type { AtorUsuario } from '../../../shared/kernel/ator';

/** Referência do planeta no platform-api (planet_meta). O estado é do serviço de simulação. */
export interface PlanetaMeta {
  id: string;
  donoId: string;
  escolaId: string | null;
  missaoId: string | null;
  eraAtual: number;
  seed: string;
  situacao: 'active' | 'archived';
}

export interface FatosDoPlaneta {
  existe: boolean;
  donoId: string | null;
  escolaId: string | null;
  professorDoDono: boolean;
}

/**
 * Posse do planeta: o aluno só acessa o próprio; o professor, os dos alunos das suas turmas
 * (só leitura); coordenação/admin da escola, leitura. Outra escola → inexistente (404).
 */
export function decidirAcessoAoPlaneta(
  ator: AtorUsuario,
  f: FatosDoPlaneta,
  intencao: 'ler' | 'agir',
): ResultadoDePosse {
  if (!f.existe) return 'inexistente';
  if (ator.papel === 'student') {
    if (f.donoId === ator.usuarioId) return 'permitido';
    return 'inexistente';
  }
  if (ator.escolaId === null || f.escolaId !== ator.escolaId)
    return 'inexistente';
  if (intencao === 'agir') return 'negado';
  if (ator.papel === 'teacher')
    return f.professorDoDono ? 'permitido' : 'negado';
  if (ator.papel === 'coordinator' || ator.papel === 'admin')
    return 'permitido';
  return 'negado';
}
