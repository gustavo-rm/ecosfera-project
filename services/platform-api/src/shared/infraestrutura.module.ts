import { Global, Inject, type DynamicModule, type OnApplicationShutdown, type Provider } from '@nestjs/common';
import type { Redis } from 'ioredis';
import type { Logger } from 'pino';
import { DataSource } from 'typeorm';

import { ArmazenamentoFalso } from './armazenamento/fake';
import { OBJECT_STORAGE } from './armazenamento/portas';
import { ArmazenamentoS3 } from './armazenamento/s3';
import { Auditoria } from './auditoria/auditoria';
import { RegistroDeRegrasDePosse } from './autorizacao/registro-de-posse';
import { adaptadoresFalsosAtivos, CONFIGURACAO, type Configuracao } from './config/configuracao';
import { opcoesDoBanco } from './database/opcoes';
import { VinculosEscolaresSql } from './database/vinculos-sql';
import { GERADOR_DE_IDS, GeradorDeUuid } from './kernel/ids';
import { RELOGIO, RelogioDoSistema } from './kernel/relogio';
import { VINCULOS_ESCOLARES } from './kernel/vinculos';
import { criarLoggerRaiz, LOGGER } from './observabilidade/logger';
import { Metricas } from './observabilidade/metricas';
import { ChavesRedis } from './redis/chaves';
import { criarRedis, REDIS, REDIS_ASSINANTE, REDIS_BLOQUEANTE } from './redis/redis';
import { Cifrador } from './seguranca/cifrador';
import { LimitadorDeTaxa } from './seguranca/limitador-de-taxa';
import { Pseudonimizador } from './seguranca/pseudonimizador';

/** Fecha conexões no desligamento (SIGTERM): nada de estado preso no processo. */
class Encerramento implements OnApplicationShutdown {
  constructor(
    private readonly ds: DataSource,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(REDIS_ASSINANTE) private readonly assinante: Redis,
    @Inject(REDIS_BLOQUEANTE) private readonly bloqueante: Redis,
  ) {}
  async onApplicationShutdown(): Promise<void> {
    for (const r of [this.bloqueante, this.assinante, this.redis]) r.disconnect();
    if (this.ds.isInitialized) await this.ds.destroy();
  }
}

/** Providers transversais, disponíveis para os quatro contextos. */
@Global()
export class InfraestruturaModule {
  static com(config: Configuracao): DynamicModule {
    const providers: Provider[] = [
      { provide: CONFIGURACAO, useValue: config },
      { provide: LOGGER, useFactory: () => criarLoggerRaiz(config.LOG_LEVEL) },
      { provide: Metricas, useFactory: () => new Metricas(config.NODE_ENV !== 'test') },
      { provide: RELOGIO, useClass: RelogioDoSistema },
      { provide: GERADOR_DE_IDS, useClass: GeradorDeUuid },
      {
        provide: DataSource,
        useFactory: async () => {
          const ds = new DataSource(
            opcoesDoBanco({
              url: config.DATABASE_URL,
              ssl: config.DB_SSL,
              logging: config.DB_LOGGING,
              poolMax: config.DB_POOL_MAX,
            }),
          );
          return ds.initialize();
        },
      },
      { provide: REDIS, useFactory: () => criarRedis(config.REDIS_URL, 'comandos') },
      { provide: REDIS_ASSINANTE, useFactory: () => criarRedis(config.REDIS_URL, 'assinante') },
      { provide: REDIS_BLOQUEANTE, useFactory: () => criarRedis(config.REDIS_URL, 'bloqueante') },
      { provide: ChavesRedis, useValue: new ChavesRedis(config.REDIS_KEY_PREFIX) },
      { provide: Auditoria, inject: [DataSource], useFactory: (ds: DataSource) => new Auditoria(ds.manager) },
      { provide: Cifrador, useValue: new Cifrador(config.DATA_ENCRYPTION_KEY) },
      { provide: Pseudonimizador, useValue: new Pseudonimizador(config.PSEUDONYM_KEY) },
      {
        provide: LimitadorDeTaxa,
        inject: [REDIS, ChavesRedis],
        useFactory: (r: Redis, c: ChavesRedis) => new LimitadorDeTaxa(r, c),
      },
      RegistroDeRegrasDePosse,
      {
        provide: OBJECT_STORAGE,
        useFactory: () =>
          config.ADAPTER_STORAGE === 'fake'
            ? new ArmazenamentoFalso(config.FAKE_STORAGE_DIR, config.PSEUDONYM_KEY, config.PUBLIC_BASE_URL)
            : new ArmazenamentoS3({
                endpoint: config.S3_ENDPOINT,
                publicEndpoint: config.S3_PUBLIC_ENDPOINT,
                region: config.S3_REGION,
                accessKey: config.S3_ACCESS_KEY,
                secretKey: config.S3_SECRET_KEY,
                forcePathStyle: config.S3_FORCE_PATH_STYLE,
              }),
      },
      { provide: VINCULOS_ESCOLARES, inject: [DataSource], useFactory: (ds: DataSource) => new VinculosEscolaresSql(ds) },
      Encerramento,
      {
        provide: 'AVISO_DE_FAKES',
        inject: [LOGGER],
        useFactory: (logger: Logger) => {
          const fakes = adaptadoresFalsosAtivos(config);
          if (fakes.length > 0) {
            // Fakes honestos: anunciados em toda inicialização.
            logger.warn({ fakeAdapters: fakes }, `ADAPTADORES FALSOS ATIVOS: ${fakes.join(', ')} — não use em produção`);
          }
          return fakes;
        },
      },
    ];
    return {
      module: InfraestruturaModule,
      providers,
      exports: providers.filter((p) => p !== Encerramento),
    };
  }
}
