import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { PostgreSqlContainer, type StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { RedisContainer, type StartedRedisContainer } from '@testcontainers/redis';
import { Client } from 'pg';
import { DataSource } from 'typeorm';

import { opcoesDoBanco } from '../../src/shared/database/opcoes';

const RAIZ = join(__dirname, '..', '..', '..', '..');
export const SENHA_APP = 'senha-de-teste-do-app';

export interface Ambiente {
  pg: StartedPostgreSqlContainer;
  redis: StartedRedisContainer;
  urlAdmin: string;
  urlApp: string;
  urlRedis: string;
}

/** Sobe PostgreSQL (mesmo init do compose) e Redis, aplica as migrações e os papéis restritos. */
export async function subirAmbiente(): Promise<Ambiente> {
  const [pg, redis] = await Promise.all([
    new PostgreSqlContainer('pgvector/pgvector:pg16')
      .withDatabase('ecosfera')
      .withUsername('ecosfera')
      .withPassword('ecosfera')
      .withCopyFilesToContainer([
        {
          source: join(RAIZ, 'infra', 'docker', 'postgres', 'initdb', '01-extensions-schemas.sql'),
          target: '/docker-entrypoint-initdb.d/01-extensions-schemas.sql',
        },
      ])
      .start(),
    new RedisContainer('redis:7-alpine').start(),
  ]);
  const urlAdmin = pg.getConnectionUri();
  const ds = new DataSource(opcoesDoBanco({ url: urlAdmin }));
  await ds.initialize();
  await ds.runMigrations({ transaction: 'each' });
  await ds.destroy();
  await aplicarPapeis(urlAdmin);
  const u = new URL(urlAdmin);
  u.username = 'platform_app';
  u.password = SENHA_APP;
  return { pg, redis, urlAdmin, urlApp: u.toString(), urlRedis: redis.getConnectionUrl() };
}

export async function aplicarPapeis(urlAdmin: string): Promise<void> {
  const c = new Client({ connectionString: urlAdmin });
  await c.connect();
  try {
    await c.query(readFileSync(join(__dirname, '..', '..', 'db', 'papeis-por-schema.sql'), 'utf8'));
    await c.query(`ALTER ROLE platform_app PASSWORD '${SENHA_APP}'`);
  } finally {
    await c.end();
  }
}
