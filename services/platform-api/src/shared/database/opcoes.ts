import { join } from 'node:path';

import type { DataSourceOptions } from 'typeorm';

import { ENTIDADES } from './entidades';

export interface OpcoesDeBanco {
  url: string;
  ssl?: boolean;
  logging?: boolean;
  poolMax?: number;
  applicationName?: string;
}

/**
 * Opções do TypeORM. `synchronize` é SEMPRE false: o schema evolui só por migração.
 * O schema `platform` é exclusivo do platform-api (ADR 0003).
 */
export function opcoesDoBanco(o: OpcoesDeBanco): DataSourceOptions {
  return {
    type: 'postgres',
    url: o.url,
    schema: 'platform',
    uuidExtension: 'pgcrypto',
    installExtensions: false,
    entities: ENTIDADES,
    migrations: [join(__dirname, '..', '..', 'infrastructure', 'database', 'migrations', '*.{ts,js}')],
    migrationsTableName: 'platform_migrations',
    migrationsTransactionMode: 'each',
    synchronize: false,
    migrationsRun: false,
    logging: o.logging ? ['error', 'warn', 'migration'] : ['error', 'migration'],
    ssl: o.ssl ? { rejectUnauthorized: true } : undefined,
    applicationName: o.applicationName ?? 'platform-api',
    extra: { max: o.poolMax ?? 10 },
  };
}
