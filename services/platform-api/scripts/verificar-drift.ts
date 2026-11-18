/**
 * Verificação de drift: as entidades TypeORM batem com o schema produzido pelas migrações?
 * Uso: DATABASE_URL=... ts-node scripts/verificar-drift.ts [--aplicar-migracoes]
 * Sai com código 1 e lista o SQL que o TypeORM geraria se houver diferença.
 */
import 'reflect-metadata';

import { DataSource } from 'typeorm';

import { opcoesDoBanco } from '../src/shared/database/opcoes';

export async function verificarDrift(
  url: string,
  aplicar: boolean,
): Promise<string[]> {
  const ds = new DataSource(opcoesDoBanco({ url }));
  await ds.initialize();
  try {
    if (aplicar) await ds.runMigrations({ transaction: 'each' });
    const sql = await ds.driver.createSchemaBuilder().log();
    return sql.upQueries.map((q) => q.query);
  } finally {
    await ds.destroy();
  }
}

if (require.main === module) {
  const url = process.env.DATABASE_URL;
  if (!url) {
    console.error('DATABASE_URL é obrigatória');
    process.exit(2);
  }
  verificarDrift(url, process.argv.includes('--aplicar-migracoes'))
    .then((diferencas) => {
      if (diferencas.length === 0) {
        console.log('Sem drift: entidades e migrações coincidem.');
        return;
      }
      console.error(
        `DRIFT: ${diferencas.length} diferença(s) entre entidades e migrações:`,
      );
      for (const d of diferencas) console.error(`  ${d}`);
      process.exit(1);
    })
    .catch((e: unknown) => {
      console.error(e);
      process.exit(2);
    });
}
