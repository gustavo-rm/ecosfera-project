import {
  exigirUrlExterna,
  ipInterno,
  PADRAO_VARIAVEL_DE_SEGREDO_OIDC,
} from './url-externa';

describe('Proteção contra SSRF e roubo de segredo na federação', () => {
  it.each([
    '127.0.0.1',
    '10.1.2.3',
    '172.20.0.1',
    '192.168.0.10',
    '169.254.169.254',
    '::1',
    'fd00::1',
    '::ffff:127.0.0.1',
  ])('%s é interno', (ip) => expect(ipInterno(ip)).toBe(true));
  it('IP público não é interno', () =>
    expect(ipInterno('8.8.8.8')).toBe(false));
  it('em produção recusa http, metadados da nuvem e localhost', async () => {
    await expect(
      exigirUrlExterna('http://idp.escola.br', true),
    ).rejects.toThrow(/https/);
    await expect(
      exigirUrlExterna('https://169.254.169.254/latest', true),
    ).rejects.toThrow(/interno/);
    await expect(
      exigirUrlExterna('https://127.0.0.1:8443', true),
    ).rejects.toThrow(/interno/);
  });
  it('fora de produção aceita o provedor local de teste', async () => {
    await expect(
      exigirUrlExterna('http://127.0.0.1:9999', false),
    ).resolves.toBeUndefined();
  });
  it('só aceita variáveis com prefixo OIDC_CLIENT_SECRET_', () => {
    for (const n of [
      'JWT_ACCESS_SECRET',
      'SERVICE_TOKEN_SECRET',
      'DATABASE_URL',
      'DATA_ENCRYPTION_KEY',
      'PSEUDONYM_KEY',
    ])
      expect(PADRAO_VARIAVEL_DE_SEGREDO_OIDC.test(n)).toBe(false);
    expect(
      PADRAO_VARIAVEL_DE_SEGREDO_OIDC.test('OIDC_CLIENT_SECRET_ESCOLA_A'),
    ).toBe(true);
  });
});
