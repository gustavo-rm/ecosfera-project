import type { ResultadoDePosse } from '../autorizacao/portas';
import type { AtorUsuario } from './ator';

/**
 * Política de acesso a dados de um aluno (ou de qualquer usuário-alvo). Função pura:
 * o guard a avalia com fatos carregados por ele, e o caso de uso a avalia de novo
 * com fatos que ele mesmo carrega (defesa em profundidade).
 *
 * Recurso de outra escola vira "inexistente" (404): não revelamos que existe.
 */
export interface FatosDoAlvo {
  existe: boolean;
  alvoId: string;
  escolaId: string | null;
  lecionaParaAlvo: boolean;
  responsavelPeloAlvo: boolean;
}

export type Intencao =
  /** Ler perfil/dados pessoais básicos. */
  | 'ler'
  /** Ler dados pedagógicos (avaliação, evidências). O próprio aluno NÃO pode (RP-004). */
  | 'ler-pedagogico'
  /** Gerir conta (papel, correção, exclusão). */
  | 'gerir';

export function decidirAcessoAoUsuario(
  ator: AtorUsuario,
  f: FatosDoAlvo,
  intencao: Intencao,
): ResultadoDePosse {
  if (!f.existe) return 'inexistente';
  const mesmaEscola = ator.escolaId !== null && f.escolaId === ator.escolaId;

  if (ator.papel === 'platform_admin') {
    return intencao === 'gerir' || intencao === 'ler' ? 'permitido' : 'negado';
  }
  if (ator.usuarioId === f.alvoId) {
    return intencao === 'ler-pedagogico'
      ? 'negado'
      : intencao === 'gerir'
        ? 'negado'
        : 'permitido';
  }
  if (ator.papel === 'guardian') {
    if (!f.responsavelPeloAlvo) return 'inexistente';
    return intencao === 'ler' ? 'permitido' : 'negado';
  }
  if (!mesmaEscola) return 'inexistente';
  switch (ator.papel) {
    case 'admin':
      return 'permitido';
    case 'coordinator':
      return intencao === 'gerir' ? 'negado' : 'permitido';
    case 'teacher':
      if (intencao === 'gerir') return 'negado';
      return f.lecionaParaAlvo ? 'permitido' : 'negado';
    default:
      return 'negado';
  }
}
