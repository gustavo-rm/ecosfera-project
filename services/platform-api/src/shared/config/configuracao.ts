import { z } from 'zod';

/**
 * Configuração do platform-api, validada no boot.
 * Falta de variável ou valor inválido derruba o processo com mensagem clara.
 * Nenhum segredo tem valor padrão.
 */
const booleano = z
  .enum(['true', 'false', '1', '0'])
  .transform((v) => v === 'true' || v === '1');

const listaSeparadaPorVirgula = z
  .string()
  .transform((v) =>
    v
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0),
  );

/** Segredo com pelo menos 32 caracteres (256 bits se for aleatório em base64/hex). */
const segredo = (nome: string) =>
  z.string().min(32, `${nome} precisa ter pelo menos 32 caracteres`);

export const esquemaConfiguracao = z
  .object({
    NODE_ENV: z
      .enum(['development', 'test', 'production'])
      .default('development'),
    PORT: z.coerce.number().int().min(1).max(65535).default(3000),
    LOG_LEVEL: z
      .enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent'])
      .default('info'),
    /** Atrás de balanceador/proxy reverso que termina TLS. */
    TRUST_PROXY: booleano.default(false),
    /** Recusa requisições que não chegaram por HTTPS (X-Forwarded-Proto). */
    REQUIRE_HTTPS: booleano.optional(),
    CORS_ORIGINS: listaSeparadaPorVirgula.default([]),
    BODY_LIMIT_BYTES: z.coerce.number().int().positive().default(256 * 1024),

    DATABASE_URL: z.string().min(1, 'DATABASE_URL é obrigatória'),
    DB_SSL: booleano.default(false),
    DB_LOGGING: booleano.default(false),
    DB_POOL_MAX: z.coerce.number().int().positive().default(10),

    REDIS_URL: z.string().min(1, 'REDIS_URL é obrigatória'),
    REDIS_KEY_PREFIX: z.string().default('ecosfera:platform:'),

    JWT_ACCESS_SECRET: segredo('JWT_ACCESS_SECRET'),
    JWT_ISSUER: z.string().default('ecosfera-platform-api'),
    ACCESS_TOKEN_TTL_SECONDS: z.coerce.number().int().min(60).default(600),
    REFRESH_TOKEN_TTL_SECONDS: z.coerce
      .number()
      .int()
      .min(300)
      .default(7 * 24 * 3600),
    COOKIE_SECURE: booleano.optional(),
    /** Segredo das credenciais de serviço (ai-sim-service → platform-api). */
    SERVICE_TOKEN_SECRET: segredo('SERVICE_TOKEN_SECRET'),
    SERVICE_ALLOWED_NAMES: listaSeparadaPorVirgula.default(['ai-sim-service']),
    /** Chave AES-256-GCM (32 bytes em base64) para campos sensíveis em repouso. */
    DATA_ENCRYPTION_KEY: z
      .string()
      .refine(
        (v) => Buffer.from(v, 'base64').length === 32,
        'DATA_ENCRYPTION_KEY precisa ser 32 bytes em base64',
      ),
    /** Chave HMAC para pseudônimos estáveis (auditoria após exclusão). */
    PSEUDONYM_KEY: segredo('PSEUDONYM_KEY'),

    ADAPTER_SIMULATION: z.enum(['fake', 'http']).default('fake'),
    ADAPTER_TUTOR: z.enum(['fake', 'http']).default('fake'),
    ADAPTER_MAILER: z.enum(['fake', 'disabled']).default('fake'),
    ADAPTER_STORAGE: z.enum(['fake', 's3']).default('s3'),
    AI_SIM_BASE_URL: z.string().url().optional(),
    AI_SIM_TIMEOUT_MS: z.coerce.number().int().positive().default(3000),
    AI_SIM_RETRIES: z.coerce.number().int().min(0).max(3).default(1),

    S3_ENDPOINT: z.string().url().optional(),
    S3_PUBLIC_ENDPOINT: z.string().url().optional(),
    S3_REGION: z.string().default('us-east-1'),
    S3_ACCESS_KEY: z.string().optional(),
    S3_SECRET_KEY: z.string().optional(),
    S3_FORCE_PATH_STYLE: booleano.default(true),
    S3_BUCKET_EXPORTS: z.string().default('exports'),
    S3_BUCKET_DATASETS: z.string().default('datasets'),
    FAKE_STORAGE_DIR: z.string().default('/tmp/ecosfera-platform-storage'),
    SIGNED_URL_TTL_SECONDS: z.coerce.number().int().min(1).max(3600).default(300),
    EXPORT_MAX_BYTES: z.coerce.number().int().positive().default(10 * 1024 * 1024),

    RATE_LIMIT_LOGIN_PER_MINUTE: z.coerce.number().int().positive().default(5),
    RATE_LIMIT_IP_PER_MINUTE: z.coerce.number().int().positive().default(300),
    RATE_LIMIT_AUTH_IP_PER_MINUTE: z.coerce.number().int().positive().default(30),

    PUBLIC_BASE_URL: z.string().url().default('http://localhost:3000'),
    METRICS_TOKEN: z.string().min(16).optional(),
    OTEL_EXPORTER_OTLP_ENDPOINT: z.string().url().optional(),
    OTEL_SERVICE_NAME: z.string().default('platform-api'),

    EVENTS_STREAM_PLATFORM: z.string().default('ecosfera.events.platform'),
    EVENTS_STREAM_ASSESSMENT: z.string().default('ecosfera.events.assessment'),
    EVENTS_CONSUMER_GROUP: z.string().default('platform-api'),
    EVENTS_CONSUMER_ENABLED: booleano.default(true),
    OUTBOX_RELAY_ENABLED: booleano.default(true),
    RETENTION_JOB_ENABLED: booleano.default(false),

    WS_MAX_BUFFERED_BYTES: z.coerce.number().int().positive().default(1024 * 1024),
    WS_REPLAY_SIZE: z.coerce.number().int().min(0).default(50),
    TICK_SYNC_MAX_STEPS: z.coerce.number().int().positive().default(10),
  })
  .superRefine((c, ctx) => {
    if (c.NODE_ENV !== 'production') return;
    // Princípio 6: fakes nunca em produção.
    const fakes = (
      [
        ['ADAPTER_SIMULATION', c.ADAPTER_SIMULATION],
        ['ADAPTER_TUTOR', c.ADAPTER_TUTOR],
        ['ADAPTER_MAILER', c.ADAPTER_MAILER],
        ['ADAPTER_STORAGE', c.ADAPTER_STORAGE],
      ] as const
    ).filter(([, v]) => v === 'fake');
    for (const [nome] of fakes) {
      ctx.addIssue({
        code: 'custom',
        path: [nome],
        message: `${nome}=fake é proibido em produção (adaptador falso)`,
      });
    }
    if (c.REQUIRE_HTTPS === false) {
      ctx.addIssue({
        code: 'custom',
        path: ['REQUIRE_HTTPS'],
        message: 'REQUIRE_HTTPS não pode ser false em produção',
      });
    }
    if (c.COOKIE_SECURE === false) {
      ctx.addIssue({
        code: 'custom',
        path: ['COOKIE_SECURE'],
        message: 'COOKIE_SECURE não pode ser false em produção',
      });
    }
    if (c.ADAPTER_SIMULATION === 'http' && !c.AI_SIM_BASE_URL) {
      ctx.addIssue({
        code: 'custom',
        path: ['AI_SIM_BASE_URL'],
        message: 'AI_SIM_BASE_URL é obrigatória com ADAPTER_SIMULATION=http',
      });
    }
  })
  .transform((c) => ({
    ...c,
    REQUIRE_HTTPS: c.REQUIRE_HTTPS ?? c.NODE_ENV === 'production',
    COOKIE_SECURE: c.COOKIE_SECURE ?? c.NODE_ENV === 'production',
  }));

