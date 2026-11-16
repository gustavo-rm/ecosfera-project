import type { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Identidade, isolamento por escola e LGPD.
 * Aditiva: nenhuma coluna ou tabela da baseline é removida.
 * - papéis `researcher` e `platform_admin` (ADR 0008);
 * - usuário: menor, situação, preferências, pseudonimização;
 * - consentimento por finalidade, com versão do texto e revogação;
 * - textos legais versionados (placeholders para revisão jurídica);
 * - audit_log imutável (gatilho que recusa UPDATE/DELETE/TRUNCATE);
 * - identidades externas (OIDC/LTI), plataformas LTI e provedores OIDC;
 * - pedidos de titular e política de retenção (placeholders para o DPO).
 */
export class IdentityTenancyLgpd1794880000000 implements MigrationInterface {
  name = 'IdentityTenancyLgpd1794880000000';

  public async up(q: QueryRunner): Promise<void> {
    await q.query(
      `ALTER TYPE platform.user_role ADD VALUE IF NOT EXISTS 'researcher'`,
    );
    await q.query(
      `ALTER TYPE platform.user_role ADD VALUE IF NOT EXISTS 'platform_admin'`,
    );

    await q.query(`
      ALTER TABLE platform.app_user
        ADD COLUMN is_minor boolean NOT NULL DEFAULT false,
        ADD COLUMN status text NOT NULL DEFAULT 'active',
        ADD COLUMN preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN pseudonymized_at timestamptz,
        ADD CONSTRAINT app_user_status_check CHECK (status IN ('active', 'disabled', 'pseudonymized'))
    `);
    await q.query(
      `CREATE INDEX app_user_school_role_idx ON platform.app_user (school_id, role)`,
    );

    await q.query(`
      ALTER TABLE platform.consent
        ADD COLUMN purpose text NOT NULL DEFAULT 'platform_use',
        ADD COLUMN text_version text,
        ADD COLUMN revoked_at timestamptz,
        ADD COLUMN revoked_by_user_id uuid,
        ADD COLUMN school_id uuid,
        ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
        ADD CONSTRAINT consent_revoked_by_user_id_fkey FOREIGN KEY (revoked_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        ADD CONSTRAINT consent_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        ADD CONSTRAINT consent_status_check CHECK (status IN ('pending', 'granted', 'revoked')),
        ADD CONSTRAINT consent_purpose_check CHECK (purpose IN ('platform_use', 'learning_assessment', 'research'))
    `);
    await q.query(`
      ALTER TABLE platform.consent
        ADD CONSTRAINT consent_student_purpose_key UNIQUE (student_user_id, purpose)
    `);

    await q.query(`
      CREATE TABLE platform.consent_text (
        id             uuid NOT NULL DEFAULT gen_random_uuid(),
        purpose        text NOT NULL,
        version        text NOT NULL,
        locale         text NOT NULL DEFAULT 'pt-BR',
        body           text NOT NULL,
        review_status  text NOT NULL DEFAULT 'pending_legal_review',
        created_at     timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT consent_text_pkey PRIMARY KEY (id),
        CONSTRAINT consent_text_purpose_version_locale_key UNIQUE (purpose, version, locale),
        CONSTRAINT consent_text_review_status_check
          CHECK (review_status IN ('pending_legal_review', 'approved', 'retired'))
      )
    `);
    // Textos PLACEHOLDER. Não são texto jurídico: precisam de revisão do DPO e da assessoria jurídica.
    await q.query(`
      INSERT INTO platform.consent_text (purpose, version, body) VALUES
      ('platform_use', '0.1-placeholder',
       '[PLACEHOLDER — PENDENTE DE REVISÃO JURÍDICA E DO DPO] Autorizo o uso da plataforma ECOSFERA pelo estudante sob minha responsabilidade: conta, turma, planetas, missões e tutor. Finalidade: atividade pedagógica.'),
      ('learning_assessment', '0.1-placeholder',
       '[PLACEHOLDER — PENDENTE DE REVISÃO JURÍDICA E DO DPO] Autorizo o registro de evidências de aprendizagem geradas pelas ações do estudante no jogo, visíveis só para professores e coordenação da escola. Finalidade: acompanhamento pedagógico.'),
      ('research', '0.1-placeholder',
       '[PLACEHOLDER — PENDENTE DE REVISÃO JURÍDICA E DO DPO] Autorizo a inclusão, de forma anonimizada e sem dados que identifiquem o estudante, em conjuntos de dados para pesquisa educacional.')
    `);

    await q.query(`
      ALTER TABLE platform.audit_log
        ADD COLUMN school_id uuid,
        ADD COLUMN actor_service text,
        ADD COLUMN trace_id text,
        ADD COLUMN outcome text NOT NULL DEFAULT 'success',
        ADD CONSTRAINT audit_log_outcome_check CHECK (outcome IN ('success', 'denied', 'failure'))
    `);
    await q.query(
      `CREATE INDEX audit_log_school_created_idx ON platform.audit_log (school_id, created_at)`,
    );
    await q.query(
      `CREATE INDEX audit_log_action_idx ON platform.audit_log (action)`,
    );
    await q.query(`
      CREATE OR REPLACE FUNCTION platform.audit_log_immutable() RETURNS trigger
      LANGUAGE plpgsql AS $$
      BEGIN
        RAISE EXCEPTION 'platform.audit_log é imutável: % não é permitido', TG_OP
          USING ERRCODE = 'insufficient_privilege';
      END
      $$
    `);
    await q.query(`
      CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON platform.audit_log
        FOR EACH ROW EXECUTE FUNCTION platform.audit_log_immutable()
    `);
    await q.query(`
      CREATE TRIGGER audit_log_no_truncate
        BEFORE TRUNCATE ON platform.audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION platform.audit_log_immutable()
    `);

    await q.query(`
      CREATE TABLE platform.external_identity (
        id             uuid NOT NULL DEFAULT gen_random_uuid(),
        user_id        uuid NOT NULL,
        provider_kind  text NOT NULL,
        issuer         text NOT NULL,
        subject        text NOT NULL,
        created_at     timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT external_identity_pkey PRIMARY KEY (id),
        CONSTRAINT external_identity_user_id_fkey FOREIGN KEY (user_id)
          REFERENCES platform.app_user(id) ON DELETE CASCADE,
        CONSTRAINT external_identity_issuer_subject_key UNIQUE (issuer, subject),
        CONSTRAINT external_identity_provider_kind_check CHECK (provider_kind IN ('oidc', 'lti'))
      )
    `);
    await q.query(
      `CREATE INDEX external_identity_user_idx ON platform.external_identity (user_id)`,
    );

    await q.query(`
      CREATE TABLE platform.lti_platform (
        id              uuid NOT NULL DEFAULT gen_random_uuid(),
        school_id       uuid NOT NULL,
        issuer          text NOT NULL,
        client_id       text NOT NULL,
        deployment_id   text NOT NULL,
        auth_login_url  text NOT NULL,
        auth_token_url  text,
        jwks_url        text NOT NULL,
        created_at      timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT lti_platform_pkey PRIMARY KEY (id),
        CONSTRAINT lti_platform_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        CONSTRAINT lti_platform_issuer_client_deployment_key UNIQUE (issuer, client_id, deployment_id)
      )
    `);

    await q.query(`
      CREATE TABLE platform.oidc_provider (
        id                  uuid NOT NULL DEFAULT gen_random_uuid(),
        school_id           uuid NOT NULL,
        slug                text NOT NULL,
        issuer              text NOT NULL,
        client_id           text NOT NULL,
        client_secret_env   text,
        default_role        platform.user_role NOT NULL DEFAULT 'student',
        allow_provisioning  boolean NOT NULL DEFAULT false,
        created_at          timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT oidc_provider_pkey PRIMARY KEY (id),
        CONSTRAINT oidc_provider_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        CONSTRAINT oidc_provider_slug_key UNIQUE (slug)
      )
    `);

    await q.query(`
      CREATE TABLE platform.data_subject_request (
        id                    uuid NOT NULL DEFAULT gen_random_uuid(),
        school_id             uuid,
        subject_user_id       uuid NOT NULL,
        requested_by_user_id  uuid,
        kind                  text NOT NULL,
        status                text NOT NULL DEFAULT 'completed',
        details               jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at            timestamptz NOT NULL DEFAULT now(),
        completed_at          timestamptz,
        CONSTRAINT data_subject_request_pkey PRIMARY KEY (id),
        CONSTRAINT data_subject_request_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        CONSTRAINT data_subject_request_subject_user_id_fkey FOREIGN KEY (subject_user_id)
          REFERENCES platform.app_user(id) ON DELETE CASCADE,
        CONSTRAINT data_subject_request_requested_by_user_id_fkey FOREIGN KEY (requested_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        CONSTRAINT data_subject_request_kind_check CHECK (kind IN ('access', 'rectification', 'deletion')),
        CONSTRAINT data_subject_request_status_check CHECK (status IN ('pending', 'completed', 'rejected'))
      )
    `);

    await q.query(`
      CREATE TABLE platform.retention_policy (
        data_category   text NOT NULL,
        retention_days  integer NOT NULL,
        action          text NOT NULL,
        review_status   text NOT NULL DEFAULT 'pending_dpo_review',
        updated_at      timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT retention_policy_pkey PRIMARY KEY (data_category),
        CONSTRAINT retention_policy_days_check CHECK (retention_days > 0),
        CONSTRAINT retention_policy_action_check CHECK (action IN ('delete', 'pseudonymize'))
      )
    `);
    // Prazos PLACEHOLDER: decisão do DPO/jurídico. O mecanismo lê daqui; muda sem novo deploy.
    await q.query(`
      INSERT INTO platform.retention_policy (data_category, retention_days, action) VALUES
        ('evidence', 365, 'delete'),
        ('competency_estimate', 365, 'delete'),
        ('feedback', 365, 'delete'),
        ('assessment_after_consent_revocation', 30, 'delete'),
        ('export_objects', 7, 'delete'),
        ('research_dataset_objects', 30, 'delete'),
        ('disabled_accounts', 730, 'pseudonymize')
    `);
  }

  public async down(q: QueryRunner): Promise<void> {
    await q.query(`DROP TABLE IF EXISTS platform.retention_policy`);
    await q.query(`DROP TABLE IF EXISTS platform.data_subject_request`);
    await q.query(`DROP TABLE IF EXISTS platform.oidc_provider`);
    await q.query(`DROP TABLE IF EXISTS platform.lti_platform`);
    await q.query(`DROP TABLE IF EXISTS platform.external_identity`);
    await q.query(
      `DROP TRIGGER IF EXISTS audit_log_no_truncate ON platform.audit_log`,
    );
    await q.query(
      `DROP TRIGGER IF EXISTS audit_log_no_update_delete ON platform.audit_log`,
    );
    await q.query(`DROP FUNCTION IF EXISTS platform.audit_log_immutable()`);
    await q.query(`DROP INDEX IF EXISTS platform.audit_log_action_idx`);
    await q.query(`DROP INDEX IF EXISTS platform.audit_log_school_created_idx`);
    await q.query(`
      ALTER TABLE platform.audit_log
        DROP CONSTRAINT IF EXISTS audit_log_outcome_check,
        DROP COLUMN IF EXISTS outcome, DROP COLUMN IF EXISTS trace_id,
        DROP COLUMN IF EXISTS actor_service, DROP COLUMN IF EXISTS school_id
    `);
    await q.query(`DROP TABLE IF EXISTS platform.consent_text`);
    await q.query(`
      ALTER TABLE platform.consent
        DROP CONSTRAINT IF EXISTS consent_student_purpose_key,
        DROP CONSTRAINT IF EXISTS consent_purpose_check,
        DROP CONSTRAINT IF EXISTS consent_status_check,
        DROP CONSTRAINT IF EXISTS consent_school_id_fkey,
        DROP CONSTRAINT IF EXISTS consent_revoked_by_user_id_fkey,
        DROP COLUMN IF EXISTS updated_at, DROP COLUMN IF EXISTS school_id,
        DROP COLUMN IF EXISTS revoked_by_user_id, DROP COLUMN IF EXISTS revoked_at,
        DROP COLUMN IF EXISTS text_version, DROP COLUMN IF EXISTS purpose
    `);
    await q.query(`DROP INDEX IF EXISTS platform.app_user_school_role_idx`);
    await q.query(`
      ALTER TABLE platform.app_user
        DROP CONSTRAINT IF EXISTS app_user_status_check,
        DROP COLUMN IF EXISTS pseudonymized_at, DROP COLUMN IF EXISTS preferences,
        DROP COLUMN IF EXISTS status, DROP COLUMN IF EXISTS is_minor
    `);
    // Valores de enum não podem ser removidos no PostgreSQL sem recriar o tipo.
    // Mantidos de propósito (inofensivos); remoção exigiria migração destrutiva aprovada.
  }
}
