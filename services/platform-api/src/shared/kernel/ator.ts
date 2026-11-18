import type { Papel } from './papeis';

/**
 * Quem está agindo. Montado pelo guard central a partir do token
 * e repassado aos casos de uso (que verificam de novo a autorização).
 */
export interface AtorUsuario {
  tipo: 'usuario';
  usuarioId: string;
  papel: Papel;
  /** Escola (tenant). Nulo só para platform_admin e pesquisador global. */
  escolaId: string | null;
  menor: boolean;
  sessaoId: string;
}

export interface AtorServico {
  tipo: 'servico';
  servico: string;
}

export type Ator = AtorUsuario | AtorServico;

export function ehUsuario(a: Ator | undefined): a is AtorUsuario {
  return !!a && a.tipo === 'usuario';
}
