/** Aplica as migrações pendentes (usado pela imagem de produção como passo separado). */
import 'reflect-metadata';

import { DataSource } from 'typeorm';

import { opcoesDoBanco } from './shared/database/opcoes';

async function migrar(): Promise<void> {
  const url = process.env.DATABASE_MIGRATION_URL ?? process.env.DATABASE_URL;
  if (!url)
    throw new Error(
      'Defina DATABASE_MIGRATION_URL (papel platform_migrator) ou DATABASE_URL',
    );
  const ds = await new DataSource(
    opcoesDoBanco({ url, ssl: process.env.DB_SSL === 'true' }),
  ).initialize();
  const feitas = await ds.runMigrations({ transaction: 'each' });
  console.log(
    `Migrações aplicadas: ${feitas.map((m) => m.name).join(', ') || 'nenhuma pendente'}`,
  );
  await ds.destroy();
}

migrar().catch((e: unknown) => {
  console.error(e);
  process.exit(1);
});
