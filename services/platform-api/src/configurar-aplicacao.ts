import type { INestApplication } from '@nestjs/common';
import type { NestExpressApplication } from '@nestjs/platform-express';
import cookieParser from 'cookie-parser';
import express from 'express';
import helmet from 'helmet';

import type { Configuracao } from './shared/config/configuracao';
import { PREFIXO_API } from './shared/http/contrato';
import { FiltroDeErros } from './shared/http/filtro-de-erros';
import {
  middlewareDeContexto,
  middlewareDeMetricas,
  middlewareHttpsObrigatorio,
  middlewareLimitePorIp,
} from './shared/http/middlewares';
import { Metricas } from './shared/observabilidade/metricas';
import { LimitadorDeTaxa } from './shared/seguranca/limitador-de-taxa';

/** Configuração HTTP única, usada pelo main.ts e pelos testes de integração. */
export function configurarAplicacao(app: INestApplication, config: Configuracao): void {
  const exp = app as NestExpressApplication;
  const filtro = app.get(FiltroDeErros);
  if (config.TRUST_PROXY) exp.set('trust proxy', 1);
  exp.disable('x-powered-by');
  app.setGlobalPrefix(PREFIXO_API);
  app.use(middlewareDeContexto);
  app.use(middlewareDeMetricas(app.get(Metricas)));
  app.use(
    helmet({
      contentSecurityPolicy: { directives: { defaultSrc: ["'self'"], scriptSrc: ["'self'"], styleSrc: ["'self'", "'unsafe-inline'"] } },
      hsts: config.REQUIRE_HTTPS ? { maxAge: 31536000, includeSubDomains: true } : false,
      crossOriginResourcePolicy: { policy: 'same-site' },
    }),
  );
  app.use(middlewareHttpsObrigatorio(config, filtro));
  app.use(middlewareLimitePorIp(config, app.get(LimitadorDeTaxa), filtro));
  app.use(express.json({ limit: config.BODY_LIMIT_BYTES }));
  app.use(express.urlencoded({ extended: false, limit: config.BODY_LIMIT_BYTES }));
  app.use(cookieParser());
  app.enableCors({
    origin: config.CORS_ORIGINS.length > 0 ? config.CORS_ORIGINS : false,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allowedHeaders: ['Authorization', 'Content-Type', 'X-Refresh-Transport', 'Idempotency-Key', 'traceparent'],
    exposedHeaders: ['X-Trace-Id', 'Retry-After'],
    maxAge: 600,
  });
  app.enableShutdownHooks();
}
