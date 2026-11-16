import { randomUUID } from 'node:crypto';

import type { NextFunction, Request, Response } from 'express';

import type { Configuracao } from '../config/configuracao';
import {
  ErroLimiteDeRequisicoes,
  ErroRequisicaoInvalida,
} from '../kernel/erros';
import {
  executarComContexto,
  novoTraceId,
  traceIdAtual,
} from '../observabilidade/contexto';
import type { Metricas } from '../observabilidade/metricas';
import type { LimitadorDeTaxa } from '../seguranca/limitador-de-taxa';
import type { FiltroDeErros } from './filtro-de-erros';

/** Abre o contexto da requisição (traceId) e devolve X-Trace-Id. */
export function middlewareDeContexto(
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  executarComContexto({ traceId: novoTraceId() }, () => {
    const traceId = traceIdAtual();
    res.setHeader('X-Trace-Id', traceId);
    res.setHeader('X-Request-Id', randomUUID());
    next();
  });
}

/** Mede latência por rota-modelo (sem ids na métrica). */
export function middlewareDeMetricas(metricas: Metricas) {
  return (req: Request, res: Response, next: NextFunction) => {
    const fim = metricas.duracaoHttp.startTimer();
    res.on('finish', () => {
      const rota =
        (req.route as { path?: string } | undefined)?.path ?? 'nao_roteada';
      fim({
        method: req.method,
        route: `${req.baseUrl ?? ''}${rota}`,
        status: String(res.statusCode),
      });
    });
    next();
  };
}

function responderProblema(
  filtro: FiltroDeErros,
  erro: unknown,
  req: Request,
  res: Response,
) {
  const p = filtro.paraProblema(erro, req);
  if (typeof p.retryAfterSeconds === 'number')
    res.setHeader('Retry-After', String(p.retryAfterSeconds));
  res.status(p.status).type('application/problem+json').send(JSON.stringify(p));
}

/** TLS obrigatório: atrás de proxy, exige X-Forwarded-Proto=https (RNF-007). */
export function middlewareHttpsObrigatorio(
  config: Configuracao,
  filtro: FiltroDeErros,
) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!config.REQUIRE_HTTPS) return next();
    if (/\/(health|ready)$/.test(req.path)) return next(); // sondas internas do orquestrador
    if (req.secure) return next();
    responderProblema(
      filtro,
      new ErroRequisicaoInvalida('HTTPS é obrigatório'),
      req,
      res,
    );
  };
}

/** Limite global por IP (proteção contra abuso). Limites mais finos ficam nos casos de uso de auth. */
export function middlewareLimitePorIp(
  config: Configuracao,
  limitador: LimitadorDeTaxa,
  filtro: FiltroDeErros,
) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (/\/(health|ready|metrics)$/.test(req.path)) return next();
    limitador
      .consumir(
        'ip',
        req.ip ?? 'desconhecido',
        config.RATE_LIMIT_IP_PER_MINUTE,
        60,
      )
      .then((r) => {
        if (r.permitido) return next();
        responderProblema(
          filtro,
          new ErroLimiteDeRequisicoes(r.tentarEmSegundos),
          req,
          res,
        );
      })
      .catch(next);
  };
}
