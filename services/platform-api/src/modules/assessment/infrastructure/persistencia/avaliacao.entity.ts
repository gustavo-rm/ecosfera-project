import { Check, Column, Entity, Index, JoinColumn, ManyToOne, PrimaryColumn, PrimaryGeneratedColumn, Unique } from 'typeorm';

import { AGORA, JSON_VAZIO, numerico, type Json } from '../../../../shared/database/colunas';

/** Modelo de LEITURA: o cálculo é do ai-sim-service; o platform-api só projeta (ADR 0013). */
@Entity({ name: 'cognitive_profile', schema: 'platform' })
@Unique('cognitive_profile_student_user_id_key', ['studentUserId'])
@Index('cognitive_profile_school_idx', ['schoolId'])
export class PerfilCognitivoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'cognitive_profile_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'cognitive_profile_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'cognitive_profile_school_id_fkey' })
  private readonly _escola?: unknown;
}

@Entity({ name: 'competency_estimate', schema: 'platform' })
@Unique('competency_estimate_cognitive_profile_id_competency_id_key', ['cognitiveProfileId', 'competencyId'])
export class EstimativaDeCompetenciaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'competency_estimate_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'cognitive_profile_id' })
  cognitiveProfileId: string;

  @ManyToOne('PerfilCognitivoEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'cognitive_profile_id', foreignKeyConstraintName: 'competency_estimate_cognitive_profile_id_fkey' })
  private readonly _perfil?: unknown;

  @Column({ type: 'uuid', name: 'competency_id' })
  competencyId: string;

  @ManyToOne('CompetenciaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'competency_id', foreignKeyConstraintName: 'competency_estimate_competency_id_fkey' })
  private readonly _competencia?: unknown;

  @Column({ type: 'numeric', precision: 5, scale: 4, default: 0, transformer: numerico })
  probability: number;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;

  @Column({ type: 'numeric', precision: 5, scale: 4, nullable: true, transformer: numerico })
  uncertainty: number | null;

  @Column({ type: 'integer', name: 'evidence_count', default: 0 })
  evidenceCount: number;

  @Column({ type: 'text', name: 'last_event_id', nullable: true })
  lastEventId: string | null;

  @Column({ type: 'timestamptz', name: 'last_event_at', nullable: true })
  lastEventAt: Date | null;

  @Column({ type: 'boolean', default: false })
  synthetic: boolean;
}

@Entity({ name: 'evidence', schema: 'platform' })
@Unique('evidence_event_id_key', ['eventId'])
@Index('evidence_student_competency_idx', ['studentUserId', 'competencyId', 'occurredAt'])
@Index('evidence_school_idx', ['schoolId', 'occurredAt'])
export class EvidenciaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'evidence_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'evidence_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'uuid', name: 'competency_id', nullable: true })
  competencyId: string | null;

  @ManyToOne('CompetenciaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'competency_id', foreignKeyConstraintName: 'evidence_competency_id_fkey' })
  private readonly _competencia?: unknown;

  @Column({ type: 'text' })
  type: string;

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  payload: Json;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'text', name: 'event_id', nullable: true })
  eventId: string | null;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'evidence_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'planet_id', nullable: true })
  planetId: string | null;

  @ManyToOne('PlanetaMetaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'planet_id', foreignKeyConstraintName: 'evidence_planet_id_fkey' })
  private readonly _planeta?: unknown;

  @Column({ type: 'uuid', name: 'bncc_skill_id', nullable: true })
  bnccSkillId: string | null;

  @ManyToOne('HabilidadeBnccEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'bncc_skill_id', foreignKeyConstraintName: 'evidence_bncc_skill_id_fkey' })
  private readonly _habilidade?: unknown;

  @Column({ type: 'text', default: 'ai-sim-service' })
  source: string;

  @Column({ type: 'boolean', default: false })
  synthetic: boolean;

  @Column({ type: 'timestamptz', name: 'occurred_at', default: AGORA })
  occurredAt: Date;
}

@Entity({ name: 'assessment', schema: 'platform' })
@Index('assessment_student_idx', ['studentUserId'])
@Check('assessment_kind_check', `kind IN ('pre_test', 'post_test', 'rubric')`)
export class AvaliacaoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'assessment_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'assessment_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'uuid', name: 'mission_id', nullable: true })
  missionId: string | null;

  @ManyToOne('MissaoEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'mission_id', foreignKeyConstraintName: 'assessment_mission_id_fkey' })
  private readonly _missao?: unknown;

  @Column({ type: 'numeric', precision: 5, scale: 2, nullable: true, transformer: numerico })
  score: number | null;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'text', default: 'rubric' })
  kind: 'pre_test' | 'post_test' | 'rubric';

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'assessment_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'competency_id', nullable: true })
  competencyId: string | null;

  @ManyToOne('CompetenciaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'competency_id', foreignKeyConstraintName: 'assessment_competency_id_fkey' })
  private readonly _competencia?: unknown;

  @Column({ type: 'uuid', name: 'recorded_by_user_id', nullable: true })
  recordedByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'recorded_by_user_id', foreignKeyConstraintName: 'assessment_recorded_by_user_id_fkey' })
  private readonly _registradoPor?: unknown;

  @Column({ type: 'jsonb', default: JSON_VAZIO })
  details: Json;
}

