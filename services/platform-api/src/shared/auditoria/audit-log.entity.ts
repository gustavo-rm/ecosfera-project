import {
  Check,
  Column,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';

import { AGORA, JSON_VAZIO, type Json } from '../database/colunas';

/** platform.audit_log — imutável (gatilho no banco; ver migração 1794880000000). */
@Entity({ name: 'audit_log', schema: 'platform' })
@Index('audit_log_entity_idx', ['entity', 'entityId'])
@Index('audit_log_school_created_idx', ['schoolId', 'createdAt'])
@Index('audit_log_action_idx', ['action'])
@Check('audit_log_outcome_check', `outcome IN ('success', 'denied', 'failure')`)
export class AuditLogEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'audit_log_pkey',
  })
  id: string;

  @Column({ type: 'uuid', name: 'actor_user_id', nullable: true })
  actorUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({
    name: 'actor_user_id',
    foreignKeyConstraintName: 'audit_log_actor_user_id_fkey',
  })
  private readonly _ator?: unknown;

  @Column({ type: 'text' })
  action: string;

  @Column({ type: 'text' })
  entity: string;

  @Column({ type: 'text', name: 'entity_id', nullable: true })
  entityId: string | null;

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  data: Json;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @Column({ type: 'text', name: 'actor_service', nullable: true })
  actorService: string | null;

  @Column({ type: 'text', name: 'trace_id', nullable: true })
  traceId: string | null;

  @Column({ type: 'text', default: 'success' })
  outcome: string;
}
