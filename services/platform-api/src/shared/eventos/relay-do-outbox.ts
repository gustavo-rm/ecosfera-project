import {
  Inject,
  Injectable,
  type OnApplicationBootstrap,
  type BeforeApplicationShutdown,
} from '@nestjs/common';
import type { Logger } from 'pino';
import { DataSource, IsNull } from 'typeorm';

import { CONFIGURACAO, type Configuracao } from '../config/configuracao';
import { LOGGER } from '../observabilidade/logger';
import { Metricas } from '../observabilidade/metricas';
import type { EnvelopeDeEvento } from './eventos';
import { EventoDeSaidaEntity } from './eventos.entity';
import { EVENT_PUBLISHER, type EventPublisher } from './portas';

/**
 * Publica o outbox no barramento. Seguro com várias réplicas: cada lote é travado
 * com FOR UPDATE SKIP LOCKED. Entrega "pelo menos uma vez": o consumidor deduplica por eventId.
 */
@Injectable()
export class RelayDoOutbox
  implements OnApplicationBootstrap, BeforeApplicationShutdown
{
  private timer?: NodeJS.Timeout;
  private rodando = false;
  private encerrando = false;
  private emAndamento?: Promise<number>;

  constructor(
    private readonly ds: DataSource,
    @Inject(EVENT_PUBLISHER) private readonly publicador: EventPublisher,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(LOGGER) private readonly logger: Logger,
    private readonly metricas: Metricas,
  ) {}

  onApplicationBootstrap(): void {
    if (!this.config.OUTBOX_RELAY_ENABLED) return;
    this.timer = setInterval(() => void this.drenar(), 500);
    this.timer.unref();
  }

  /**
   * Roda ANTES do fechamento das conexões (onApplicationShutdown): para o timer e espera
   * o lote em curso terminar, para não cortar uma transação no meio do desligamento.
   */
  async beforeApplicationShutdown(): Promise<void> {
    this.encerrando = true;
    if (this.timer) clearInterval(this.timer);
    await this.emAndamento?.catch(() => undefined);
  }

  drenar(): Promise<number> {
    if (this.encerrando || this.rodando) return Promise.resolve(0);
    this.emAndamento = this.executar();
    return this.emAndamento;
  }

  private async executar(): Promise<number> {
    this.rodando = true;
    try {
      return await this.ds.transaction(async (em) => {
        const lote = await em
          .getRepository(EventoDeSaidaEntity)
          .createQueryBuilder('o')
          .where('o.published_at IS NULL')
          .orderBy('o.occurred_at', 'ASC')
          .limit(100)
          .setLock('pessimistic_write')
          .setOnLocked('skip_locked')
          .getMany();
        for (const ev of lote) {
          const envelope: EnvelopeDeEvento = {
            eventId: ev.id,
            type: ev.eventType,
            version: 1,
            occurredAt: ev.occurredAt.toISOString(),
            traceId: ev.traceId ?? '',
            producer: 'platform-api',
            data: ev.payload,
          };
          try {
            await this.publicador.publicar(
              this.config.EVENTS_STREAM_PLATFORM,
              envelope,
            );
            await em.update(
              EventoDeSaidaEntity,
              { id: ev.id },
              { publishedAt: new Date(), attempts: ev.attempts + 1 },
            );
          } catch (e) {
            await em.update(
              EventoDeSaidaEntity,
              { id: ev.id },
              {
                attempts: ev.attempts + 1,
                lastError: (e as Error).message.slice(0, 500),
              },
            );
          }
        }
        const pendentes = await em
          .getRepository(EventoDeSaidaEntity)
          .countBy({ publishedAt: IsNull() });
        this.metricas.outboxPendente.set(pendentes);
        return lote.length;
      });
    } catch (e) {
      this.logger.error(
        { err: (e as Error).message },
        'falha ao drenar o outbox',
      );
      return 0;
    } finally {
      this.rodando = false;
    }
  }
}
