import { SetMetadata } from '@nestjs/common';

import type { Finalidade } from '../kernel/finalidades';
import type { Papel } from '../kernel/papeis';

/**
 * Declaração de autorização de uma rota. Toda rota precisa de uma
 * (o guard nega a rota que não tiver, e um teste de arquitetura falha).
 */
export type DeclaracaoDeAutorizacao =
  | { publico: true; motivo: string }
  | { servico: true; servicos?: string[] }
  | {
      papeis: readonly Papel[];
      /** Regra de posse avaliada pelo guard e verificada de novo no caso de uso. */
      posse?: {
        regra: string;
        parametro?: string;
        origem?: 'params' | 'body' | 'query';
      };
      /** Finalidade exigida quando o próprio ator é menor (aluno). */
      consentimento?: Finalidade;
    };

export const META_AUTORIZACAO = 'ecosfera:autorizacao';

export const Autorizacao = (d: DeclaracaoDeAutorizacao) =>
  SetMetadata(META_AUTORIZACAO, d);
