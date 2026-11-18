import {
  Check,
  Column,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
  Unique,
} from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';
import type { Finalidade } from '../../../../shared/kernel/finalidades';

/** platform.consent — estado atual do consentimento por (aluno, finalidade). Histórico no audit_log. */
@Entity({ name: 'consent', schema: 'platform' })
@Unique('consent_student_purpose_key', ['studentUserId', 'purpose'])
@Check('consent_status_check', `status IN ('pending', 'granted', 'revoked')`)
@Check(
  'consent_purpose_check',
  `purpose IN ('platform_use', 'learning_assessment', 'research')`,
)
export class ConsentimentoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'consent_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'student_user_id',
    foreignKeyConstraintName: 'consent_student_user_id_fkey',
  })
  private readonly _aluno?: unknown;

  @Column({ type: 'uuid', name: 'guardian_user_id', nullable: true })
  guardianUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({
    name: 'guardian_user_id',
    foreignKeyConstraintName: 'consent_guardian_user_id_fkey',
  })
  private readonly _responsavel?: unknown;

  @Column({ type: 'text', default: 'pending' })
  status: 'pending' | 'granted' | 'revoked';

  @Column({ type: 'timestamptz', name: 'granted_at', nullable: true })
  grantedAt: Date | null;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'text', default: 'platform_use' })
  purpose: Finalidade;

  @Column({ type: 'text', name: 'text_version', nullable: true })
  textVersion: string | null;

  @Column({ type: 'timestamptz', name: 'revoked_at', nullable: true })
  revokedAt: Date | null;

  @Column({ type: 'uuid', name: 'revoked_by_user_id', nullable: true })
  revokedByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({
    name: 'revoked_by_user_id',
    foreignKeyConstraintName: 'consent_revoked_by_user_id_fkey',
  })
  private readonly _revogadoPor?: unknown;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({
    name: 'school_id',
    foreignKeyConstraintName: 'consent_school_id_fkey',
  })
  private readonly _escola?: unknown;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}
