import { PostgreSqlContainer } from '@testcontainers/postgresql';
import { Client } from 'pg';
import { DataSource } from 'typeorm';

import { verificarDrift } from '../../scripts/verificar-drift';
import { opcoesDoBanco } from '../../src/shared/database/opcoes';

async function consultar(url: string, sql: string, params: unknown[] = []) {
  const c = new Client({ connectionString: url });
  await c.connect();
  try {
    return await c.query(sql, params);
  } finally {
    await c.end();
  }
}

describe('Migrações do schema platform', () => {
  const admin = () => process.env.TEST_DATABASE_ADMIN_URL!;
  const app = () => process.env.DATABASE_URL!;

  it('não há drift entre entidades TypeORM e migrações', async () => {
    expect(await verificarDrift(admin(), false)).toEqual([]);
  });

  it('a baseline continua com as 18 tabelas originais', async () => {
    const r = await consultar(
      admin(),
      `SELECT count(*)::int AS n FROM information_schema.tables WHERE table_schema = 'platform' AND table_name = ANY($1)`,
      [[
        'school', 'app_user', 'guardian', 'consent', 'class', 'enrollment', 'track', 'mission', 'bncc_skill',
        'mission_bncc', 'competency', 'cognitive_profile', 'competency_estimate', 'evidence', 'assessment',
        'feedback', 'planet_meta', 'audit_log',
      ]],
    );
    expect(r.rows[0].n).toBe(18);
  });

  it('o platform-api não tem acesso ao schema rag', async () => {
    await expect(consultar(app(), 'CREATE TABLE rag.intruso (id int)')).rejects.toThrow(/permission denied/);
  });

  describe('audit_log é imutável', () => {
    let id: string;
    beforeAll(async () => {
      const r = await consultar(app(), `INSERT INTO platform.audit_log (action, entity) VALUES ('teste.imutavel', 'teste') RETURNING id`);
      id = r.rows[0].id as string;
    });

    it('a role da aplicação não consegue UPDATE', async () => {
      await expect(consultar(app(), `UPDATE platform.audit_log SET action = 'x' WHERE id = $1`, [id])).rejects.toThrow(/permission denied/);
    });
    it('a role da aplicação não consegue DELETE', async () => {
      await expect(consultar(app(), `DELETE FROM platform.audit_log WHERE id = $1`, [id])).rejects.toThrow(/permission denied/);
    });
    it('a role da aplicação não consegue TRUNCATE', async () => {
      await expect(consultar(app(), `TRUNCATE platform.audit_log`)).rejects.toThrow(/permission denied/);
    });
    it('mesmo o dono do schema é barrado pelo gatilho (UPDATE e DELETE)', async () => {
      await expect(consultar(admin(), `UPDATE platform.audit_log SET action = 'x' WHERE id = $1`, [id])).rejects.toThrow(/imutável/);
      await expect(consultar(admin(), `DELETE FROM platform.audit_log WHERE id = $1`, [id])).rejects.toThrow(/imutável/);
    });
  });

  it('sobem do zero, descem (down) e sobem de novo sem duplicar o seed', async () => {
    const pg = await new PostgreSqlContainer('pgvector/pgvector:pg16').start();
    try {
      await consultar(pg.getConnectionUri(), 'CREATE EXTENSION IF NOT EXISTS vector; CREATE SCHEMA IF NOT EXISTS platform; CREATE SCHEMA IF NOT EXISTS rag;');
      const ds = new DataSource(opcoesDoBanco({ url: pg.getConnectionUri() }));
      await ds.initialize();
      const aplicadas = await ds.runMigrations({ transaction: 'each' });
      expect(aplicadas.map((m) => m.name)).toEqual([
        'InitPlatformSchema1710000000000',
        'IdentityTenancyLgpd1794880000000',
        'EducationCurriculum1794880100000',
        'AssessmentOrchestration1794880200000',
        'LtiContext1794880300000',
      ]);
      for (let i = 0; i < 4; i++) await ds.undoLastMigration({ transaction: 'each' });
      await ds.runMigrations({ transaction: 'each' });
      const trilhas: { n: number }[] = await ds.query(`SELECT count(*)::int AS n FROM platform.track WHERE level IS NOT NULL`);
      const habilidades: { n: number }[] = await ds.query(`SELECT count(*)::int AS n FROM platform.bncc_skill`);
      const competencias: { n: number }[] = await ds.query(`SELECT count(*)::int AS n FROM platform.competency WHERE code IS NOT NULL`);
      expect(trilhas[0]!.n).toBe(3);
      expect(habilidades[0]!.n).toBe(28);
      expect(competencias[0]!.n).toBe(10);
      await ds.destroy();
      expect(await verificarDrift(pg.getConnectionUri(), false)).toEqual([]);
    } finally {
      await pg.stop();
    }
  });
});
