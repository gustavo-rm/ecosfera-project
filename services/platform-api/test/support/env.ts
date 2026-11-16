import { randomBytes } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

/** Variáveis do ambiente de teste. Segredos aleatórios por execução: nada fixo no repositório. */
const arquivo = join(__dirname, '..', '..', '.ambiente-de-teste.json');
if (existsSync(arquivo)) {
  const amb = JSON.parse(readFileSync(arquivo, 'utf8')) as {
    urlAdmin: string;
    urlApp: string;
    urlRedis: string;
  };
  process.env.DATABASE_URL = amb.urlApp;
  process.env.TEST_DATABASE_ADMIN_URL = amb.urlAdmin;
  process.env.REDIS_URL = amb.urlRedis;
}
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = process.env.LOG_LEVEL_TESTE ?? 'silent';
process.env.JWT_ACCESS_SECRET = randomBytes(48).toString('base64');
process.env.SERVICE_TOKEN_SECRET = randomBytes(48).toString('base64');
process.env.DATA_ENCRYPTION_KEY = randomBytes(32).toString('base64');
process.env.PSEUDONYM_KEY = randomBytes(48).toString('base64');
process.env.REDIS_KEY_PREFIX = `teste:${randomBytes(4).toString('hex')}:`;
process.env.ADAPTER_STORAGE = process.env.ADAPTER_STORAGE ?? 'fake';
process.env.FAKE_STORAGE_DIR = join(
  '/tmp',
  `ecosfera-teste-${randomBytes(4).toString('hex')}`,
);
process.env.RATE_LIMIT_IP_PER_MINUTE = '100000';
process.env.RATE_LIMIT_AUTH_IP_PER_MINUTE = '100000';
process.env.RATE_LIMIT_LOGIN_PER_MINUTE = '5';
process.env.EVENTS_CONSUMER_ENABLED =
  process.env.EVENTS_CONSUMER_ENABLED ?? 'true';
