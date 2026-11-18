import type { LoggerService } from '@nestjs/common';
import pino, { type Logger } from 'pino';

import { contextoAtual, traceIdAtual } from './contexto';

/**
 * Logs estruturados em JSON, com traceId, sem PII e sem segredos.
 * A redação é a última linha de defesa: o código não deve logar PII.
 */
export const CAMINHOS_REDIGIDOS = [
  '*.password',
  '*.senha',
  '*.newPassword',
  '*.token',
  '*.accessToken',
  '*.refreshToken',
  '*.id_token',
  '*.authorization',
  '*.cookie',
  '*.email',
  '*.name',
  '*.nome',
  'req.headers.authorization',
  'req.headers.cookie',
  'req.headers["sec-websocket-protocol"]',
  'headers.authorization',
  'headers.cookie',
];

export function criarLoggerRaiz(nivel: string): Logger {
  return pino({
    level: nivel,
    base: { service: 'platform-api' },
    timestamp: pino.stdTimeFunctions.isoTime,
    redact: { paths: CAMINHOS_REDIGIDOS, censor: '[redigido]' },
    mixin() {
      const ctx = contextoAtual();
      const ator = ctx?.ator;
      return {
        traceId: traceIdAtual(),
        // Só identificadores opacos; nunca nome ou e-mail.
        ...(ator?.tipo === 'usuario' ? { actorId: ator.usuarioId } : {}),
        ...(ator?.tipo === 'servico' ? { actorService: ator.servico } : {}),
      };
    },
    formatters: { level: (label) => ({ level: label }) },
  });
}

/** Adaptador do pino para o LoggerService do Nest. */
export class LoggerNest implements LoggerService {
  constructor(private readonly raiz: Logger) {}
  log(message: unknown, context?: string) {
    this.raiz.info({ context }, String(message));
  }
  error(message: unknown, trace?: string, context?: string) {
    this.raiz.error({ context, stack: trace }, String(message));
  }
  warn(message: unknown, context?: string) {
    this.raiz.warn({ context }, String(message));
  }
  debug(message: unknown, context?: string) {
    this.raiz.debug({ context }, String(message));
  }
  verbose(message: unknown, context?: string) {
    this.raiz.trace({ context }, String(message));
  }
}

export const LOGGER = Symbol('Logger');
