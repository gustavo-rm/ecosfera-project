import type { Redis } from 'ioredis';

import { ProjecaoDeAvaliacao } from '../../src/modules/assessment/application/projecao.service';
import { ChavesRedis } from '../../src/shared/redis/chaves';
import { REDIS } from '../../src/shared/redis/redis';
import {
  API,
  type AppDeTeste,
  bearer,
  criarApp,
  criarEscola,
  criarUsuario,
  login,
  SENHA_PADRAO,
  sufixo,
  type UsuarioDeTeste,
} from '../support/app';

/** Regressões dos achados da revisão independente (docs/backend/RELATORIO_FINAL.md, seção "Revisão independente"). */
describe('Regressões da revisão independente', () => {
  let t: AppDeTeste;
  let escola: string;
  let admin: UsuarioDeTeste;
  let coord: UsuarioDeTeste;
  let profA: UsuarioDeTeste;
  let profB: UsuarioDeTeste;
  let operador: UsuarioDeTeste;
  let resp: UsuarioDeTeste;

  beforeAll(async () => {
    t = await criarApp({ CONSENT_REQUIRE_APPROVED_TEXT: 'true' });
    escola = await criarEscola(t);
    admin = await criarUsuario(t, 'admin', escola);
    coord = await criarUsuario(t, 'coordinator', escola);
    profA = await criarUsuario(t, 'teacher', escola);
    profB = await criarUsuario(t, 'teacher', escola);
    operador = await criarUsuario(t, 'platform_admin', null);
    resp = await criarUsuario(t, 'guardian', null);
  });
  afterAll(() => t.fechar());

  it('achado 2: professor não captura aluno de outro professor matriculando-o; coordenação pode', async () => {
    const aluno = await criarUsuario(t, 'student', escola);
    const tA = (
      await t
        .http()
        .post(`${API}/classes`)
        .set(...bearer(profA))
        .send({ name: 'A' })
    ).body.id as string;
    const tB = (
      await t
        .http()
        .post(`${API}/classes`)
        .set(...bearer(profB))
        .send({ name: 'B' })
    ).body.id as string;
    expect(
      (
        await t
          .http()
          .post(`${API}/classes/${tA}/students`)
          .set(...bearer(profA))
          .send({ studentIds: [aluno.id] })
      ).status,
    ).toBe(200);
    const roubo = await t
      .http()
      .post(`${API}/classes/${tB}/students`)
      .set(...bearer(profB))
      .send({ studentIds: [aluno.id] });
    expect(roubo.status).toBe(403);
    expect(
      (
        await t
          .http()
          .get(`${API}/assessment/students/${aluno.id}/profile`)
          .set(...bearer(profB))
      ).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .post(`${API}/classes/${tB}/students`)
          .set(...bearer(coord))
          .send({ studentIds: [aluno.id] })
      ).status,
    ).toBe(200);
  });

  it('achado 3: professor não declara aluno maior de idade; voltar a aluno reativa a proteção', async () => {
    const r = await t
      .http()
      .post(`${API}/users`)
      .set(...bearer(profA))
      .send({
        name: 'x',
        email: `x.${sufixo()}@t.local`,
        role: 'student',
        isMinor: false,
        password: SENHA_PADRAO,
      });
    expect(r.status).toBe(403);
    const u = await criarUsuario(t, 'student', escola);
    await t
      .http()
      .patch(`${API}/users/${u.id}/role`)
      .set(...bearer(admin))
      .send({ role: 'teacher' });
    const volta = await t
      .http()
      .patch(`${API}/users/${u.id}/role`)
      .set(...bearer(admin))
      .send({ role: 'student' });
    expect(volta.body).toMatchObject({ role: 'student', isMinor: true });
  });

  it('achado 4: refresh contínuo não escapa de "revogar todas"; sessão tem vida máxima absoluta', async () => {
    const u = await criarUsuario(t, 'coordinator', escola);
    const s = await login(t, u.email, SENHA_PADRAO);
    const r1 = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('X-Refresh-Transport', 'body')
      .send({ refreshToken: s.refresh });
    const redis = t.app.get<Redis>(REDIS);
    const ch = t.app.get(ChavesRedis);
    expect(await redis.ttl(ch.sessoesDoUsuario(u.id))).toBeGreaterThan(
      t.config.REFRESH_TOKEN_TTL_SECONDS - 60,
    );
    // Vida máxima: sessão "criada" há 31 dias não renova mais.
    const sid = s.refresh.split('.')[0];
    await redis.hset(
      ch.sessao(sid),
      'criada',
      String(Date.now() - 31 * 24 * 3600 * 1000),
    );
    const velha = await t
      .http()
      .post(`${API}/auth/refresh`)
      .set('X-Refresh-Transport', 'body')
      .send({ refreshToken: r1.body.refreshToken });
    expect(velha.status).toBe(401);
  });

  it('achado 5: admin não troca o e-mail do responsável; troca de e-mail encerra sessões', async () => {
    const g = await criarUsuario(t, 'guardian', escola);
    expect(
      (
        await t
          .http()
          .patch(`${API}/users/${g.id}`)
          .set(...bearer(admin))
          .send({ email: `atacante.${sufixo()}@x.local` })
      ).status,
    ).toBe(403);
    const p = await criarUsuario(t, 'teacher', escola);
    expect(
      (
        await t
          .http()
          .patch(`${API}/users/${p.id}`)
          .set(...bearer(admin))
          .send({ email: `novo.${sufixo()}@x.local` })
      ).status,
    ).toBe(200);
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set(...bearer(p))
      ).status,
    ).toBe(401);
  });

  it('achado 7: em produção só vale aceite sobre texto APROVADO; operador publica a versão aprovada', async () => {
    const aluno = await criarUsuario(t, 'student', escola);
    await t
      .http()
      .post(`${API}/users/${aluno.id}/guardians`)
      .set(...bearer(admin))
      .send({ guardianUserId: resp.id });
    const placeholder = await t
      .http()
      .post(`${API}/users/${aluno.id}/consent`)
      .set(...bearer(resp))
      .send({
        purposes: ['platform_use'],
        textVersion: '0.1-placeholder',
        accepted: true,
      });
    expect(placeholder.status).toBe(422);
    const v = `1.0-${sufixo()}`;
    expect(
      (
        await t
          .http()
          .post(`${API}/admin/consent-texts`)
          .set(...bearer(admin))
          .send({
            purpose: 'platform_use',
            version: v,
            body: 'Texto aprovado pelo DPO (teste) com mais de vinte caracteres',
            reviewStatus: 'approved',
          })
      ).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .post(`${API}/admin/consent-texts`)
          .set(...bearer(operador))
          .send({
            purpose: 'platform_use',
            version: v,
            body: 'Texto aprovado pelo DPO (teste) com mais de vinte caracteres',
            reviewStatus: 'approved',
          })
      ).status,
    ).toBe(201);
    expect(
      (
        await t
          .http()
          .post(`${API}/users/${aluno.id}/consent`)
          .set(...bearer(resp))
          .send({ purposes: ['platform_use'], textVersion: v, accepted: true })
      ).status,
    ).toBe(201);
  });

  it('achado 1: clientSecretEnv só aceita variável OIDC_CLIENT_SECRET_* (nunca segredo do servidor)', async () => {
    for (const nome of [
      'JWT_ACCESS_SECRET',
      'SERVICE_TOKEN_SECRET',
      'DATABASE_URL',
    ]) {
      const r = await t
        .http()
        .post(`${API}/admin/oidc/providers`)
        .set(...bearer(admin))
        .send({
          slug: `x-${sufixo()}`,
          issuer: 'http://127.0.0.1:1',
          clientId: 'c',
          clientSecretEnv: nome,
          defaultRole: 'student',
        });
      expect([r.status, nome]).toEqual([422, nome]);
    }
  });

  it('achados 10 e 15: payload de sync e contextRef são validados; erro devolve só o tipo', async () => {
    const aluno = await criarUsuario(t, 'student', escola, { isMinor: false });
    const p = (
      await t
        .http()
        .post(`${API}/planets`)
        .set(...bearer(aluno))
        .send({ params: {} })
    ).body.planetId as string;
    const r = await t
      .http()
      .post(`${API}/planets/${p}/sync`)
      .set(...bearer(aluno))
      .send({
        actions: [
          {
            idempotencyKey: `k-${sufixo()}-1`,
            type: 'intervention',
            payload: {
              action: 'x',
              target: 't',
              cost: { actionPoints: 99999 },
            },
            clientTimestamp: '2026-01-01T00:00:00Z',
          },
          {
            idempotencyKey: `k-${sufixo()}-2`,
            type: 'tick',
            payload: { steps: 2, speed: 'muito' },
            clientTimestamp: '2026-01-01T00:00:01Z',
          },
          {
            idempotencyKey: `k-${sufixo()}-3`,
            type: 'intervention',
            payload: {
              action: 'NAO_EXISTE',
              target: 't',
              cost: { actionPoints: 1 },
            },
            clientTimestamp: '2026-01-01T00:00:02Z',
          },
        ],
      });
    expect(
      r.body.results.map((x: { status: string; error?: string }) => [
        x.status,
        x.error,
      ]),
    ).toEqual([
      ['rejected', '/errors/validation'],
      ['rejected', '/errors/validation'],
      ['rejected', '/errors/validation'],
    ]);
    const livre = await t
      .http()
      .post(`${API}/ai/explain`)
      .set(...bearer(aluno))
      .send({ planetId: p, contextRef: 'meu nome é Ana e moro na rua X' });
    expect(livre.status).toBe(422);
  });

  it('achado 14: evento ocorrido ANTES da concessão não é projetado', async () => {
    const aluno = await criarUsuario(t, 'student', escola);
    await t.ds.query(
      `INSERT INTO platform.consent (student_user_id, purpose, status, granted_at, text_version) VALUES ($1, 'learning_assessment', 'granted', now(), 'teste')`,
      [aluno.id],
    );
    const r = await t.app.get(ProjecaoDeAvaliacao).tratar({
      eventId: `antes-${aluno.id}`,
      type: 'EvidenciaGerada',
      version: 1,
      occurredAt: '2020-01-01T00:00:00Z',
      data: {
        studentId: aluno.id,
        competencyCode: 'CAUSE_EFFECT',
        type: 'x',
        payload: {},
      },
    });
    expect(r).toBe('skipped_no_consent');
  });

  it('RF-002: desativar conta encerra sessões e impede login; reativar devolve o acesso', async () => {
    const u = await criarUsuario(t, 'teacher', escola);
    expect(
      (
        await t
          .http()
          .patch(`${API}/users/${u.id}/status`)
          .set(...bearer(admin))
          .send({ status: 'disabled' })
      ).status,
    ).toBe(200);
    expect(
      (
        await t
          .http()
          .get(`${API}/auth/me`)
          .set(...bearer(u))
      ).status,
    ).toBe(401);
    await expect(login(t, u.email, SENHA_PADRAO)).rejects.toThrow(/401/);
    expect(
      (
        await t
          .http()
          .patch(`${API}/users/${u.id}/status`)
          .set(...bearer(admin))
          .send({ status: 'active' })
      ).status,
    ).toBe(200);
    await expect(login(t, u.email, SENHA_PADRAO)).resolves.toBeDefined();
  });
});
