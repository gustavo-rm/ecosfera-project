import { rmSync } from 'node:fs';

import type { Ambiente } from './containers';
import { ARQUIVO_AMBIENTE } from './global-setup';

export default async function globalTeardown(): Promise<void> {
  const amb = (globalThis as Record<string, unknown>).__AMBIENTE__ as Ambiente | undefined;
  await Promise.all([amb?.pg.stop(), amb?.redis.stop()]);
  rmSync(ARQUIVO_AMBIENTE, { force: true });
}
