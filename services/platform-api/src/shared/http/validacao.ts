import {
  type CallHandler,
  type ExecutionContext,
  Injectable,
  type NestInterceptor,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import type { Observable } from 'rxjs';
import { z } from 'zod';

import { ErroDeValidacao } from '../kernel/erros';
import { type DefinicaoDeEndpoint, META_CONTRATO } from './contrato';

// Mensagens de validação em pt-BR (RNF-026).
z.config(z.locales.ptBR());

/** Converte issues do Zod em detalhes de campo, sem ecoar valores enviados. */
export function errosDoZod(origem: string, erro: z.ZodError): { campo: string; mensagem: string }[] {
  return erro.issues.map((i) => ({
    campo: [origem, ...i.path.map(String)].join('.'),
    mensagem: i.message,
  }));
}

export function validar<T extends z.ZodType>(esquema: T, valor: unknown, origem: string): z.infer<T> {
  const r = esquema.safeParse(valor);
  if (!r.success) {
    throw new ErroDeValidacao('Os dados enviados não passaram na validação', errosDoZod(origem, r.error));
  }
  return r.data;
}

/**
 * Valida parâmetros, query e corpo pelo contrato da rota e substitui
 * os valores pelos valores já convertidos (coerção, defaults, strip).
 * Roda depois do guard: quem não pode, recebe 401/403 antes de 422.
 */
@Injectable()
export class InterceptadorDeValidacao implements NestInterceptor {
  constructor(private readonly reflector: Reflector) {}

  intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown> {
    if (ctx.getType() !== 'http') return next.handle();
    const def = this.reflector.get<DefinicaoDeEndpoint | undefined>(META_CONTRATO, ctx.getHandler());
    if (def) {
      const req = ctx.switchToHttp().getRequest<Request & { consultaValidada?: unknown }>();
      if (def.parametros) req.params = validar(def.parametros, req.params, 'params') as Record<string, string>;
      if (def.consulta) req.consultaValidada = validar(def.consulta, req.query, 'query');
      if (def.corpo) req.body = validar(def.corpo, req.body ?? {}, 'body') as unknown;
    }
    return next.handle();
  }
}