export type Configuracao = z.infer<typeof esquemaConfiguracao>;

export const CONFIGURACAO = Symbol('CONFIGURACAO');

export class ErroDeConfiguracao extends Error {
  constructor(public readonly problemas: string[]) {
    super(
      `Configuração inválida do platform-api:\n${problemas.map((p) => `  - ${p}`).join('\n')}`,
    );
    this.name = 'ErroDeConfiguracao';
  }
}

/** Valida o ambiente. Nunca inclui valores de variáveis na mensagem de erro. */
export function carregarConfiguracao(
  env: Record<string, string | undefined> = process.env,
): Configuracao {
  const resultado = esquemaConfiguracao.safeParse(env);
  if (!resultado.success) {
    throw new ErroDeConfiguracao(
      resultado.error.issues.map(
        (i) => `${i.path.join('.') || '(raiz)'}: ${i.message}`,
      ),
    );
  }
  return resultado.data;
}

/** Lista os adaptadores falsos ligados (para log de inicialização e /ready). */
export function adaptadoresFalsosAtivos(c: Configuracao): string[] {
  const lista: string[] = [];
  if (c.ADAPTER_SIMULATION === 'fake') lista.push('SimulationGateway');
  if (c.ADAPTER_TUTOR === 'fake') lista.push('TutorGateway');
  if (c.ADAPTER_MAILER === 'fake') lista.push('Mailer');
  if (c.ADAPTER_STORAGE === 'fake') lista.push('ObjectStorage');
  return lista;
}