@Entity({ name: 'feedback', schema: 'platform' })
@Index('feedback_student_idx', ['studentUserId', 'createdAt'])
export class FeedbackEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'feedback_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'assessment_id', nullable: true })
  assessmentId: string | null;

  @ManyToOne('AvaliacaoEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'assessment_id', foreignKeyConstraintName: 'feedback_assessment_id_fkey' })
  private readonly _avaliacao?: unknown;

  /** Texto cifrado em repouso (AES-256-GCM): pode conter observação sensível sobre menor. */
  @Column({ type: 'text' })
  content: string;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'uuid', name: 'student_user_id', nullable: true })
  studentUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'feedback_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'uuid', name: 'author_user_id', nullable: true })
  authorUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'author_user_id', foreignKeyConstraintName: 'feedback_author_user_id_fkey' })
  private readonly _autor?: unknown;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'feedback_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'timestamptz', name: 'read_at', nullable: true })
  readAt: Date | null;
}

@Entity({ name: 'alert_config', schema: 'platform' })
@Check('alert_config_threshold_check', `mastery_threshold >= 0 AND mastery_threshold <= 1`)
export class ConfiguracaoDeAlertaEntity {
  @PrimaryColumn({ type: 'uuid', name: 'school_id', primaryKeyConstraintName: 'alert_config_pkey' })
  schoolId: string;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'alert_config_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'numeric', name: 'mastery_threshold', precision: 5, scale: 4, default: () => '0.4', transformer: numerico })
  masteryThreshold: number;

  @Column({ type: 'numeric', name: 'max_uncertainty', precision: 5, scale: 4, default: () => '0.35', transformer: numerico })
  maxUncertainty: number;

  @Column({ type: 'integer', name: 'min_evidence', default: 3 })
  minEvidence: number;

  @Column({ type: 'integer', name: 'inactivity_days', default: 14 })
  inactivityDays: number;

  @Column({ type: 'text', name: 'review_status', default: 'pending_pedagogical_review' })
  reviewStatus: string;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}

@Entity({ name: 'export_record', schema: 'platform' })
@Index('export_record_created_idx', ['createdAt'])
@Check('export_record_kind_check', `kind IN ('report', 'dataset')`)
@Check('export_record_format_check', `format IN ('pdf', 'csv', 'json')`)
export class RegistroDeExportacaoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'export_record_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'school_id', nullable: true })
  schoolId: string | null;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: true })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'export_record_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'requested_by_user_id', nullable: true })
  requestedByUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'requested_by_user_id', foreignKeyConstraintName: 'export_record_requested_by_user_id_fkey' })
  private readonly _solicitante?: unknown;

  @Column({ type: 'text' })
  kind: 'report' | 'dataset';

  @Column({ type: 'text' })
  format: 'pdf' | 'csv' | 'json';

  @Column({ type: 'text' })
  bucket: string;

  @Column({ type: 'text', name: 'object_key' })
  objectKey: string;

  @Column({ type: 'integer', name: 'size_bytes' })
  sizeBytes: number;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'purged_at', nullable: true })
  purgedAt: Date | null;
}
