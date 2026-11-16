import { Check, Column, Entity, Index, JoinColumn, ManyToOne, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';

import { AGORA, JSON_VAZIO, type Json } from '../../../../shared/database/colunas';

@Entity({ name: 'mission', schema: 'platform' })
@Index('mission_school_idx', ['schoolId'])
@Check('mission_status_check', `status IN ('draft', 'published', 'archived')`)
export class MissaoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'mission_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'track_id' })
  trackId: string;

  @ManyToOne('TrilhaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'track_id', foreignKeyConstraintName: 'mission_track_id_fkey' })
  private readonly _trilha?: unknown;

  @Column({ type: 'text' })
  title: string;

  @Column({ type: 'text', nullable: true })
  description: string | null;

  @Column({ type: 'integer', name: 'order_index', default: 0 })
  orderIndex: number;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'mission_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'created_by_user_id', nullable: true })
  createdByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'created_by_user_id', foreignKeyConstraintName: 'mission_created_by_user_id_fkey' })
  private readonly _autor?: unknown;

  @Column({ type: 'text', nullable: true })
  objective: string | null;

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  parameters: Json;

  @Column({ type: 'text', default: 'draft' })
  status: 'draft' | 'published' | 'archived';

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}

@Entity({ name: 'mission_bncc', schema: 'platform' })
export class MissaoHabilidadeEntity {
  @PrimaryColumn({ type: 'uuid', name: 'mission_id', primaryKeyConstraintName: 'mission_bncc_pkey' })
  missionId: string;

  @ManyToOne('MissaoEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'mission_id', foreignKeyConstraintName: 'mission_bncc_mission_id_fkey' })
  private readonly _missao?: unknown;

  @PrimaryColumn({ type: 'uuid', name: 'bncc_skill_id', primaryKeyConstraintName: 'mission_bncc_pkey' })
  bnccSkillId: string;

  @ManyToOne('HabilidadeBnccEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'bncc_skill_id', foreignKeyConstraintName: 'mission_bncc_bncc_skill_id_fkey' })
  private readonly _habilidade?: unknown;
}

@Entity({ name: 'mission_assignment', schema: 'platform' })
@Index('mission_assignment_class_idx', ['classId'])
export class PublicacaoDeMissaoEntity {
  @PrimaryColumn({ type: 'uuid', name: 'mission_id', primaryKeyConstraintName: 'mission_assignment_pkey' })
  missionId: string;

  @ManyToOne('MissaoEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'mission_id', foreignKeyConstraintName: 'mission_assignment_mission_id_fkey' })
  private readonly _missao?: unknown;

  @PrimaryColumn({ type: 'uuid', name: 'class_id', primaryKeyConstraintName: 'mission_assignment_pkey' })
  classId: string;

  @ManyToOne('TurmaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'class_id', foreignKeyConstraintName: 'mission_assignment_class_id_fkey' })
  private readonly _turma?: unknown;

  @Column({ type: 'uuid', name: 'assigned_by_user_id', nullable: true })
  assignedByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'assigned_by_user_id', foreignKeyConstraintName: 'mission_assignment_assigned_by_user_id_fkey' })
  private readonly _autor?: unknown;

  @Column({ type: 'timestamptz', name: 'published_at', default: AGORA })
  publishedAt: Date;
}
