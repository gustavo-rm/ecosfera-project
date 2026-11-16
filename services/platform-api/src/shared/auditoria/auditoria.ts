import type { EntityManager } from 'typeorm';

import type { Json } from '../database/colunas';

import type { Ator } from '../kernel/ator';
import { contextoAtual, traceIdAtual } from '../observabilidade/contexto';
import { AuditLogEntity } from './audit-log.entity';

export type ResultadoAuditado = 'success' | 'denied' | 'failure';

export interface RegistroDeAuditoria {
  /** Ex.: consent.granted, consent.revoked, export.created, user.role_changed, auth.login_failed. */
  acao: string;
  entidade: string;
  entidadeId?: string | null;
  escolaId?: string | null;
  /** Só identificadores e metadados. Nada de nome, e-mail ou conteúdo pessoal. */
  dados?: Record<string, unknown>;
  resultado?: ResultadoAuditado;
  ator?: Ator;
}

/**
 * Registro imutável de ações sensíveis. Só INSERT: o banco recusa UPDATE/DELETE/TRUNCATE.
 * Quando chamado com o EntityManager de uma transação, o registro entra nela.
 */
export class Auditoria {
  constructor(private readonly gerenciador: EntityManager) {}

  async registrar(r: RegistroDeAuditoria, em?: EntityManager): Promise<void> {
    const ator = r.ator ?? contextoAtual()?.ator;
    const m = em ?? this.gerenciador;
    await m.insert(AuditLogEntity, {
      actorUserId: ator?.tipo === 'usuario' ? ator.usuarioId : null,
      actorService: ator?.tipo === 'servico' ? ator.servico : null,
      action: r.acao,
      entity: r.entidade,
      entityId: r.entidadeId ?? null,
      schoolId: r.escolaId ?? (ator?.tipo === 'usuario' ? ator.escolaId : null),
      data: (r.dados ?? {}) as Json,
      outcome: r.resultado ?? 'success',
      traceId: traceIdAtual(),
    });
  }
}
