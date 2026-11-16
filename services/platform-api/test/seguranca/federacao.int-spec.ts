import { generateKeyPair } from 'jose';

import { API, type AppDeTeste, bearer, criarApp, criarEscola, criarUsuario, type UsuarioDeTeste } from '../support/app';
import { ProvedorDeTeste } from '../support/provedor-de-teste';

const LTI = 'https://purl.imsglobal.org/spec/lti/claim/';

describe('Federação: LTI 1.3 e OIDC contra provedor LOCAL de teste (RF-009, TASK-0028)', () => {
  let t: AppDeTeste;
  let idp: ProvedorDeTeste;
  let escola: string;
  let admin: UsuarioDeTeste;

  beforeAll(async () => {
    idp = new ProvedorDeTeste();
    await idp.iniciar();
    t = await criarApp();
    escola = await criarEscola(t);
    admin = await criarUsuario(t, 'admin', escola);
    const r = await t.http().post(`${API}/admin/lti/platforms`).set(...bearer(admin)).send({
      issuer: idp.url, clientId: idp.clientId, deploymentId: 'dep-1', authLoginUrl: `${idp.url}/authorize`, jwksUrl: `${idp.url}/jwks`,
    });
    expect(r.status).toBe(201);
    const o = await t.http().post(`${API}/admin/oidc/providers`).set(...bearer(admin)).send({ slug: 'idp-escola', issuer: idp.url, clientId: idp.clientId, defaultRole: 'teacher', allowProvisioning: true });
    expect(o.status).toBe(201);
  });
  afterAll(async () => {
    await t.fechar();
    await idp.parar();
  });

  async function iniciarLti(): Promise<{ state: string; nonce: string }> {
    const r = await t.http().get(`${API}/auth/lti/login`).query({ iss: idp.url, login_hint: 'u1', target_link_uri: 'http://x' });
    expect(r.status).toBe(302);
    const loc = new URL(r.headers.location as string);
    expect(loc.searchParams.get('response_mode')).toBe('form_post');
    return { state: loc.searchParams.get('state')!, nonce: loc.searchParams.get('nonce')! };
  }

  const claimsLti = (nonce: string, sub: string, papel: string, extra: Record<string, unknown> = {}) => ({
    sub, nonce, given_name: 'Ana',
    [`${LTI}version`]: '1.3.0', [`${LTI}message_type`]: 'LtiResourceLinkRequest', [`${LTI}deployment_id`]: 'dep-1',
    [`${LTI}roles`]: [`http://purl.imsglobal.org/vocab/lis/v2/membership#${papel}`],
    [`${LTI}context`]: { id: 'curso-42', title: 'Ciências 7º ano' },
    ...extra,
  });

  it('launch do professor importa a turma; launch do aluno entra nela como MENOR restrito', async () => {
    let s = await iniciarLti();
    const prof = await t.http().post(`${API}/auth/lti/launch`).type('form').set('X-Refresh-Transport', 'body')
      .send({ id_token: await idp.assinar(claimsLti(s.nonce, 'prof-1', 'Instructor')), state: s.state });
    expect(prof.status).toBe(200);
    expect(prof.body.turma.name).toBe('Ciências 7º ano');
    const me = await t.http().get(`${API}/auth/me`).set('Authorization', `Bearer ${prof.body.accessToken as string}`);
    expect(me.body).toMatchObject({ role: 'teacher', schoolId: escola });
    expect(me.body.email).toMatch(/@federado\.invalid$/);

    s = await iniciarLti();
    const aluno = await t.http().post(`${API}/auth/lti/launch`).type('form')
      .send({ id_token: await idp.assinar(claimsLti(s.nonce, 'aluno-1', 'Learner')), state: s.state });
    expect(aluno.status).toBe(200);
    expect(aluno.body.turma.id).toBe(prof.body.turma.id);
    const alunos = await t.http().get(`${API}/classes/${prof.body.turma.id as string}/students`).set('Authorization', `Bearer ${prof.body.accessToken as string}`);
    expect(alunos.body.items).toHaveLength(1);
    expect(alunos.body.items[0].isMinor).toBe(true);
    const planeta = await t.http().post(`${API}/planets`).set('Authorization', `Bearer ${aluno.body.accessToken as string}`).send({ params: {} });
    expect(planeta.body.type).toBe('/errors/consent-required');
  });

  it('administrador do LMS não vira admin da escola (mapeado para coordenador)', async () => {
    const s = await iniciarLti();
    const r = await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: await idp.assinar(claimsLti(s.nonce, 'adm-lms', 'Administrator')), state: s.state });
    const me = await t.http().get(`${API}/auth/me`).set('Authorization', `Bearer ${r.body.accessToken as string}`);
    expect(me.body.role).toBe('coordinator');
  });

  it('recusa: estado reutilizado, nonce errado, deployment errado, assinatura de outra chave', async () => {
    const s = await iniciarLti();
    const token = await idp.assinar(claimsLti(s.nonce, 'aluno-2', 'Learner'));
    expect((await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: token, state: s.state })).status).toBe(200);
    expect((await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: token, state: s.state })).status).toBe(401);

    const s2 = await iniciarLti();
    expect((await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: await idp.assinar(claimsLti('outro-nonce', 'x', 'Learner')), state: s2.state })).status).toBe(401);

    const s3 = await iniciarLti();
    expect((await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: await idp.assinar(claimsLti(s3.nonce, 'x', 'Learner', { [`${LTI}deployment_id`]: 'dep-2' })), state: s3.state })).status).toBe(401);

    const s4 = await iniciarLti();
    const { privateKey } = await generateKeyPair('RS256');
    const forjado = await idp.assinar(claimsLti(s4.nonce, 'x', 'Learner'), privateKey);
    const r = await t.http().post(`${API}/auth/lti/launch`).type('form').send({ id_token: forjado, state: s4.state });
    expect(r.status).toBe(401);
    const aud = await t.ds.query(`SELECT 1 FROM platform.audit_log WHERE action = 'auth.lti_launch_failed'`);
    expect(aud.length).toBeGreaterThan(0);
  });

  it('OIDC: código + PKCE abre sessão; callback repetido é recusado', async () => {
    const a = await t.http().get(`${API}/auth/oidc/idp-escola/authorize`);
    expect(a.status).toBe(302);
    const loc = new URL(a.headers.location as string);
    expect(loc.searchParams.get('code_challenge_method')).toBe('S256');
    const state = loc.searchParams.get('state')!;
    const code = idp.emitirCodigo({ sub: 'prof-oidc', nonce: loc.searchParams.get('nonce')!, name: 'Marina' });
    const r = await t.http().get(`${API}/auth/oidc/idp-escola/callback`).query({ code, state }).set('X-Refresh-Transport', 'body');
    expect(r.status).toBe(200);
    expect(r.body.accessToken).toBeDefined();
    expect((await t.http().get(`${API}/auth/oidc/idp-escola/callback`).query({ code, state })).status).toBe(401);
  });

  it('só admin da escola registra plataformas', async () => {
    const prof = await criarUsuario(t, 'teacher', escola);
    expect((await t.http().post(`${API}/admin/lti/platforms`).set(...bearer(prof)).send({ issuer: 'x', clientId: 'y', deploymentId: 'z', authLoginUrl: 'http://a.b', jwksUrl: 'http://a.b' })).status).toBe(403);
  });
});
