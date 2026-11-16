import { z } from 'zod';

import type { TipoDeProblema } from '../kernel/erros';

/**
 * Catálogo dos tipos de erro RFC 7807 do platform-api.
 * `type` é relativo (`/errors/<slug>`), como no exemplo do Dossiê §5.
 */
export const CATALOGO_DE_PROBLEMAS: Record<
  TipoDeProblema,
  { status: number; titulo: string }
> = {
  validation: { status: 422, titulo: 'Dados inválidos' },
  'bad-request': { status: 400, titulo: 'Requisição malformada' },
  unauthenticated: { status: 401, titulo: 'Não autenticado' },
  forbidden: { status: 403, titulo: 'Acesso negado' },
  'consent-required': {
    status: 403,
    titulo: 'Consentimento do responsável necessário',
  },
  'not-found': { status: 404, titulo: 'Recurso não encontrado' },
  conflict: { status: 409, titulo: 'Conflito' },
  'insufficient-action-points': {
    status: 409,
    titulo: 'Pontos de ação insuficientes',
  },
  'payload-too-large': { status: 413, titulo: 'Conteúdo grande demais' },
  'rate-limited': { status: 429, titulo: 'Limite de requisições excedido' },
  'dependency-unavailable': { status: 503, titulo: 'Dependência indisponível' },
  'dependency-timeout': {
    status: 504,
    titulo: 'Dependência não respondeu a tempo',
  },
  'not-implemented': { status: 501, titulo: 'Não implementado' },
  internal: { status: 500, titulo: 'Erro interno' },
};

export const EsquemaProblema = z
  .object({
    type: z.string().describe('URI relativa do tipo de erro (/errors/<slug>)'),
    title: z.string(),
    status: z.number().int(),
    detail: z.string(),
    instance: z.string(),
    traceId: z.string(),
    errors: z
      .array(z.object({ field: z.string(), message: z.string() }))
      .optional(),
  })
  .catchall(z.unknown())
  .meta({
    id: 'Problem',
    description: 'Erro no formato RFC 7807 (Problem Details)',
  });

export type Problema = z.infer<typeof EsquemaProblema>;

export function tipoUri(tipo: TipoDeProblema): string {
  return `/errors/${tipo}`;
}
