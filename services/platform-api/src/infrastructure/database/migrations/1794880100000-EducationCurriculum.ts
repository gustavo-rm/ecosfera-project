import type { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Educação e catálogo curricular.
 * - trilha com nível (Fundamental II, Médio, Técnico) e turma ligada à trilha (RF-061, RP-002);
 * - missão com escola, autor, objetivo, parâmetros e situação; publicação para turmas (RF-062);
 * - competência e habilidade BNCC como DADO versionado, com estado de validação (RSK-06).
 *
 * O seed do catálogo vem do briefing (Dossiê §5.3). Todos os registros entram como
 * `pending_validation`: os códigos existem na BNCC, mas o vínculo com o tema/competência
 * e as descrições são resumos NÃO oficiais e precisam de validação por especialista.
 */
const COMPETENCIAS: [string, string, string[]][] = [
  ['SCIENTIFIC_THINKING', 'Pensamento científico', ['CG2']],
  ['CAUSE_EFFECT', 'Causa e efeito', ['CG2']],
  ['SYSTEMS_THINKING', 'Pensamento sistêmico', []],
  ['DECISION_MAKING', 'Tomada de decisão', ['CG7']],
  ['CONSEQUENCE_ANALYSIS', 'Análise de consequências', []],
  ['DATA_LITERACY', 'Letramento de dados', ['CG5']],
  ['EVOLUTION', 'Evolução (Biologia)', []],
  ['PERSISTENCE', 'Persistência', []],
  ['CREATIVITY', 'Criatividade', []],
  ['ARGUMENTATION', 'Argumentação', ['CG7']],
];

/** [código, componente, tema, etapa, competência] */
const HABILIDADES: [string, string, string, string, string][] = [
  ['EF09CI16', 'Ciências', 'Criar planeta / zona habitável', 'fundamental', 'CAUSE_EFFECT'],
  ['EF09CI14', 'Ciências', 'Criar planeta / zona habitável', 'fundamental', 'CAUSE_EFFECT'],
  ['EM13CNT201', 'Ciências da Natureza', 'Criar planeta / zona habitável', 'medio', 'CAUSE_EFFECT'],
  ['EM13CNT202', 'Ciências da Natureza', 'Criar planeta / zona habitável', 'medio', 'CAUSE_EFFECT'],
  ['EF06CI11', 'Ciências', 'Estrutura da Terra e geologia', 'fundamental', 'SYSTEMS_THINKING'],
  ['EF06CI14', 'Ciências', 'Órbita, estações, dia/noite', 'fundamental', 'CAUSE_EFFECT'],
  ['EF09CI17', 'Ciências', 'Órbita, estações, dia/noite', 'fundamental', 'CAUSE_EFFECT'],
  ['EF07CI13', 'Ciências', 'Atmosfera e efeito estufa', 'fundamental', 'CAUSE_EFFECT'],
  ['EF07CI12', 'Ciências', 'Atmosfera e efeito estufa', 'fundamental', 'CAUSE_EFFECT'],
  ['EF07CI14', 'Ciências', 'Camada de ozônio', 'fundamental', 'CAUSE_EFFECT'],
  ['EF08CI14', 'Ciências', 'Clima e circulação', 'fundamental', 'SYSTEMS_THINKING'],
  ['EF08CI15', 'Ciências', 'Eventos climáticos', 'fundamental', 'CONSEQUENCE_ANALYSIS'],
  ['EF08CI16', 'Ciências', 'Alterações climáticas', 'fundamental', 'CONSEQUENCE_ANALYSIS'],
  ['EM13CNT101', 'Ciências da Natureza', 'Ciclos do carbono/água/nitrogênio', 'medio', 'SYSTEMS_THINKING'],
  ['EM13CNT203', 'Ciências da Natureza', 'Ciclos do carbono/água/nitrogênio; trade-offs', 'medio', 'SYSTEMS_THINKING'],
  ['EF07CI07', 'Ciências', 'Ecossistemas e cadeias tróficas', 'fundamental', 'SYSTEMS_THINKING'],
  ['EF07CI08', 'Ciências', 'Ecossistemas e cadeias tróficas', 'fundamental', 'SYSTEMS_THINKING'],
  ['EF09CI12', 'Ciências', 'Biodiversidade e espécies', 'fundamental', 'CONSEQUENCE_ANALYSIS'],
  ['EM13CNT206', 'Ciências da Natureza', 'Biodiversidade e espécies; trade-offs', 'medio', 'CONSEQUENCE_ANALYSIS'],
  ['EF09CI11', 'Ciências', 'Evolução e seleção natural', 'fundamental', 'EVOLUTION'],
  ['EF09CI09', 'Ciências', 'Evolução e seleção natural', 'fundamental', 'EVOLUTION'],
  ['EF07MA17', 'Matemática', 'Séries temporais e dados', 'fundamental', 'DATA_LITERACY'],
  ['EF07MA35', 'Matemática', 'Séries temporais e dados', 'fundamental', 'DATA_LITERACY'],
  ['EF07MA36', 'Matemática', 'Séries temporais e dados', 'fundamental', 'DATA_LITERACY'],
  ['EF07MA37', 'Matemática', 'Séries temporais e dados', 'fundamental', 'DATA_LITERACY'],
  ['EM13CNT306', 'Ciências da Natureza', 'Trade-offs e decisão socioambiental', 'medio', 'DECISION_MAKING'],
  ['EM13CNT301', 'Ciências da Natureza', 'Investigar (hipótese → teste → revisão)', 'medio', 'SCIENTIFIC_THINKING'],
  ['EM13CNT302', 'Ciências da Natureza', 'Investigar (hipótese → teste → revisão)', 'medio', 'SCIENTIFIC_THINKING'],
];

export const VERSAO_INICIAL_DO_CATALOGO = '2026.0-draft';

export class EducationCurriculum1794880100000 implements MigrationInterface {
  name = 'EducationCurriculum1794880100000';

  public async up(q: QueryRunner): Promise<void> {
    await q.query(`
      ALTER TABLE platform.track
        ADD COLUMN level text,
        ADD CONSTRAINT track_level_check CHECK (level IN ('fundamental_ii', 'medio', 'tecnico')),
        ADD CONSTRAINT track_level_key UNIQUE (level)
    `);
    const trilhas: [string, string, string][] = [
      ['Fundamental II', 'Trilha para os anos finais do Ensino Fundamental', 'fundamental_ii'],
      ['Ensino Médio', 'Trilha para o Ensino Médio', 'medio'],
      ['Técnico', 'Trilha para o ensino técnico', 'tecnico'],
    ];
    for (const [nome, descricao, nivel] of trilhas) {
      // Reaplicável: reaproveita a trilha de mesmo nome se ela já existir.
      await q.query(
        `UPDATE platform.track SET level = $2 WHERE id = (SELECT id FROM platform.track WHERE name = $1 AND level IS NULL ORDER BY created_at LIMIT 1)`,
        [nome, nivel],
      );
      await q.query(
        `INSERT INTO platform.track (name, description, level) SELECT $1, $2, $3
         WHERE NOT EXISTS (SELECT 1 FROM platform.track WHERE level = $3)`,
        [nome, descricao, nivel],
      );
    }

    await q.query(`
      ALTER TABLE platform.class
        ADD COLUMN track_id uuid,
        ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
        ADD CONSTRAINT class_track_id_fkey FOREIGN KEY (track_id)
          REFERENCES platform.track(id) ON DELETE SET NULL
    `);
    await q.query(`CREATE INDEX class_school_idx ON platform.class (school_id)`);
    await q.query(`CREATE INDEX class_teacher_idx ON platform.class (teacher_user_id)`);
    await q.query(`CREATE INDEX enrollment_student_idx ON platform.enrollment (student_user_id)`);
    await q.query(`CREATE INDEX guardian_student_idx ON platform.guardian (student_user_id)`);

    await q.query(`
      ALTER TABLE platform.mission
        ADD COLUMN school_id uuid,
        ADD COLUMN created_by_user_id uuid,
        ADD COLUMN objective text,
        ADD COLUMN parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN status text NOT NULL DEFAULT 'draft',
        ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
        ADD CONSTRAINT mission_school_id_fkey FOREIGN KEY (school_id)
          REFERENCES platform.school(id) ON DELETE CASCADE,
        ADD CONSTRAINT mission_created_by_user_id_fkey FOREIGN KEY (created_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL,
        ADD CONSTRAINT mission_status_check CHECK (status IN ('draft', 'published', 'archived'))
    `);
    await q.query(`CREATE INDEX mission_school_idx ON platform.mission (school_id)`);

    await q.query(`
      CREATE TABLE platform.mission_assignment (
        mission_id           uuid NOT NULL,
        class_id             uuid NOT NULL,
        assigned_by_user_id  uuid,
        published_at         timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT mission_assignment_pkey PRIMARY KEY (mission_id, class_id),
        CONSTRAINT mission_assignment_mission_id_fkey FOREIGN KEY (mission_id)
          REFERENCES platform.mission(id) ON DELETE CASCADE,
        CONSTRAINT mission_assignment_class_id_fkey FOREIGN KEY (class_id)
          REFERENCES platform.class(id) ON DELETE CASCADE,
        CONSTRAINT mission_assignment_assigned_by_user_id_fkey FOREIGN KEY (assigned_by_user_id)
          REFERENCES platform.app_user(id) ON DELETE SET NULL
      )
    `);
    await q.query(`CREATE INDEX mission_assignment_class_idx ON platform.mission_assignment (class_id)`);

    await q.query(`
      ALTER TABLE platform.competency
        ADD COLUMN code text,
        ADD COLUMN general_competencies text[] NOT NULL DEFAULT '{}'::text[],
        ADD COLUMN validation_status text NOT NULL DEFAULT 'pending_validation',
        ADD COLUMN catalog_version text NOT NULL DEFAULT '${VERSAO_INICIAL_DO_CATALOGO}',
        ADD CONSTRAINT competency_code_key UNIQUE (code),
        ADD CONSTRAINT competency_validation_status_check
          CHECK (validation_status IN ('pending_validation', 'validated', 'rejected'))
    `);
    await q.query(`
      ALTER TABLE platform.bncc_skill
        ADD COLUMN competency_id uuid,
        ADD COLUMN component text,
        ADD COLUMN theme text,
        ADD COLUMN stage text,
        ADD COLUMN validation_status text NOT NULL DEFAULT 'pending_validation',
        ADD COLUMN catalog_version text NOT NULL DEFAULT '${VERSAO_INICIAL_DO_CATALOGO}',
        ADD COLUMN active boolean NOT NULL DEFAULT true,
        ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
        ADD CONSTRAINT bncc_skill_competency_id_fkey FOREIGN KEY (competency_id)
          REFERENCES platform.competency(id) ON DELETE SET NULL,
        ADD CONSTRAINT bncc_skill_validation_status_check
          CHECK (validation_status IN ('pending_validation', 'validated', 'rejected')),
        ADD CONSTRAINT bncc_skill_stage_check CHECK (stage IN ('fundamental', 'medio', 'tecnico'))
    `);

    for (const [codigo, nome, cgs] of COMPETENCIAS) {
      await q.query(`UPDATE platform.competency SET code = $1 WHERE name = $2 AND code IS NULL`, [codigo, nome]);
      await q.query(
        `INSERT INTO platform.competency (code, name, description, general_competencies)
         VALUES ($1, $2, $3, $4) ON CONFLICT (code) DO NOTHING`,
        [codigo, nome, 'Competência do modelo pedagógico ECOSFERA — pendente de validação', cgs],
      );
    }
    for (const [codigo, componente, tema, etapa, competencia] of HABILIDADES) {
      await q.query(
        `INSERT INTO platform.bncc_skill (code, description, component, theme, stage, competency_id)
         VALUES ($1, $2, $3, $4, $5, (SELECT id FROM platform.competency WHERE code = $6))
         ON CONFLICT (code) DO UPDATE SET
           component = EXCLUDED.component, theme = EXCLUDED.theme, stage = EXCLUDED.stage,
           competency_id = EXCLUDED.competency_id
         WHERE platform.bncc_skill.validation_status = 'pending_validation'`,
        [
          codigo,
          `${tema} — resumo não oficial; conferir com o texto da BNCC (pendente de validação)`,
          componente,
          tema,
          etapa,
          competencia,
        ],
      );
    }
  }

  public async down(q: QueryRunner): Promise<void> {
    // Não destrutiva: linhas do catálogo e trilhas permanecem; só colunas e constraints saem.
    await q.query(`
      ALTER TABLE platform.bncc_skill
        DROP CONSTRAINT IF EXISTS bncc_skill_stage_check,
        DROP CONSTRAINT IF EXISTS bncc_skill_validation_status_check,
        DROP CONSTRAINT IF EXISTS bncc_skill_competency_id_fkey,
        DROP COLUMN IF EXISTS updated_at, DROP COLUMN IF EXISTS active,
        DROP COLUMN IF EXISTS catalog_version, DROP COLUMN IF EXISTS validation_status,
        DROP COLUMN IF EXISTS stage, DROP COLUMN IF EXISTS theme,
        DROP COLUMN IF EXISTS component, DROP COLUMN IF EXISTS competency_id
    `);
    await q.query(`
      ALTER TABLE platform.competency
        DROP CONSTRAINT IF EXISTS competency_validation_status_check,
        DROP CONSTRAINT IF EXISTS competency_code_key,
        DROP COLUMN IF EXISTS catalog_version, DROP COLUMN IF EXISTS validation_status,
        DROP COLUMN IF EXISTS general_competencies, DROP COLUMN IF EXISTS code
    `);
    await q.query(`DROP TABLE IF EXISTS platform.mission_assignment`);
    await q.query(`DROP INDEX IF EXISTS platform.mission_school_idx`);
    await q.query(`
      ALTER TABLE platform.mission
        DROP CONSTRAINT IF EXISTS mission_status_check,
        DROP CONSTRAINT IF EXISTS mission_created_by_user_id_fkey,
        DROP CONSTRAINT IF EXISTS mission_school_id_fkey,
        DROP COLUMN IF EXISTS updated_at, DROP COLUMN IF EXISTS status,
        DROP COLUMN IF EXISTS parameters, DROP COLUMN IF EXISTS objective,
        DROP COLUMN IF EXISTS created_by_user_id, DROP COLUMN IF EXISTS school_id
    `);
    await q.query(`DROP INDEX IF EXISTS platform.guardian_student_idx`);
    await q.query(`DROP INDEX IF EXISTS platform.enrollment_student_idx`);
    await q.query(`DROP INDEX IF EXISTS platform.class_teacher_idx`);
    await q.query(`DROP INDEX IF EXISTS platform.class_school_idx`);
    await q.query(`
      ALTER TABLE platform.class
        DROP CONSTRAINT IF EXISTS class_track_id_fkey,
        DROP COLUMN IF EXISTS updated_at, DROP COLUMN IF EXISTS track_id
    `);
    await q.query(`
      ALTER TABLE platform.track
        DROP CONSTRAINT IF EXISTS track_level_key,
        DROP CONSTRAINT IF EXISTS track_level_check,
        DROP COLUMN IF EXISTS level
    `);
  }
}
