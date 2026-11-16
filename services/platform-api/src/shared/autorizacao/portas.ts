import type { AtorServico, AtorUsuario } from '../kernel/ator';
import type { Finalidade } from '../kernel/finalidades';

/** Verifica tokens (implementado no contexto identity). */
export interface VerificadorDeCredenciais {
  verificarAcesso(token: string): Promise<AtorUsuario>;
  verificarServico(token: string): Promise<AtorServico>;
}
export const VERIFICADOR_DE_CREDENCIAIS = Symbol('VerificadorDeCredenciais');

/** Gate de consentimento (implementado no contexto identity). */
export interface GateDeConsentimento {
  /** Verdadeiro se o usuário não é menor ou tem consentimento válido para a finalidade. */
  permite(usuarioId: string, finalidade: Finalidade): Promise<boolean>;
}
export const GATE_DE_CONSENTIMENTO = Symbol('GateDeConsentimento');

export type ResultadoDePosse = 'permitido' | 'negado' | 'inexistente';

/** Regra de posse: o ator pode agir sobre o recurso identificado por `valor`? */
export type RegraDePosse = (
  ator: AtorUsuario,
  valor: string,
) => Promise<ResultadoDePosse>;
