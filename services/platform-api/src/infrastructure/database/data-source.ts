import 'reflect-metadata';
import 'dotenv/config';
import { DataSource } from 'typeorm';

import { opcoesDoBanco } from '../../shared/database/opcoes';

/**
 * DataSource usado pela CLI de migrações do TypeORM.
 * O schema relacional autoritativo vive em "platform" (ver init do Postgres).
 * `synchronize` é SEMPRE false: schema evolui exclusivamente por migration.
 */
if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL é obrigatória para a CLI de migrações');
}

export default new DataSource(
  opcoesDoBanco({
    url: process.env.DATABASE_URL,
    ssl: process.env.DB_SSL === 'true',
    logging: process.env.DB_LOGGING === 'true',
    applicationName: 'platform-api-migrations',
  }),
);
