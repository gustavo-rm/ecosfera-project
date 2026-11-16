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

export type EstadoDeValidacao = 'pending_validation' | 'validated' | 'rejected';

@Entity({ name: 'competency', schema: 'platform' })
@Unique('competency_code_key', ['code'])
@Check(
  'competency_validation_status_check',
  `validation_status IN ('pending_validation', 'validated', 'rejected')`,
)
export class CompetenciaEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'competency_pkey',
  })
  id: string;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'text', nullable: true })
  description: string | null;

  @Column({ type: 'text', nullable: true })
  code: string | null;

  @Column({
    type: 'text',
    name: 'general_competencies',
    array: true,
    default: [],
  })
  generalCompetencies: string[];

  @Column({
    type: 'text',
    name: 'validation_status',
    default: 'pending_validation',
  })
  validationStatus: EstadoDeValidacao;

  @Column({ type: 'text', name: 'catalog_version', default: '2026.0-draft' })
  catalogVersion: string;
}

@Entity({ name: 'bncc_skill', schema: 'platform' })
@Unique('bncc_skill_code_key', ['code'])
@Check(
  'bncc_skill_validation_status_check',
  `validation_status IN ('pending_validation', 'validated', 'rejected')`,
)
@Check('bncc_skill_stage_check', `stage IN ('fundamental', 'medio', 'tecnico')`)
export class HabilidadeBnccEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'bncc_skill_pkey',
  })
  id: string;

  @Column({ type: 'text' })
  code: string;

  @Column({ type: 'text' })
  description: string;

  @Column({ type: 'uuid', name: 'competency_id', nullable: true })
  competencyId: string | null;

  @ManyToOne('CompetenciaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({
    name: 'competency_id',
    foreignKeyConstraintName: 'bncc_skill_competency_id_fkey',
  })
  private readonly _competencia?: unknown;

  @Column({ type: 'text', nullable: true })
  component: string | null;

  @Column({ type: 'text', nullable: true })
  theme: string | null;

  @Column({ type: 'text', nullable: true })
  stage: 'fundamental' | 'medio' | 'tecnico' | null;

  @Column({
    type: 'text',
    name: 'validation_status',
    default: 'pending_validation',
  })
  validationStatus: EstadoDeValidacao;

  @Column({ type: 'text', name: 'catalog_version', default: '2026.0-draft' })
  catalogVersion: string;

  @Column({ type: 'boolean', default: true })
  active: boolean;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}
