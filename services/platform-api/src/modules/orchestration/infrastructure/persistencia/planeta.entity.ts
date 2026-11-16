import { Check, Column, Entity, Index, JoinColumn, ManyToOne, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';

/** platform.planet_meta — referência do planeta para posse e vínculo. O estado é do ai-sim-service. */
@Entity({ name: 'planet_meta', schema: 'platform' })
@Index('planet_meta_owner_idx', ['ownerUserId'])
@Index('planet_meta_school_idx', ['schoolId'])
@Check('planet_meta_status_check', `status IN ('active', 'archived')`)
export class PlanetaMetaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'planet_meta_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'owner_user_id' })
  ownerUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'owner_user_id', foreignKeyConstraintName: 'planet_meta_owner_user_id_fkey' })
  private readonly _dono?: unknown;

  @Column({ type: 'uuid', name: 'mission_id', nullable: true })
  missionId: string | null;

  @ManyToOne('MissaoEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'mission_id', foreignKeyConstraintName: 'planet_meta_mission_id_fkey' })
  private readonly _missao?: unknown;

  @Column({ type: 'integer', name: 'current_era', default: 0 })
  currentEra: number;

  @Column({ type: 'text', nullable: true })
  seed: string | null;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'planet_meta_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'text', default: 'active' })
  status: 'active' | 'archived';
}

/** Respostas já dadas a pedidos com chave de idempotência (sync offline, reenvios). */
@Entity({ name: 'idempotency_record', schema: 'platform' })
export class RegistroDeIdempotenciaEntity {
  @PrimaryColumn({ type: 'text', primaryKeyConstraintName: 'idempotency_record_pkey' })
  scope: string;

  @PrimaryColumn({ type: 'text', primaryKeyConstraintName: 'idempotency_record_pkey' })
  key: string;

  @Column({ type: 'uuid', name: 'user_id', nullable: true })
  userId: string | null;

  @Column({ type: 'integer', name: 'status_code' })
  statusCode: number;

  @Column({ type: 'jsonb' })
  response: unknown;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}
