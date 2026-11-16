import {
  Check,
  Column,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  PrimaryColumn,
  PrimaryGeneratedColumn,
  Unique,
} from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';
import { PAPEIS, type Papel } from '../../../../shared/kernel/papeis';

/** Identidade externa (OIDC/LTI) ligada a um usuário: chave (issuer, subject). */
@Entity({ name: 'external_identity', schema: 'platform' })
@Unique('external_identity_issuer_subject_key', ['issuer', 'subject'])
@Index('external_identity_user_idx', ['userId'])
@Check(
  'external_identity_provider_kind_check',
  `provider_kind IN ('oidc', 'lti')`,
)
export class IdentidadeExternaEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'external_identity_pkey',
  })
  id: string;

  @Column({ type: 'uuid', name: 'user_id' })
  userId: string;

  @ManyToOne('UsuarioEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'user_id',
    foreignKeyConstraintName: 'external_identity_user_id_fkey',
  })
  private readonly _usuario?: unknown;

  @Column({ type: 'text', name: 'provider_kind' })
  providerKind: 'oidc' | 'lti';

  @Column({ type: 'text' })
  issuer: string;

  @Column({ type: 'text' })
  subject: string;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}

/** Plataforma LTI 1.3 registrada por uma escola. */
@Entity({ name: 'lti_platform', schema: 'platform' })
@Unique('lti_platform_issuer_client_deployment_key', [
  'issuer',
  'clientId',
  'deploymentId',
])
export class PlataformaLtiEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'lti_platform_pkey',
  })
  id: string;

  @Column({ type: 'uuid', name: 'school_id' })
  schoolId: string;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'school_id',
    foreignKeyConstraintName: 'lti_platform_school_id_fkey',
  })
  private readonly _escola?: unknown;

  @Column({ type: 'text' })
  issuer: string;

  @Column({ type: 'text', name: 'client_id' })
  clientId: string;

  @Column({ type: 'text', name: 'deployment_id' })
  deploymentId: string;

  @Column({ type: 'text', name: 'auth_login_url' })
  authLoginUrl: string;

  @Column({ type: 'text', name: 'auth_token_url', nullable: true })
  authTokenUrl: string | null;

  @Column({ type: 'text', name: 'jwks_url' })
  jwksUrl: string;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}

/** Provedor OIDC de uma escola. O segredo do cliente fica no cofre/ambiente; aqui só o nome da variável. */
@Entity({ name: 'oidc_provider', schema: 'platform' })
@Unique('oidc_provider_slug_key', ['slug'])
export class ProvedorOidcEntity {
  @PrimaryGeneratedColumn('uuid', {
    primaryKeyConstraintName: 'oidc_provider_pkey',
  })
  id: string;

  @Column({ type: 'uuid', name: 'school_id' })
  schoolId: string;

  @ManyToOne('EscolaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'school_id',
    foreignKeyConstraintName: 'oidc_provider_school_id_fkey',
  })
  private readonly _escola?: unknown;

  @Column({ type: 'text' })
  slug: string;

  @Column({ type: 'text' })
  issuer: string;

  @Column({ type: 'text', name: 'client_id' })
  clientId: string;

  @Column({ type: 'text', name: 'client_secret_env', nullable: true })
  clientSecretEnv: string | null;

  @Column({
    type: 'enum',
    enum: PAPEIS,
    enumName: 'user_role',
    name: 'default_role',
    default: 'student',
  })
  defaultRole: Papel;

  @Column({ type: 'boolean', name: 'allow_provisioning', default: false })
  allowProvisioning: boolean;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}

/** Curso do LMS ↔ turma do ECOSFERA. */
@Entity({ name: 'lti_context', schema: 'platform' })
export class ContextoLtiEntity {
  @PrimaryColumn({
    type: 'uuid',
    name: 'platform_id',
    primaryKeyConstraintName: 'lti_context_pkey',
  })
  platformId: string;

  @ManyToOne('PlataformaLtiEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'platform_id',
    foreignKeyConstraintName: 'lti_context_platform_id_fkey',
  })
  private readonly _plataforma?: unknown;

  @PrimaryColumn({
    type: 'text',
    name: 'context_id',
    primaryKeyConstraintName: 'lti_context_pkey',
  })
  contextId: string;

  @Column({ type: 'uuid', name: 'class_id' })
  classId: string;

  @ManyToOne('TurmaEntity', { onDelete: 'CASCADE', nullable: false })
  @JoinColumn({
    name: 'class_id',
    foreignKeyConstraintName: 'lti_context_class_id_fkey',
  })
  private readonly _turma?: unknown;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}
