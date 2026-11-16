import { Check, Column, Entity, Index, JoinColumn, ManyToOne, PrimaryGeneratedColumn, Unique } from 'typeorm';

import { AGORA, JSON_VAZIO, type Json } from '../../../../shared/database/colunas';
import { PAPEIS, type Papel } from '../../../../shared/kernel/papeis';

@Entity({ name: 'app_user', schema: 'platform' })
@Unique('app_user_email_key', ['email'])
@Index('app_user_school_role_idx', ['schoolId', 'role'])
@Check('app_user_status_check', `status IN ('active', 'disabled', 'pseudonymized')`)
export class UsuarioEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'app_user_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'app_user_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'text' })
  email: string;

  @Column({ type: 'text', name: 'password_hash' })
  passwordHash: string;

  @Column({ type: 'enum', enum: PAPEIS, enumName: 'user_role' })
  role: Papel;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;

  @Column({ type: 'boolean', name: 'is_minor', default: false })
  isMinor: boolean;

  @Column({ type: 'text', default: 'active' })
  status: 'active' | 'disabled' | 'pseudonymized';

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  preferences: Json;

  @Column({ type: 'timestamptz', name: 'pseudonymized_at', nullable: true })
  pseudonymizedAt: Date | null;
}
