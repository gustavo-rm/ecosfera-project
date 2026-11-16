import { Module, type OnModuleInit } from '@nestjs/common';
import type { Redis } from 'ioredis';
import type { Logger } from 'pino';

import { RegistroDeRegrasDePosse } from '../../shared/autorizacao/registro-de-posse';
import { CONFIGURACAO, type Configuracao } from '../../shared/config/configuracao';
import { ASSESSMENT_EVENT_SOURCE, EVENT_PUBLISHER } from '../../shared/eventos/portas';
import { FonteRedisStreams, PublicadorRedisStreams } from '../../shared/eventos/redis-streams';
import { RelayDoOutbox } from '../../shared/eventos/relay-do-outbox';
import { LOGGER } from '../../shared/observabilidade/logger';
import { Metricas } from '../../shared/observabilidade/metricas';
import { ChavesRedis } from '../../shared/redis/chaves';
import { REDIS, REDIS_BLOQUEANTE } from '../../shared/redis/redis';
import { EducationModule } from '../education/education.module';
import { IdentityModule } from '../identity/identity.module';
import { ServicoDeTokens } from '../identity/infrastructure/tokens';
import { ServicoDeIdempotencia } from './application/idempotencia';
import { ServicoDePlanetas } from './application/planetas.service';
import { ServicoDeTutor } from './application/tutor.service';
import { decidirAcessoAoPlaneta } from './domain/planeta';
import { PUBLICADOR_DO_PLANETA, type PublicadorDoPlaneta, SIMULATION_GATEWAY, TUTOR_GATEWAY } from './domain/portas';
import { SimulacaoHttp, TutorHttp } from './infrastructure/adaptadores-http';
import { ClienteHttpDoServico } from './infrastructure/cliente-http';
import { GatewayDeTempoReal } from './infrastructure/gateway-de-tempo-real';
import { PublicadorRedisDoPlaneta } from './infrastructure/publicador-do-planeta';
import { SimulacaoFalsa } from './infrastructure/simulacao-falsa';
import { TutorFalso } from './infrastructure/tutor-falso';
import { IaController } from './interface/ia.controller';
import { PlanetasController } from './interface/planetas.controller';

function cliente(c: Configuracao, m: Metricas, nome: string): ClienteHttpDoServico {
  return new ClienteHttpDoServico(
    {
      baseUrl: c.AI_SIM_BASE_URL ?? 'http://ai-sim-service.invalid',
      timeoutMs: c.AI_SIM_TIMEOUT_MS,
      repeticoes: c.AI_SIM_RETRIES,
      nomeDaDependencia: nome,
      token: () => ServicoDeTokens.emitirTokenDeServico(c.SERVICE_TOKEN_SECRET, 'platform-api', 120),
    },
    m,
  );
}

/** Contexto orchestration: gateway de simulação e tutor, tempo real e barramento de eventos. */
@Module({
  imports: [IdentityModule, EducationModule],
  controllers: [PlanetasController, IaController],
  providers: [
    {
      provide: PUBLICADOR_DO_PLANETA,
      inject: [REDIS, ChavesRedis, CONFIGURACAO],
      useFactory: (r: Redis, ch: ChavesRedis, c: Configuracao) => new PublicadorRedisDoPlaneta(r, ch, c.WS_REPLAY_SIZE),
    },
    {
      provide: SIMULATION_GATEWAY,
      inject: [CONFIGURACAO, REDIS, ChavesRedis, PUBLICADOR_DO_PLANETA, LOGGER, Metricas],
      useFactory: (c: Configuracao, r: Redis, ch: ChavesRedis, p: PublicadorDoPlaneta, l: Logger, m: Metricas) =>
        c.ADAPTER_SIMULATION === 'fake' ? new SimulacaoFalsa(r, ch, p, l, c.EVENTS_STREAM_ASSESSMENT) : new SimulacaoHttp(cliente(c, m, 'ai-sim-service')),
    },
    {
      provide: TUTOR_GATEWAY,
      inject: [CONFIGURACAO, LOGGER, Metricas],
      useFactory: (c: Configuracao, l: Logger, m: Metricas) => (c.ADAPTER_TUTOR === 'fake' ? new TutorFalso(l) : new TutorHttp(cliente(c, m, 'tutor'))),
    },
    { provide: EVENT_PUBLISHER, inject: [REDIS], useFactory: (r: Redis) => new PublicadorRedisStreams(r) },
    {
      provide: ASSESSMENT_EVENT_SOURCE,
      inject: [REDIS, REDIS_BLOQUEANTE, LOGGER, Metricas, CONFIGURACAO],
      useFactory: (r: Redis, b: Redis, l: Logger, m: Metricas, c: Configuracao) =>
        new FonteRedisStreams(r, b, l, m, {
          stream: c.EVENTS_STREAM_ASSESSMENT,
          grupo: c.EVENTS_CONSUMER_GROUP,
          consumidor: `${c.EVENTS_CONSUMER_GROUP}-${process.pid}`,
          maxEntregas: 5,
          ociosoMs: 30_000,
          bloqueioMs: 1000,
        }),
    },
    RelayDoOutbox,
    ServicoDeIdempotencia,
    ServicoDePlanetas,
    ServicoDeTutor,
    GatewayDeTempoReal,
  ],
  exports: [ServicoDePlanetas, ASSESSMENT_EVENT_SOURCE, EVENT_PUBLISHER, RelayDoOutbox, GatewayDeTempoReal, SIMULATION_GATEWAY, TUTOR_GATEWAY],
})
export class OrchestrationModule implements OnModuleInit {
  constructor(
    private readonly registro: RegistroDeRegrasDePosse,
    private readonly planetas: ServicoDePlanetas,
  ) {}

  onModuleInit(): void {
    for (const intencao of ['ler', 'agir'] as const) {
      this.registro.registrar(`planeta:${intencao}`, async (ator, id) => decidirAcessoAoPlaneta(ator, await this.planetas.fatos(ator, id), intencao));
    }
  }
}
