import type { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Avaliação (modelo de leitura) e orquestração.
 * - evidence / competency_estimate / cognitive_profile: colunas para projeção idempotente
 *   (id do evento), rastreabilidade e isolamento por escola (ADR 0013);
 * - assessment: tipo (pré/pós-teste, rubrica) para RF-074/075;
 * - feedback: passa a poder existir sem avaliação, dirigido ao aluno (RF-067);
 * - planet_meta: escola e situação; alert_config: limiares por escola (placeholder pedagógico);
 * - processed_event, outbox_event, idempotency_record, export_record.
 * Única alteração de restrição da baseline: feedback.assessment_id deixa de ser NOT NULL
 * (afrouxamento, não destrutivo).
 */
export class AssessmentOrchestration1794880200000 implements MigrationInterface {
  name = 'AssessmentOrchestration1794880200000';

  public async up(q: QueryRunner): Promise<void> {
    await q.query(`
      ALTER TABLE platform.planet_meta
        ADD COLUMN school_id uuid,
        ADD COLUMN status text NOT NULL DEFAULT 'active',
        ADD CONSTRAINT planet_meta_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        ADD CONSTRAINT planet_meta_status_check CHECK (status IN ('active', 'archived'))
    `);
    await q.query(
      `CREATE INDEX planet_meta_owner_idx ON platform.planet_meta (owner_user_id)`,
    );
    await q.query(
      `CREATE INDEX planet_meta_school_idx ON platform.planet_meta (school_id)`,
    );

    await q.query(`
      ALTER TABLE platform.evidence
        ADD COLUMN event_id text,
        ADD COLUMN school_id uuid,
        ADD COLUMN planet_id uuid,
        ADD COLUMN bncc_skill_id uuid,
        ADD COLUMN source text NOT NULL DEFAULT 'ai-sim-service',
        ADD COLUMN synthetic boolean NOT NULL DEFAULT false,
        ADD COLUMN occurred_at timestamptz NOT NULL DEFAULT now(),
        ADD CONSTRAINT evidence_event_id_key UNIQUE (event_id),
        ADD CONSTRAINT evidence_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        ADD CONSTRAINT evidence_planet_id_fkey FOREIGN KEY (planet_id)
          REFERENCES platform.planet_meta(id) ON DELETE SET NULL,
        ADD CONSTRAINT evidence_bncc_skill_id_fkey FOREIGN KEY (bncc_skill_id)
          REFERENCES platform.bncc_skill(id) ON DELETE SET NULL
    `);
    await q.query(
      `CREATE INDEX evidence_student_competency_idx ON platform.evidence (student_user_id, competency_id, occurred_at)`,
    );
    await q.query(
      `CREATE INDEX evidence_school_idx ON platform.evidence (school_id, occurred_at)`,
    );

    await q.query(`
      ALTER TABLE platform.cognitive_profile
        ADD COLUMN school_id uuid,
        ADD CONSTRAINT cognitive_profile_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE
    `);
    await q.query(
      `CREATE INDEX cognitive_profile_school_idx ON platform.cognitive_profile (school_id)`,
    );

    await q.query(`
      ALTER TABLE platform.competency_estimate
        ADD COLUMN uncertainty numeric(5,4),
        ADD COLUMN evidence_count integer NOT NULL DEFAULT 0,
        ADD COLUMN last_event_id text,
        ADD COLUMN last_event_at timestamptz,
        ADD COLUMN synthetic boolean NOT NULL DEFAULT false
    `);

    await q.query(`
      ALTER TABLE platform.assessment
        ADD COLUMN kind text NOT NULL DEFAULT 'rubric',
        ADD COLUMN school_id uuid,
        ADD COLUMN competency_id uuid,
        ADD COLUMN recorded_by_user_id uuid,
        ADD COLUMN details jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD CONSTRAINT assessment_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        ADD CONSTRAINT assessment_competency_id_fkey FOREIGN KEY (competency_id)
          REFERENCES platform.competency(id) ON DELETE SET NULL,
        ADD CONSTRAINT assessment_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        ADD CONSTRAINT assessment_kind_check CHECK (kind IN ('pre_test', 'post_test', 'rubric'))
    `);
    await q.query(
      `CREATE INDEX assessment_student_idx ON platform.assessment (student_user_id)`,
    );

    await q.query(
      `ALTER TABLE platform.feedback ALTER COLUMN assessment_id DROP NOT NULL`,
    );
    await q.query(`
      ALTER TABLE platform.feedback
        ADD COLUMN student_user_id uuid,
        ADD COLUMN author_user_id uuid,
        ADD COLUMN school_id uuid,
        ADD COLUMN read_at timestamptz,
        ADD CONSTRAINT feedback_student_user_id_fkey FOREIGN KEY (student_user_id)
          REFERENCES platform.app_user(id) ON DELETE CASCADE,
        ADD CONSTRAINT feedback_author_user_id_fkey FOREIGN KEY (author_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        ADD CONSTRAINT feedback_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE
    `);
    await q.query(
      `CREATE INDEX feedback_student_idx ON platform.feedback (student_user_id, created_at)`,
    );

    await q.query(`
      CREATE TABLE platform.alert_config (
        school_id          uuid NOT NULL,
        mastery_threshold  numeric(5,4) NOT NULL DEFAULT 0.4,
        max_uncertainty    numeric(5,4) NOT NULL DEFAULT 0.35,
        min_evidence       integer NOT NULL DEFAULT 3,
        inactivity_days    integer NOT NULL DEFAULT 14,
        review_status      text NOT NULL DEFAULT 'pending_pedagogical_review',
        updated_at         timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT alert_config_pkey PRIMARY KEY (school_id),
        CONSTRAINT alert_config_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        CONSTRAINT alert_config_threshold_check CHECK (mastery_threshold >= 0 AND mastery_threshold <= 1)
      )
    `);

    await q.query(`
      CREATE TABLE platform.processed_event (
        event_id      text NOT NULL,
        event_type    text NOT NULL,
        stream        text NOT NULL,
        outcome       text NOT NULL,
        processed_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT processed_event_pkey PRIMARY KEY (event_id)
      )
    `);

    await q.query(`
      CREATE TABLE platform.outbox_event (
        id            uuid NOT NULL DEFAULT gen_random_uuid(),
        event_type    text NOT NULL,
        aggregate_id  text,
        payload       jsonb NOT NULL,
        trace_id      text,
        occurred_at   timestamptz NOT NULL DEFAULT now(),
        published_at  timestamptz,
        attempts      integer NOT NULL DEFAULT 0,
        last_error    text,
        CONSTRAINT outbox_event_pkey PRIMARY KEY (id)
      )
    `);
    await q.query(
      `CREATE INDEX outbox_event_pending_idx ON platform.outbox_event (published_at, occurred_at)`,
    );

    await q.query(`
      CREATE TABLE platform.idempotency_record (
        scope        text NOT NULL,
        key          text NOT NULL,
        user_id      uuid,
        status_code  integer NOT NULL,
        response     jsonb NOT NULL,
        created_at   timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT idempotency_record_pkey PRIMARY KEY (scope, key)
      )
    `);

    await q.query(`
      CREATE TABLE platform.export_record (
        id                    uuid NOT NULL DEFAULT gen_random_uuid(),
        school_id             uuid,
        requested_by_user_id  uuid,
        kind                  text NOT NULL,
        format                text NOT NULL,
        bucket                text NOT NULL,
        object_key            text NOT NULL,
        size_bytes            integer NOT NULL,
        created_at            timestamptz NOT NULL DEFAULT now(),
        purged_at             timestamptz,
        CONSTRAINT export_record_pkey PRIMARY KEY (id),
        CONSTRAINT export_record_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        CONSTRAINT export_record_requested_by_user_id_fkey FOREIGN KEY (requested_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        CONSTRAINT export_record_kind_check CHECK (kind IN ('report', 'dataset')),
        CONSTRAINT export_record_format_check CHECK (format IN ('pdf', 'csv', 'json'))
      )
    `);
    await q.query(
      `CREATE INDEX export_record_created_idx ON platform.export_record (created_at)`,
    );
  }

  public async down(q: QueryRunner): Promise<void> {
    await q.query(`DROP TABLE IF EXISTS platform.export_record`);
    await q.query(`DROP TABLE IF EXISTS platform.idempotency_record`);
    await q.query(`DROP TABLE IF EXISTS platform.outbox_event`);
    await q.query(`DROP TABLE IF EXISTS platform.processed_event`);
    await q.query(`DROP TABLE IF EXISTS platform.alert_config`);
    await q.query(`DROP INDEX IF EXISTS platform.feedback_student_idx`);
    await q.query(`
      ALTER TABLE platform.feedback
        DROP CONSTRAINT IF EXISTS feedback_school_id_fkey,
        DROP CONSTRAINT IF EXISTS feedback_author_user_id_fkey,
        DROP CONSTRAINT IF EXISTS feedback_student_user_id_fkey,
        DROP COLUMN IF EXISTS read_at, DROP COLUMN IF EXISTS school_id,
        DROP COLUMN IF EXISTS author_user_id, DROP COLUMN IF EXISTS student_user_id
    `);
    // Volta ao NOT NULL só se não houver feedback sem avaliação (não apaga dados).
    await q.query(`
      DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM platform.feedback WHERE assessment_id IS NULL) THEN
          ALTER TABLE platform.feedback ALTER COLUMN assessment_id SET NOT NULL;
        END IF;
      END $$
    `);
    await q.query(`DROP INDEX IF EXISTS platform.assessment_student_idx`);
    await q.query(`
      ALTER TABLE platform.assessment
        DROP CONSTRAINT IF EXISTS assessment_kind_check,
        DROP CONSTRAINT IF EXISTS assessment_recorded_by_user_id_fkey,
        DROP CONSTRAINT IF EXISTS assessment_competency_id_fkey,
        DROP CONSTRAINT IF EXISTS assessment_school_id_fkey,
        DROP COLUMN IF EXISTS details, DROP COLUMN IF EXISTS recorded_by_user_id,
        DROP COLUMN IF EXISTS competency_id, DROP COLUMN IF EXISTS school_id, DROP COLUMN IF EXISTS kind
    `);
    await q.query(`
      ALTER TABLE platform.competency_estimate
        DROP COLUMN IF EXISTS synthetic, DROP COLUMN IF EXISTS last_event_at,
        DROP COLUMN IF EXISTS last_event_id, DROP COLUMN IF EXISTS evidence_count,
        DROP COLUMN IF EXISTS uncertainty
    `);
    await q.query(`DROP INDEX IF EXISTS platform.cognitive_profile_school_idx`);
    await q.query(`
      ALTER TABLE platform.cognitive_profile
        DROP CONSTRAINT IF EXISTS cognitive_profile_school_id_fkey, DROP COLUMN IF EXISTS school_id
    `);
    await q.query(`DROP INDEX IF EXISTS platform.evidence_school_idx`);
    await q.query(
      `DROP INDEX IF EXISTS platform.evidence_student_competency_idx`,
    );
    await q.query(`
      ALTER TABLE platform.evidence
        DROP CONSTRAINT IF EXISTS evidence_bncc_skill_id_fkey,
        DROP CONSTRAINT IF EXISTS evidence_planet_id_fkey,
        DROP CONSTRAINT IF EXISTS evidence_school_id_fkey,
        DROP CONSTRAINT IF EXISTS evidence_event_id_key,
        DROP COLUMN IF EXISTS occurred_at, DROP COLUMN IF EXISTS synthetic, DROP COLUMN IF EXISTS source,
        DROP COLUMN IF EXISTS bncc_skill_id, DROP COLUMN IF EXISTS planet_id,
        DROP COLUMN IF EXISTS school_id, DROP COLUMN IF EXISTS event_id
    `);
    await q.query(`DROP INDEX IF EXISTS platform.planet_meta_school_idx`);
    await q.query(`DROP INDEX IF EXISTS platform.planet_meta_owner_idx`);
    await q.query(`
      ALTER TABLE platform.planet_meta
        DROP CONSTRAINT IF EXISTS planet_meta_status_check,
        DROP CONSTRAINT IF EXISTS planet_meta_school_id_fkey,
        DROP COLUMN IF EXISTS status, DROP COLUMN IF EXISTS school_id
    `);
  }
}
