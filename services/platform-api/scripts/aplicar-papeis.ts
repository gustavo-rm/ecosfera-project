/** Aplica db/papeis-por-schema.sql com uma URL de administrador (DATABASE_ADMIN_URL). */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { Client } from 'pg';

const url = process.env.DATABASE_ADMIN_URL;
if (!url) {
  console.error('Defina DATABASE_ADMIN_URL (dono do banco).');
  process.exit(2);
}
const c = new Client({ connectionString: url });
c.connect()
  .then(() =>
    c.query(
      readFileSync(
        join(__dirname, '..', 'db', 'papeis-por-schema.sql'),
        'utf8',
      ),
    ),
  )
  .then(() =>
    console.log(
      'Papéis aplicados. Defina as senhas com ALTER ROLE ... PASSWORD (do cofre).',
    ),
  )
  .catch((e: unknown) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => void c.end());
