import {
  Check,
  Column,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryColumn,
  PrimaryGeneratedColumn,
} from 'typeorm';

import {
  AGORA,
  JSON_VAZIO,
  type Json,
} from '../../../../shared/database/colunas';

/** Pedido do titular (acesso, correção, exclusão) — RNF-012. */
@Entity({ name: 'data_subject_request', schema: 'platform' })
@Check(
  'data_subject_request_kind_check',
  `kind IN ('access', 'rectification', 'deletion')`,
)
@Check(
  'data_subject_request_status_check',
  `status IN ('pending', 'completed', 'rejected')`,
)
export class PedidoDeTitularEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'data_subject_request_pkey',
  })
  id: string;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({
    name: 'school_id',
    foreignKeyConstraintName: 'data_subject_request_school_id_fkey',
  })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'subject_user_id' })
  subjectUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'subject_user_id',
    foreignKeyConstraintName: 'data_subject_request_subject_user_id_fkey',
  })
  private readonly _titular?: unknown;

  @Column({ type: 'uuid', name: 'requested_by_user_id', nullable: true })
  requestedByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({
    name: 'requested_by_user_id',
    foreignKeyConstraintName: 'data_subject_request_requested_by_user_id_fkey',
  })
  private readonly _solicitante?: unknown;

  @Column({ type: 'text' })
  kind: 'access' | 'rectification' | 'deletion';

  @Column({ type: 'text', default: 'completed' })
  status: 'pending' | 'completed' | 'rejected';

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  details: Json;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'completed_at', nullable: true })
  completedAt: Date | null;
}

/** Política de retenção por categoria de dado — prazos placeholder do DPO. */
@Entity({ name: 'retention_policy', schema: 'platform' })
@Check('retention_policy_days_check', `retention_days > 0`)
@Check('retention_policy_action_check', `action IN ('delete', 'pseudonymize')`)
export class PoliticaDeRetencaoEntity {
  @PrimaryColumn({
    type: 'text',
    name: 'data_category',
    primaryKeyConstraintName: 'retention_policy_pkey',
  })
  dataCategory: string;

  @Column({ type: 'integer', name: 'retention_days' })
  retentionDays: number;

  @Column({ type: 'text' })
  action: 'delete' | 'pseudonymize';

  @Column({
    type: 'text',
    name: 'review_status',
    default: 'pending_dpo_review',
  })
  reviewStatus: string;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}
