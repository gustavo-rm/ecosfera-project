import type { MigrationInterface, QueryRunner } from 'typeorm';

/** Mapeia o contexto (curso) do LMS à turma do ECOSFERA, para importação via LTI 1.3 (RF-009). */
export class LtiContext1794880300000 implements MigrationInterface {
  name = 'LtiContext1794880300000';

  public async up(q: QueryRunner): Promise<void> {
    await q.query(`
      CREATE TABLE platform.lti_context (
        platform_id  uuid NOT NULL,
        context_id   text NOT NULL,
        class_id     uuid NOT NULL,
        created_at   timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT lti_context_pkey PRIMARY KEY (platform_id, context_id),
        CONSTRAINT lti_context_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES platform.lti_platform(id) ON DELETE CASCADE,
        CONSTRAINT lti_context_class_id_fkey FOREIGN KEY (class_id) REFERENCES platform.class(id) ON DELETE CASCADE
      )
    `);
  }

  public async down(q: QueryRunner): Promise<void> {
    await q.query(`DROP TABLE IF EXISTS platform.lti_context`);
  }
}
