import { AsyncLocalStorage } from 'node:async_hooks';
import { randomBytes } from 'node:crypto';
import { trace } from '@opentelemetry/api';

import type { Ator } from '../kernel/ator';

/** Contexto por requisição: traceId e ator. Nada de estado global mutável. */
export interface ContextoDaRequisicao {
  traceId: string;
  ator?: Ator;
}

const armazenamento = new AsyncLocalStorage<ContextoDaRequisicao>();

export function executarComContexto<T>(
  ctx: ContextoDaRequisicao,
  fn: () => T,
): T {
  return armazenamento.run(ctx, fn);
}

export function contextoAtual(): ContextoDaRequisicao | undefined {
  return armazenamento.getStore();
}

/** traceId do span OTel ativo; senão, do contexto; senão, um novo. */
export function traceIdAtual(): string {
  const span = trace.getActiveSpan();
  const id = span?.spanContext().traceId;
  if (id && id !== '00000000000000000000000000000000') return id;
  return armazenamento.getStore()?.traceId ?? novoTraceId();
}

export function novoTraceId(): string {
  return randomBytes(16).toString('hex');
}
