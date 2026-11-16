import { z } from 'zod';

/** Convenções únicas de paginação, ordenação e identificadores. */
export const Uuid = z.uuid({ version: 'v4' }).meta({ format: 'uuid' });

export const ParametroId = z.object({ id: Uuid });

export const ConsultaPaginada = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(20),
});

export function Pagina<T extends z.ZodType>(item: T, nome: string) {
  return z
    .object({
      items: z.array(item),
      page: z.number().int(),
      pageSize: z.number().int(),
      total: z.number().int(),
    })
    .meta({ id: nome });
}

export const DataHora = z.iso.datetime({ offset: true });

export const SemConteudo = undefined;
