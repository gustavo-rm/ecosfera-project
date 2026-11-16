import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { subirAmbiente } from './containers';

export const ARQUIVO_AMBIENTE = join(__dirname, '..', '..', '.ambiente-de-teste.json');

export default async function globalSetup(): Promise<void> {
  const amb = await subirAmbiente();
  (globalThis as Record<string, unknown>).__AMBIENTE__ = amb;
  writeFileSync(
    ARQUIVO_AMBIENTE,
    JSON.stringify({ urlAdmin: amb.urlAdmin, urlApp: amb.urlApp, urlRedis: amb.urlRedis }),
  );
}
