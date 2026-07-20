import { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Baseline do schema relacional autoritativo (schema "platform").
 * Fiel ao modelo de dados do dossiê (§6.4). Colunas mínimas viáveis:
 * estenda por novas migrations conforme cada contexto for implementado.
 */
export class InitPlatformSchema1710000000000 implements MigrationInterface {
  name = 'InitPlatformSchema1710000000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TYPE platform.user_role AS ENUM
        ('student', 'teacher', 'coordinator', 'admin', 'guardian');
    `);

    await queryRunner.query(`
      CREATE TABLE platform.school (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name        text NOT NULL,
        created_at  timestamptz NOT NULL DEFAULT now(),
        updated_at  timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.app_user (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        school_id      uuid REFERENCES platform.school(id) ON DELETE SET NULL,
        name           text NOT NULL,
        email          text NOT NULL UNIQUE,
        password_hash  text NOT NULL,
        role           platform.user_role NOT NULL,
        created_at     timestamptz NOT NULL DEFAULT now(),
        updated_at     timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.guardian (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        guardian_user_id  uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        student_user_id   uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        created_at        timestamptz NOT NULL DEFAULT now(),
        UNIQUE (guardian_user_id, student_user_id)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.consent (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        student_user_id   uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        guardian_user_id  uuid REFERENCES platform.app_user(id) ON DELETE SET NULL,
        status            text NOT NULL DEFAULT 'pending',
        granted_at        timestamptz,
        created_at        timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.class (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        school_id        uuid NOT NULL REFERENCES platform.school(id) ON DELETE CASCADE,
        teacher_user_id  uuid REFERENCES platform.app_user(id) ON DELETE SET NULL,
        name             text NOT NULL,
        year             integer,
        created_at       timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.enrollment (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        class_id         uuid NOT NULL REFERENCES platform.class(id) ON DELETE CASCADE,
        student_user_id  uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        created_at       timestamptz NOT NULL DEFAULT now(),
        UNIQUE (class_id, student_user_id)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.track (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name         text NOT NULL,
        description  text,
        created_at   timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.mission (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        track_id     uuid NOT NULL REFERENCES platform.track(id) ON DELETE CASCADE,
        title        text NOT NULL,
        description  text,
        order_index  integer NOT NULL DEFAULT 0,
        created_at   timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.bncc_skill (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code         text NOT NULL UNIQUE,
        description  text NOT NULL
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.mission_bncc (
        mission_id     uuid NOT NULL REFERENCES platform.mission(id) ON DELETE CASCADE,
        bncc_skill_id  uuid NOT NULL REFERENCES platform.bncc_skill(id) ON DELETE CASCADE,
        PRIMARY KEY (mission_id, bncc_skill_id)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.competency (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name         text NOT NULL,
        description  text
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.cognitive_profile (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        student_user_id  uuid NOT NULL UNIQUE REFERENCES platform.app_user(id) ON DELETE CASCADE,
        updated_at       timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.competency_estimate (
        id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        cognitive_profile_id  uuid NOT NULL REFERENCES platform.cognitive_profile(id) ON DELETE CASCADE,
        competency_id         uuid NOT NULL REFERENCES platform.competency(id) ON DELETE CASCADE,
        probability           numeric(5,4) NOT NULL DEFAULT 0,
        updated_at            timestamptz NOT NULL DEFAULT now(),
        UNIQUE (cognitive_profile_id, competency_id)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.evidence (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        student_user_id  uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        competency_id    uuid REFERENCES platform.competency(id) ON DELETE SET NULL,
        type             text NOT NULL,
        payload          jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at       timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.assessment (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        student_user_id  uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        mission_id       uuid REFERENCES platform.mission(id) ON DELETE SET NULL,
        score            numeric(5,2),
        created_at       timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.feedback (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        assessment_id  uuid NOT NULL REFERENCES platform.assessment(id) ON DELETE CASCADE,
        content        text NOT NULL,
        created_at     timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.planet_meta (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        owner_user_id  uuid NOT NULL REFERENCES platform.app_user(id) ON DELETE CASCADE,
        mission_id     uuid REFERENCES platform.mission(id) ON DELETE SET NULL,
        current_era    integer NOT NULL DEFAULT 0,
        seed           text,
        created_at     timestamptz NOT NULL DEFAULT now(),
        updated_at     timestamptz NOT NULL DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE platform.audit_log (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        actor_user_id  uuid REFERENCES platform.app_user(id) ON DELETE SET NULL,
        action         text NOT NULL,
        entity         text NOT NULL,
        entity_id      text,
        data           jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at     timestamptz NOT NULL DEFAULT now()
      );
    `);
    await queryRunner.query(`
      CREATE INDEX audit_log_entity_idx ON platform.audit_log (entity, entity_id);
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Ordem inversa por causa das FKs.
    await queryRunner.query(`DROP TABLE IF EXISTS platform.audit_log;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.planet_meta;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.feedback;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.assessment;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.evidence;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.competency_estimate;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.cognitive_profile;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.competency;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.mission_bncc;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.bncc_skill;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.mission;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.track;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.enrollment;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.class;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.consent;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.guardian;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.app_user;`);
    await queryRunner.query(`DROP TABLE IF EXISTS platform.school;`);
    await queryRunner.query(`DROP TYPE IF EXISTS platform.user_role;`);
  }
}
