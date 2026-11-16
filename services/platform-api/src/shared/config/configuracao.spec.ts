import { randomBytes } from 'node:crypto';

import {
  adaptadoresFalsosAtivos,
  carregarConfiguracao,
  ErroDeConfiguracao,
} from './configuracao';

const base = () => ({
  DATABASE_URL: 'postgresql://x@y/z',
  REDIS_URL: 'redis://r',
  JWT_ACCESS_SECRET: 'a'.repeat(40),
  SERVICE_TOKEN_SECRET: 'b'.repeat(40),
  DATA_ENCRYPTION_KEY: randomBytes(32).toString('base64'),
  PSEUDONYM_KEY: 'c'.repeat(40),
});

describe('Configuração validada no boot', () => {
  it('falta de variável obrigatória dá erro claro, sem ecoar valores', () => {
    const env = { ...base(), JWT_ACCESS_SECRET: 'curto' } as Record<
      string,
      string
    >;
    delete env.DATABASE_URL;
    try {
      carregarConfiguracao(env);
      fail('deveria falhar');
    } catch (e) {
      expect(e).toBeInstanceOf(ErroDeConfiguracao);
      const m = (e as Error).message;
      expect(m).toContain('DATABASE_URL');
      expect(m).toContain('JWT_ACCESS_SECRET');
      expect(m).not.toContain('curto');
    }
  });

  it('em desenvolvimento os fakes são permitidos e anunciados', () => {
    const c = carregarConfiguracao({ ...base(), ADAPTER_STORAGE: 'fake' });
    expect(adaptadoresFalsosAtivos(c)).toEqual([
      'SimulationGateway',
      'TutorGateway',
      'Mailer',
      'ObjectStorage',
    ]);
  });

  it('FAKES NÃO LIGAM EM PRODUÇÃO: o boot falha para cada adaptador falso', () => {
    expect(() =>
      carregarConfiguracao({ ...base(), NODE_ENV: 'production' }),
    ).toThrow(/ADAPTER_SIMULATION=fake é proibido em produção/);
    const msg = (() => {
      try {
        carregarConfiguracao({
          ...base(),
          NODE_ENV: 'production',
          ADAPTER_STORAGE: 'fake',
        });
      } catch (e) {
        return (e as Error).message;
      }
      return '';
    })();
    for (const a of [
      'ADAPTER_SIMULATION',
      'ADAPTER_TUTOR',
      'ADAPTER_MAILER',
      'ADAPTER_STORAGE',
    ])
      expect(msg).toContain(`${a}=fake é proibido`);
  });

  it('produção com adaptadores reais sobe, com HTTPS e cookie Secure obrigatórios', () => {
    const c = carregarConfiguracao({
      ...base(),
      NODE_ENV: 'production',
      ADAPTER_SIMULATION: 'http',
      AI_SIM_BASE_URL: 'http://ai:8000',
      ADAPTER_TUTOR: 'http',
      ADAPTER_MAILER: 'disabled',
      ADAPTER_STORAGE: 's3',
    });
    expect(c.REQUIRE_HTTPS).toBe(true);
    expect(c.COOKIE_SECURE).toBe(true);
    expect(adaptadoresFalsosAtivos(c)).toEqual([]);
    expect(() =>
      carregarConfiguracao({
        ...base(),
        NODE_ENV: 'production',
        ADAPTER_SIMULATION: 'http',
        AI_SIM_BASE_URL: 'http://ai',
        ADAPTER_TUTOR: 'http',
        ADAPTER_MAILER: 'disabled',
        REQUIRE_HTTPS: 'false',
      }),
    ).toThrow(/REQUIRE_HTTPS/);
  });

  it('http sem AI_SIM_BASE_URL em produção falha', () => {
    expect(() =>
      carregarConfiguracao({
        ...base(),
        NODE_ENV: 'production',
        ADAPTER_SIMULATION: 'http',
        ADAPTER_TUTOR: 'http',
        ADAPTER_MAILER: 'disabled',
      }),
    ).toThrow(/AI_SIM_BASE_URL/);
  });
});
