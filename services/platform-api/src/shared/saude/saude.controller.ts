import { Controller, Header, Inject, Req, Res } from '@nestjs/common';
import type { Request, Response } from 'express';
import type { Redis } from 'ioredis';
import { DataSource } from 'typeorm';
import { z } from 'zod';

import { Autorizacao } from '../autorizacao/autorizacao.decorator';
import { CONFIGURACAO, type Configuracao } from '../config/configuracao';
import { definirEndpoint, Endpoint } from '../http/contrato';
import { ErroAcessoNegado, ErroDeDependencia } from '../kernel/erros';
import { Metricas } from '../observabilidade/metricas';
import { REDIS } from '../redis/redis';

const Saude = z.object({ status: z.literal('ok') }).meta({ id: 'Health' });
const Prontidao = z
  .object({
    status: z.literal('ready'),
    checks: z.object({ database: z.literal('ok'), redis: z.literal('ok') }),
    fakeAdapters: z
      .array(z.string())
      .describe('Adaptadores falsos ativos (vazio em produção)'),
  })
  .meta({ id: 'Readiness' });

export const ContratosDeSaude = {
  saude: definirEndpoint({
    operationId: 'health',
    metodo: 'GET',
    caminho: '/health',
    tag: 'operacao',
    resumo: 'Liveness: o processo está de pé',
    seguranca: 'publico',
    sucesso: 200,
    respostas: { 200: { descricao: 'Processo vivo', esquema: Saude } },
  }),
  prontidao: definirEndpoint({
    operationId: 'ready',
    metodo: 'GET',
    caminho: '/ready',
    tag: 'operacao',
    resumo: 'Readiness: banco e Redis respondem',
    seguranca: 'publico',
    sucesso: 200,
    respostas: {
      200: { descricao: 'Pronto para receber tráfego', esquema: Prontidao },
      503: { descricao: 'Dependência indisponível' },
    },
  }),
  metricas: definirEndpoint({
    operationId: 'metrics',
    metodo: 'GET',
    caminho: '/metrics',
    tag: 'operacao',
    resumo: 'Métricas Prometheus (exige METRICS_TOKEN em produção)',
    seguranca: 'publico',
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Métricas no formato texto do Prometheus',
        tipoConteudo: 'text/plain',
      },
      403: { descricao: 'Token de métricas ausente ou inválido' },
    },
  }),
};

@Controller()
export class SaudeController {
  constructor(
    private readonly ds: DataSource,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject('AVISO_DE_FAKES') private readonly fakes: string[],
    private readonly metricas: Metricas,
  ) {}

  @Endpoint(ContratosDeSaude.saude)
  @Autorizacao({ publico: true, motivo: 'sonda de liveness do orquestrador' })
  saude() {
    return { status: 'ok' as const };
  }

  @Endpoint(ContratosDeSaude.prontidao)
  @Autorizacao({ publico: true, motivo: 'sonda de readiness do orquestrador' })
  async prontidao() {
    try {
      await this.ds.query('SELECT 1');
    } catch {
      throw new ErroDeDependencia('PostgreSQL');
    }
    try {
      await this.redis.ping();
    } catch {
      throw new ErroDeDependencia('Redis');
    }
    return {
      status: 'ready' as const,
      checks: { database: 'ok' as const, redis: 'ok' as const },
      fakeAdapters: this.fakes,
    };
  }

  @Endpoint(ContratosDeSaude.metricas)
  @Autorizacao({
    publico: true,
    motivo: 'raspagem do Prometheus; protegida por METRICS_TOKEN',
  })
  @Header('Cache-Control', 'no-store')
  async metricasPrometheus(@Req() req: Request, @Res() res: Response) {
    const token = this.config.METRICS_TOKEN;
    if (token) {
      if (req.headers.authorization !== `Bearer ${token}`)
        throw new ErroAcessoNegado('Token de métricas inválido');
    } else if (this.config.NODE_ENV === 'production') {
      throw new ErroAcessoNegado(
        'Métricas desabilitadas: defina METRICS_TOKEN',
      );
    }
    res.setHeader('Content-Type', this.metricas.registro.contentType);
    res.send(await this.metricas.registro.metrics());
  }
}
