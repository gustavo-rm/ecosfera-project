import { jwtVerify, SignJWT } from 'jose';

import { MAILER } from '../../src/modules/identity/domain/portas';
import {
  API,
  type AppDeTeste,
  bearer,
  criarApp,
  criarEscola,
  criarUsuario,
  login,
  SENHA_PADRAO,
  type UsuarioDeTeste,
} from '../support/app';

describe('Autenticação (RF-003, RF-006, TASK-0026)', () => {
  let t: AppDeTeste;
  let escola: string;
  let prof: UsuarioDeTeste;

  beforeAll(async () => {
    t = await criarApp();
    escola = await criarEscola(t);
    prof = await criarUsuario(t, 'teacher', escola);
  });
  afterAll(() => t.fechar());

  const auditoria = async (acao: string) =>
    await t.ds.query(
      `SELECT * FROM platform.audit_log WHERE action = $1 ORDER BY created_at DESC LIMIT 5`,
      [acao],
    );

  it('login válido devolve access token, perfil e refresh em cookie httpOnly', async () => {
    const r = await t
      .http()
      .post(`${API}/auth/login`)
      .send({ email: prof.email, senha: SENHA_PADRAO });
    expect(r.status).toBe(200);
    expect(r.body.tokenType).toBe('Bearer');
    expect(r.body.refreshToken).toBeUndefined();
    expect(r.body.perfil).toMatchObject({
      id: prof.id,
      role: 'teacher',
      schoolId: escola,
    });
    const cookie = String(r.headers['set-cookie']);
    expect(cookie).toMatch(/ecosfera_refresh=/);
    expect(cookie).toMatch(/HttpOnly/);
    expect(cookie).toMatch(/SameSite=Strict/);
    expect(cookie).toMatch(/Path=\/platform\/api\/v1\/auth/);
    expect(r.headers['cache-control']).toBe('no-store');
  });

  it('senha errada e e-mail inexistente recebem a MESMA resposta (sem enumeração) e são registrados', async () => {
    const a = await t
      .http()
      .post(`${API}/auth/login`)
      .send({ email: prof.email, senha: 'errada-123456' });
    const b = await t
      .http()
      .post(`${API}/auth/login`)
      .send({
        email: `ninguem.${Date.now()}@teste.local`,
        senha: 'errada-123456',
      });
    expect(a.status).toBe(401);
    expect(b.status).toBe(401);
    expect(a.body.detail).toBe(b.body.detail);
    expect(a.body.type).toBe('/errors/unauthenticated');
    expect(a.body.traceId).toMatch(/^[0-9a-f]{32}$/);
    const reg = await auditoria('auth.login_failed');
    expect(reg.length).toBeGreaterThanOrEqual(2);
    expect(reg[0].outcome).toBe('denied');
    expect(JSON.stringify(reg)).not.toContain(prof.email);
  });

  it('excesso de tentativas na mesma conta → 429 com Retry-After', async () => {
    const alvo = await criarUsuario(t, 'student', escola, { isMinor: false });
    const codigos: number[] = [];
    for (let i = 0; i < 7; i++) {
      codigos.push(
        (
          await t
            .http()
            .post(`${API}/auth/login`)
            .send({ email: alvo.email, senha: 'errada-123456' })
        ).status,
      );
    }
    expect(codigos.slice(0, 5)).toEqual([401, 401, 401, 401, 401]);
    expect(codigos.slice(5)).toEqual([429, 429]);
    // Bloqueada: nem a senha certa entra enquanto durar a janela (15 min).
    const ultimo = await t
      .http()
      .post(`${API}/auth/login`)
      .send({ email: alvo.email, senha: SENHA_PADRAO });
    expect(ultimo.status).toBe(429);
    expect(ultimo.body.type).toBe('/errors/rate-limited');
    expect(Number(ultimo.headers['retry-after'])).toBeGreaterThan(0);
  });

  it('refresh rotativo: o refresh usado não vale de novo, e reusá-lo revoga a família inteira', async () => {
    const s = await login(t, prof.email, SENHA_PADRAO);
    const r1 = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('X-Refresh-Transport', 'body')
      .send({ refreshToken: s.refresh });
    expect(r1.status).toBe(200);
    const novoRefresh = r1.body.refreshToken as string;
    expect(novoRefresh).not.toBe(s.refresh);
    // Reuso do refresh antigo: detectado.
    const reuso = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('X-Refresh-Transport', 'body')
      .send({ refreshToken: s.refresh });
    expect(reuso.status).toBe(401);
    expect(reuso.body.detail).toMatch(/reutilizado/);
    // A família foi revogada: o refresh novo e o access token da sessão também morrem.
    const comNovo = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('X-Refresh-Transport', 'body')
      .send({ refreshToken: novoRefresh });
    expect(comNovo.status).toBe(401);
    const me = await t
      .http()
      .get(`${API}/auth/me`)
      .set('Authorization', `Bearer ${r1.body.accessToken as string}`);
    expect(me.status).toBe(401);
    expect((await auditoria('auth.refresh_reuse_detected'))[0].outcome).toBe(
      'denied',
    );
  });

  it('refresh pelo cookie funciona e é rotacionado', async () => {
    const r = await t
      .http()
      .post(`${API}/auth/login`)
      .send({ email: prof.email, senha: SENHA_PADRAO });
    const cookie = (r.headers['set-cookie'] as unknown as string[])[0].split(
      ';',
    )[0];
    const r2 = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('Cookie', cookie)
      .send({});
    expect(r2.status).toBe(200);
    expect(String(r2.headers['set-cookie'])).not.toContain(cookie);
  });

  it('logout invalida o access token na hora', async () => {
    const s = await login(t, prof.email, SENHA_PADRAO);
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set(...bearer(s))
      ).status,
    ).toBe(200);
    expect(
      (
        await t
          .http()
          .post(`${API}/auth/logout`)
          .set(...bearer(s))
      ).status,
    ).toBe(204);
    const depois = await t
      .http()
      .get(`${API}/auth/me`)
      .set(...bearer(s));
    expect(depois.status).toBe(401);
    expect(depois.body.detail).toMatch(/revogada|encerrada/);
  });

  it('token expirado → 401 "Token expirado"', async () => {
    const chave = new TextEncoder().encode(t.config.JWT_ACCESS_SECRET);
    const { payload } = await jwtVerify(prof.token, chave);
    const velho = await new SignJWT({ ...payload })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt(Math.floor(Date.now() / 1000) - 3600)
      .setExpirationTime(Math.floor(Date.now() / 1000) - 60)
      .sign(chave);
    const r = await t
      .http()
      .get(`${API}/auth/me`)
      .set('Authorization', `Bearer ${velho}`);
    expect(r.status).toBe(401);
    expect(r.body.detail).toBe('Token expirado');
  });

  it('token assinado com outro segredo ou alg "none" → 401', async () => {
    const falso = await new SignJWT({ typ: 'access', role: 'admin', sid: 'x' })
      .setProtectedHeader({ alg: 'HS256' })
      .setSubject(prof.id)
      .setExpirationTime('5m')
      .sign(
        new TextEncoder().encode('outro-segredo-qualquer-com-32-caracteres!!'),
      );
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set('Authorization', `Bearer ${falso}`)
      ).status,
    ).toBe(401);
    const semAssinatura = `${Buffer.from('{"alg":"none"}').toString('base64url')}.${Buffer.from(JSON.stringify({ sub: prof.id, role: 'admin', typ: 'access' })).toString('base64url')}.`;
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set('Authorization', `Bearer ${semAssinatura}`)
      ).status,
    ).toBe(401);
  });

  it('redefinição de senha: 202 sempre, código de uso único, encerra sessões', async () => {
    const alvo = await criarUsuario(t, 'coordinator', escola);
    const caixa = t.app.get(MAILER).caixa;
    const antes = caixa.length;
    expect(
      (
        await t
          .http()
          .post(`${API}/auth/password/forgot`)
          .send({ email: `nao.existe.${Date.now()}@x.local` })
      ).status,
    ).toBe(202);
    expect(caixa.length).toBe(antes);
    expect(
      (
        await t
          .http()
          .post(`${API}/auth/password/forgot`)
          .send({ email: alvo.email })
      ).status,
    ).toBe(202);
    const msg = caixa[caixa.length - 1];
    expect(msg.para).toBe(alvo.email);
    const codigo = /: (\S+)$/.exec(msg.texto)![1];
    const fraca = await t
      .http()
      .post(`${API}/auth/password/reset`)
      .send({ token: codigo, newPassword: 'curta' });
    expect(fraca.status).toBe(422);
    const ok = await t
      .http()
      .post(`${API}/auth/password/reset`)
      .send({ token: codigo, newPassword: 'Nova-senha-segura-42' });
    expect(ok.status).toBe(204);
    expect(
      (
        await t
          .http()
          .post(`${API}/auth/password/reset`)
          .send({ token: codigo, newPassword: 'Outra-senha-segura-42' })
      ).status,
    ).toBe(400);
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set(...bearer(alvo))
      ).status,
    ).toBe(401);
    await expect(
      login(t, alvo.email, 'Nova-senha-segura-42'),
    ).resolves.toBeDefined();
  });
});
