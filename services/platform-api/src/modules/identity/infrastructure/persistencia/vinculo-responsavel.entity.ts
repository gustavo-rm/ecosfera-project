import { Column, Entity, Index, JoinColumn, ManyToOne, PrimaryGeneratedColumn, Unique } from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';

/** platform.guardian — vínculo responsável ↔ aluno (RF-007). */
@Entity({ name: 'guardian', schema: 'platform' })
@Unique('guardian_guardian_user_id_student_user_id_key', ['guardianUserId', 'studentUserId'])
@Index('guardian_student_idx', ['studentUserId'])
export class VinculoResponsavelEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'guardian_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'guardian_user_id' })
  guardianUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'guardian_user_id', foreignKeyConstraintName: 'guardian_guardian_user_id_fkey' })
  private readonly _responsavel?: unknown;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'guardian_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}
