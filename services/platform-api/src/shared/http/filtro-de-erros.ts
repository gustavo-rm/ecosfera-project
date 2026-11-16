import {
  type ArgumentsHost,
  Catch,
  type ExceptionFilter,
  HttpException,
  Inject,
} from '@nestjs/common';
import type { Request, Response } from 'express';
import type { Logger } from 'pino';

import { ErroDeAplicacao, ErroDeValidacao, type TipoDeProblema } from '../kernel/erros';
import { traceIdAtual } from '../observabilidade/contexto';
import { LOGGER } from '../observabilidade/logger';
import { Metricas } from '../observabilidade/metricas';
import { CATALOGO_DE_PROBLEMAS, type Problema, tipoUri } from './problemas';

/** Converte qualquer erro em RFC 7807 com traceId. Nada de 500 genérico sem tipo. */
@Catch()
export class FiltroDeErros implements ExceptionFilter {
  constructor(
    @Inject(LOGGER) private readonly logger: Logger,
    private readonly metricas: Metricas,
  ) {}

  catch(erro: unknown, host: ArgumentsHost): void {
    if (host.getType() !== 'http') return;
    const ctx = host.switchToHttp();
    const req = ctx.getRequest<Request>();
    const res = ctx.getResponse<Response>();
    const problema = this.paraProblema(erro, req);
    this.metricas.errosHttp.inc({ type: problema.type, status: String(problema.status) });
    if (problema.status >= 500) {
      this.logger.error(
        { err: erro instanceof Error ? { name: erro.name, message: erro.message, stack: erro.stack } : String(erro), problem: problema.type },
        'erro na requisição',
      );
    }
    if (res.headersSent) {
      res.end();
      return;
    }
    if (problema.type === tipoUri('rate-limited') && typeof problema.retryAfterSeconds === 'number') {
      res.setHeader('Retry-After', String(problema.retryAfterSeconds));
    }
    if (problema.status === 401) res.setHeader('WWW-Authenticate', 'Bearer');
    res.status(problema.status).type('application/problem+json').send(JSON.stringify(problema));
  }

  paraProblema(erro: unknown, req: Pick<Request, 'originalUrl' | 'url'>): Problema {
    const instance = (req.originalUrl ?? req.url ?? '').split('?')[0] ?? '';
    const traceId = traceIdAtual();
    const montar = (tipo: TipoDeProblema, detail: string, extras: Record<string, unknown> = {}): Problema => ({
      type: tipoUri(tipo),
      title: CATALOGO_DE_PROBLEMAS[tipo].titulo,
      status: CATALOGO_DE_PROBLEMAS[tipo].status,
      detail,
      instance,
      traceId,
      ...extras,
    });

    if (erro instanceof ErroDeValidacao) {
      return montar('validation', erro.message, {
        errors: erro.campos.map((c) => ({ field: c.campo, message: c.mensagem })),
      });
    }
    if (erro instanceof ErroDeAplicacao) {
      return montar(erro.tipo, erro.message, erro.extras);
    }
    if (erro instanceof HttpException) {
      const status = erro.getStatus();
      const porStatus: Record<number, TipoDeProblema> = {
        400: 'bad-request',
        401: 'unauthenticated',
        403: 'forbidden',
        404: 'not-found',
        409: 'conflict',
        413: 'payload-too-large',
        415: 'bad-request',
        422: 'validation',
        429: 'rate-limited',
      };
      const tipo = porStatus[status] ?? (status >= 500 ? 'internal' : 'bad-request');
      const detalhe = status === 404 ? 'Rota não encontrada' : erro.message;
      return montar(tipo, detalhe);
    }
    // Erros de parser do Express (JSON malformado, corpo grande demais).
    const e = erro as { type?: string; status?: number };
    if (e?.type === 'entity.too.large' || e?.status === 413) {
      return montar('payload-too-large', 'O corpo da requisição excede o limite permitido');
    }
    if (e?.type === 'entity.parse.failed') {
      return montar('bad-request', 'Corpo JSON malformado');
    }
    return montar('internal', 'Ocorreu um erro inesperado. Informe o traceId ao suporte.');
  }
}
