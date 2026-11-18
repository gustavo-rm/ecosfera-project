import type { Redis } from 'ioredis';
import type { Logger } from 'pino';

import type { Metricas } from '../observabilidade/metricas';
import type { EnvelopeDeEvento } from './eventos';
import type {
  AssessmentEventSource,
  EventPublisher,
  TratadorDeEvento,
} from './portas';

/** Publicador em Redis Streams: um campo `envelope` com o JSON do evento. */
export class PublicadorRedisStreams implements EventPublisher {
  constructor(
    private readonly redis: Redis,
    private readonly tamanhoMaximo = 100_000,
  ) {}
  async publicar(topico: string, e: EnvelopeDeEvento): Promise<string> {
    const id = await this.redis.xadd(
      topico,
      'MAXLEN',
      '~',
      String(this.tamanhoMaximo),
      '*',
      'envelope',
      JSON.stringify(e),
      'type',
      e.type,
    );
    return id ?? '';
  }
}

interface OpcoesDoConsumidor {
  stream: string;
  grupo: string;
  consumidor: string;
  maxEntregas: number;
  ociosoMs: number;
  bloqueioMs: number;
}

/**
 * Consumidor de grupo (XREADGROUP). ACK só depois do tratamento; falha deixa pendente,
 * que é reivindicado (XAUTOCLAIM) e reprocessado. Depois de N entregas, vai para `<stream>.dlq`.
 * O tratador é idempotente (processed_event), então reentrega não duplica efeito.
 */
export class FonteRedisStreams implements AssessmentEventSource {
  private ativo = false;
  private laco?: Promise<void>;

  constructor(
    private readonly comandos: Redis,
    private readonly bloqueante: Redis,
    private readonly logger: Logger,
    private readonly metricas: Metricas,
    private readonly o: OpcoesDoConsumidor,
  ) {}

  async iniciar(tratador: TratadorDeEvento): Promise<void> {
    try {
      await this.comandos.xgroup(
        'CREATE',
        this.o.stream,
        this.o.grupo,
        '0',
        'MKSTREAM',
      );
    } catch (e) {
      if (!String((e as Error).message).includes('BUSYGROUP')) throw e;
    }
    this.ativo = true;
    this.laco = this.rodar(tratador);
  }

  async parar(): Promise<void> {
    this.ativo = false;
    await this.laco?.catch(() => undefined);
  }

  /** Processa uma rodada (usado também pelos testes para drenar de forma determinística). */
  async rodada(tratador: TratadorDeEvento, bloquear: boolean): Promise<number> {
    await this.reivindicarPendentes(tratador);
    const args: (string | number)[] = [
      'GROUP',
      this.o.grupo,
      this.o.consumidor,
      'COUNT',
      50,
    ];
    if (bloquear) args.push('BLOCK', this.o.bloqueioMs);
    args.push('STREAMS', this.o.stream, '>');
    const r = (await (
      this.bloqueante as unknown as {
        xreadgroup: (...a: (string | number)[]) => Promise<unknown>;
      }
    ).xreadgroup(...args)) as [string, [string, string[]][]][] | null;
    if (!r) return 0;
    let n = 0;
    for (const [, mensagens] of r) {
      for (const [id, campos] of mensagens) {
        await this.tratar(tratador, id, campos);
        n++;
      }
    }
    return n;
  }

  private async rodar(tratador: TratadorDeEvento): Promise<void> {
    while (this.ativo) {
      try {
        await this.rodada(tratador, true);
      } catch (e) {
        if (!this.ativo) return;
        this.logger.error(
          { err: (e as Error).message, stream: this.o.stream },
          'falha no consumidor de eventos',
        );
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }

  private async tratar(
    tratador: TratadorDeEvento,
    id: string,
    campos: string[],
  ): Promise<void> {
    const i = campos.indexOf('envelope');
    let envelope: EnvelopeDeEvento | undefined;
    try {
      envelope = JSON.parse(campos[i + 1] ?? '') as EnvelopeDeEvento;
    } catch {
      envelope = undefined;
    }
    if (
      !envelope ||
      typeof envelope.eventId !== 'string' ||
      typeof envelope.type !== 'string'
    ) {
      await this.morta(id, campos, 'envelope inválido');
      return;
    }
    try {
      const resultado = await tratador(envelope);
      this.metricas.eventosConsumidos.inc({
        type: envelope.type,
        outcome: resultado,
      });
      await this.comandos.xack(this.o.stream, this.o.grupo, id);
    } catch (e) {
      this.metricas.eventosConsumidos.inc({
        type: envelope.type,
        outcome: 'error',
      });
      this.logger.warn(
        {
          err: (e as Error).message,
          eventId: envelope.eventId,
          type: envelope.type,
        },
        'evento não processado; ficará pendente',
      );
    }
  }

  private async reivindicarPendentes(
    tratador: TratadorDeEvento,
  ): Promise<void> {
    const pendentes = (await this.comandos.xpending(
      this.o.stream,
      this.o.grupo,
      'IDLE',
      this.o.ociosoMs,
      '-',
      '+',
      50,
    )) as [string, string, number, number][];
    for (const [id, , , entregas] of pendentes) {
      const reivindicado = (await this.comandos.xclaim(
        this.o.stream,
        this.o.grupo,
        this.o.consumidor,
        this.o.ociosoMs,
        id,
      )) as [string, string[]][];
      const msg = reivindicado[0];
      if (!msg) continue;
      if (entregas >= this.o.maxEntregas) {
        await this.morta(id, msg[1], `excedeu ${this.o.maxEntregas} entregas`);
        continue;
      }
      await this.tratar(tratador, id, msg[1]);
    }
  }

  private async morta(
    id: string,
    campos: string[],
    motivo: string,
  ): Promise<void> {
    await this.comandos.xadd(
      `${this.o.stream}.dlq`,
      '*',
      ...campos,
      'motivo',
      motivo,
      'origem',
      id,
    );
    await this.comandos.xack(this.o.stream, this.o.grupo, id);
    this.logger.error(
      { stream: this.o.stream, id, motivo },
      'evento movido para a fila de mensagens mortas',
    );
  }
}
