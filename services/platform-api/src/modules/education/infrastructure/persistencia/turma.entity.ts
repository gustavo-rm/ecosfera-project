import { Check, Column, Entity, Index, JoinColumn, ManyToOne, PrimaryGeneratedColumn, Unique } from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';

@Entity({ name: 'track', schema: 'platform' })
@Unique('track_level_key', ['level'])
@Check('track_level_check', `level IN ('fundamental_ii', 'medio', 'tecnico')`)
export class TrilhaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'track_pkey' })
  id: string;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'text', nullable: true })
  description: string | null;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'text', nullable: true })
  level: 'fundamental_ii' | 'medio' | 'tecnico' | null;
}

@Entity({ name: 'class', schema: 'platform' })
@Index('class_school_idx', ['schoolId'])
@Index('class_teacher_idx', ['teacherUserId'])
export class TurmaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'class_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'school_id' })
  schoolId: string;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'school_id', foreignKeyConstraintName: 'class_school_id_fkey' })
  private readonly _escola?: unknown;

  @Column({ type: 'uuid', name: 'teacher_user_id', nullable: true })
  teacherUserId: string | null;

  @ManyToOne('UsuarioEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'teacher_user_id', foreignKeyConstraintName: 'class_teacher_user_id_fkey' })
  private readonly _professor?: unknown;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'integer', nullable: true })
  year: number | null;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'uuid', name: 'track_id', nullable: true })
  trackId: string | null;

  @ManyToOne('TrilhaEntity', { onDelete: 'SET NULL', nullable: true })
  @JoinColumn({ name: 'track_id', foreignKeyConstraintName: 'class_track_id_fkey' })
  private readonly _trilha?: unknown;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}

@Entity({ name: 'enrollment', schema: 'platform' })
@Unique('enrollment_class_id_student_user_id_key', ['classId', 'studentUserId'])
@Index('enrollment_student_idx', ['studentUserId'])
export class MatriculaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'enrollment_pkey' })
  id: string;

  @Column({ type: 'uuid', name: 'class_id' })
  classId: string;

  @ManyToOne('TurmaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'class_id', foreignKeyConstraintName: 'enrollment_class_id_fkey' })
  private readonly _turma?: unknown;

  @Column({ type: 'uuid', name: 'student_user_id' })
  studentUserId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({ name: 'student_user_id', foreignKeyConstraintName: 'enrollment_student_user_id_fkey' })
  private readonly _aluno?: unknown;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}
