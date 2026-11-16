import { randomUUID } from 'node:crypto';

import type { EntityManager } from 'typeorm';

import type { Json } from '../database/colunas';
import { traceIdAtual } from '../observabilidade/contexto';
import { EventoDeSaidaEntity } from './eventos.entity';

/**
 * Eventos de domínio publicados pelo platform-api (contrato assíncrono em
 * packages/api-contracts/asyncapi). Nomes da linguagem ubíqua.
 */
export type TipoDeEventoPublicado =
  | 'PlanetaCriado'
  | 'IntervencaoAplicada'
  | 'ConsentimentoRevogado'
  | 'ConsentimentoConcedido'
  | 'MissaoPublicada';

export interface EnvelopeDeEvento {
  eventId: string;
  type: string;
  version: 1;
  occurredAt: string;
  traceId: string;
  producer: 'platform-api';
  data: Record<string, unknown>;
}

/** Grava o evento no outbox dentro da transação do fato (publicado depois pelo relay). */
export async function registrarNoOutbox(
  em: EntityManager,
  tipo: TipoDeEventoPublicado,
  agregadoId: string,
  data: Record<string, unknown>,
): Promise<string> {
  const id = randomUUID();
  await em.insert(EventoDeSaidaEntity, {
    id,
    eventType: tipo,
    aggregateId: agregadoId,
    payload: data as Json,
    traceId: traceIdAtual(),
  });
  return id;
}
