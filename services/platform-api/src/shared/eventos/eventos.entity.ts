import {
  Column,
  Entity,
  Index,
  PrimaryColumn,
  PrimaryGeneratedColumn,
} from 'typeorm';

import { AGORA, type Json } from '../database/colunas';

/** Outbox transacional: o evento nasce na mesma transação do fato e é publicado depois. */
@Entity({ name: 'outbox_event', schema: 'platform' })
@Index('outbox_event_pending_idx', ['publishedAt', 'occurredAt'])
export class EventoDeSaidaEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'outbox_event_pkey',
  })
  id: string;

  @Column({ type: 'text', name: 'event_type' })
  eventType: string;

  @Column({ type: 'text', name: 'aggregate_id', nullable: true })
  aggregateId: string | null;

  @Column({ type: 'jsonb' })
  payload: Json;

  @Column({ type: 'text', name: 'trace_id', nullable: true })
  traceId: string | null;

  @Column({ type: 'timestamptz', name: 'occurred_at', default: AGORA })
  occurredAt: Date;

  @Column({ type: 'timestamptz', name: 'published_at', nullable: true })
  publishedAt: Date | null;

  @Column({ type: 'integer', default: 0 })
  attempts: number;

  @Column({ type: 'text', name: 'last_error', nullable: true })
  lastError: string | null;
}

/** Eventos já consumidos (idempotência do consumidor). */
@Entity({ name: 'processed_event', schema: 'platform' })
export class EventoProcessadoEntity {
  @PrimaryColumn({
    type: 'text',
    name: 'event_id',
    primaryKeyConstraintName: 'processed_event_pkey',
  })
  eventId: string;

  @Column({ type: 'text', name: 'event_type' })
  eventType: string;

  @Column({ type: 'text' })
  stream: string;

  @Column({ type: 'text' })
  outcome: string;

  @Column({ type: 'timestamptz', name: 'processed_at', default: AGORA })
  processedAt: Date;
}
