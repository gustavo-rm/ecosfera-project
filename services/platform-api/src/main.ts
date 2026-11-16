import './instrumentacao';
import 'reflect-metadata';

import { NestFactory } from '@nestjs/core';
import type { NestExpressApplication } from '@nestjs/platform-express';

import { AppModule } from './app.module';
import { configurarAplicacao } from './configurar-aplicacao';
import { carregarConfiguracao, ErroDeConfiguracao } from './shared/config/configuracao';
import { criarLoggerRaiz, LoggerNest } from './shared/observabilidade/logger';
import { encerrarRastreamento } from './shared/observabilidade/rastreamento';

async function iniciar(): Promise<void> {
  let config;
  try {
    config = carregarConfiguracao();
  } catch (e) {
    if (e instanceof ErroDeConfiguracao) {
      process.stderr.write(`${e.message}\n`);
      process.exit(1);
    }
    throw e;
  }
  const logger = criarLoggerRaiz(config.LOG_LEVEL);
  const app = await NestFactory.create<NestExpressApplication>(AppModule.com(config), {
    bodyParser: false,
    logger: new LoggerNest(logger),
  });
  configurarAplicacao(app, config);
  await app.listen(config.PORT);
  logger.info({ port: config.PORT, env: config.NODE_ENV }, 'platform-api no ar');
  process.on('SIGTERM', () => void encerrarRastreamento());
}

void iniciar();
