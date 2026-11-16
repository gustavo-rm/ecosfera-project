import { ProjecaoDeAvaliacao } from '../../src/modules/assessment/application/projecao.service';
import { API, type AppDeTeste, bearer, criarApp, criarEscola, criarUsuario, login, SENHA_PADRAO, type UsuarioDeTeste } from '../support/app';

describe('LGPD (direitos do titular, retenção) e avaliação (pré/pós-teste, feedback, tutor)', () => {
  let t: AppDeTeste;
  let escola: string;
  let admin: UsuarioDeTeste;
  let prof: UsuarioDeTeste;
  let aluno: UsuarioDeTeste;
  let resp: UsuarioDeTeste;
  let operador: UsuarioDeTeste;
  let turma: string;
  let missao: string;
  let planeta: string;

  beforeAll(async () => {
    t = await criarApp();
    escola = await criarEscola(t);
    admin = await criarUsuario(t, 'admin', escola);
    prof = await criarUsuario(t, 'teacher', escola);
    aluno = await criarUsuario(t, 'student', escola, { nome: 'Sofia Teste' });
    resp = await criarUsuario(t, 'guardian', null);
    operador = await criarUsuario(t, 'platform_admin', null);
    await t.http().post(`${API}/users/${aluno.id}/guardians`).set(...bearer(admin)).send({ guardianUserId: resp.id });
    await t.http().post(`${API}/users/${aluno.id}/consent`).set(...bearer(resp)).send({ purposes: ['platform_use', 'learning_assessment'], textVersion: '0.1-placeholder', accepted: true });
    turma = (await t.http().post(`${API}/classes`).set(...bearer(prof)).send({ name: 'L1', trackLevel: 'medio' })).body.id;
    await t.http().post(`${API}/classes/${turma}/students`).set(...bearer(prof)).send({ studentIds: [aluno.id] });
    missao = (await t.http().post(`${API}/missions`).set(...bearer(prof)).send({ title: 'm', objective: 'o', trackLevel: 'medio', bnccCodes: ['EM13CNT203'], classIds: [turma] })).body.id;
    planeta = (await t.http().post(`${API}/planets`).set(...bearer(aluno)).send({ params: {}, missionId: missao })).body.planetId;
    const proj = t.app.get(ProjecaoDeAvaliacao);
    const agora = new Date().toISOString();
    await proj.tratar({ eventId: `ev-a-${aluno.id}`, type: 'EvidenciaGerada', version: 1, occurredAt: agora, data: { studentId: aluno.id, competencyCode: 'SYSTEMS_THINKING', type: 'intervention', payload: { a: 1 } } });
    await proj.tratar({ eventId: `ev-b-${aluno.id}`, type: 'CompetenciaAtualizada', version: 1, occurredAt: agora, data: { studentId: aluno.id, competencyCode: 'SYSTEMS_THINKING', probability: 0.7, uncertainty: 0.1 } });
  });
  afterAll(() => t.fechar());

  it('projeção é idempotente: o mesmo eventId não duplica', async () => {
    const r = await t.app.get(ProjecaoDeAvaliacao).tratar({ eventId: `ev-a-${aluno.id}`, type: 'EvidenciaGerada', version: 1, occurredAt: new Date().toISOString(), data: { studentId: aluno.id, competencyCode: 'SYSTEMS_THINKING', type: 'intervention', payload: {} } });
    expect(r).toBe('duplicate');
    const n = await t.ds.query(`SELECT count(*)::int AS n FROM platform.evidence WHERE student_user_id = $1`, [aluno.id]);
    expect(n[0].n).toBe(1);
  });

  it('estimativa mais antiga não sobrescreve a mais nova (ordem de chegada não importa)', async () => {
    await t.app.get(ProjecaoDeAvaliacao).tratar({ eventId: `ev-c-${aluno.id}`, type: 'CompetenciaAtualizada', version: 1, occurredAt: '2020-01-01T00:00:00Z', data: { studentId: aluno.id, competencyCode: 'SYSTEMS_THINKING', probability: 0.1 } });
    const p = await t.http().get(`${API}/assessment/students/${aluno.id}/profile`).set(...bearer(prof));
    expect(p.body.competencies[0].probability).toBe(0.7);
  });

  it('pré/pós-teste (RF-074): professor registra; aluno não registra nem lê', async () => {
    const r = await t.http().post(`${API}/assessment/students/${aluno.id}/assessments`).set(...bearer(prof)).send({ kind: 'pre_test', score: 42, competencyCode: 'SYSTEMS_THINKING', missionId: missao });
    expect(r.status).toBe(201);
    expect(r.body).toMatchObject({ kind: 'pre_test', score: 42, competencyCode: 'SYSTEMS_THINKING' });
    const l = await t.http().get(`${API}/assessment/students/${aluno.id}/assessments`).set(...bearer(prof));
    expect(l.body.items).toHaveLength(1);
    expect((await t.http().get(`${API}/assessment/students/${aluno.id}/assessments`).set(...bearer(aluno))).status).toBe(403);
  });

  it('feedback (RF-067): professor envia, aluno lê e marca como lido; texto fica cifrado no banco', async () => {
    const f = await t.http().post(`${API}/dashboard/students/${aluno.id}/feedback`).set(...bearer(prof)).send({ content: 'Ótima hipótese sobre o CO2!' });
    expect(f.status).toBe(201);
    const bruto = await t.ds.query(`SELECT content FROM platform.feedback WHERE id = $1`, [f.body.id]);
    expect(bruto[0].content).toMatch(/^v1:/);
    expect(bruto[0].content).not.toContain('CO2');
    const meus = await t.http().get(`${API}/feedback/me`).set(...bearer(aluno));
    expect(meus.body.items[0].content).toBe('Ótima hipótese sobre o CO2!');
    expect((await t.http().post(`${API}/feedback/${f.body.id as string}/read`).set(...bearer(aluno))).status).toBe(204);
    expect((await t.http().post(`${API}/feedback/${f.body.id as string}/read`).set(...bearer(prof))).status).toBe(403);
  });

  it('tutor: dica exige missão acessível; conselheiro responde marcado como simulado', async () => {
    const d = await t.http().post(`${API}/ai/hint`).set(...bearer(aluno)).send({ planetId: planeta, missionId: missao });
    expect(d.status).toBe(200);
    expect(d.body.hint).toContain('[SIMULADO]');
    const c = await t.http().post(`${API}/ai/advisor`).set(...bearer(aluno)).send({ role: 'ecologist', query: 'devo reflorestar?' });
    expect(c.body.advice).toContain('[SIMULADO]');
    expect((await t.http().get(`${API}/ai/adaptation/${aluno.id}`).set(...bearer(prof))).status).toBe(200);
  });

  it('direito de acesso: responsável recebe todos os dados; professor não', async () => {
    const r = await t.http().get(`${API}/users/${aluno.id}/data-export`).set(...bearer(resp));
    expect(r.status).toBe(200);
    expect(r.body.subject).toMatchObject({ id: aluno.id, name: 'Sofia Teste' });
    expect(r.body.evidence).toHaveLength(1);
    expect(r.body.feedback[0].content).toContain('CO2');
    expect((await t.http().get(`${API}/users/${aluno.id}/data-export`).set(...bearer(prof))).status).toBe(403);
    const pedido = await t.ds.query(`SELECT kind FROM platform.data_subject_request WHERE subject_user_id = $1`, [aluno.id]);
    expect(pedido.map((x: { kind: string }) => x.kind)).toContain('access');
  });

  it('retenção após revogação: dados projetados são apagados pela política; operador ajusta prazo sem deploy', async () => {
    const outro = await criarUsuario(t, 'student', escola);
    await t.http().post(`${API}/users/${outro.id}/guardians`).set(...bearer(admin)).send({ guardianUserId: resp.id });
    await t.http().post(`${API}/users/${outro.id}/consent`).set(...bearer(resp)).send({ purposes: ['learning_assessment'], textVersion: '0.1-placeholder', accepted: true });
    await t.app.get(ProjecaoDeAvaliacao).tratar({ eventId: `ev-r-${outro.id}`, type: 'EvidenciaGerada', version: 1, occurredAt: new Date().toISOString(), data: { studentId: outro.id, competencyCode: 'CAUSE_EFFECT', type: 'x', payload: {} } });
    await t.http().post(`${API}/users/${outro.id}/consent/revoke`).set(...bearer(resp)).send({ purposes: ['learning_assessment'] });
    // Simula a passagem do prazo: revogação "antiga".
    await t.ds.query(`UPDATE platform.consent SET revoked_at = now() - interval '40 days' WHERE student_user_id = $1`, [outro.id]);
    expect((await t.http().put(`${API}/admin/retention/policies/assessment_after_consent_revocation`).set(...bearer(admin)).send({ retentionDays: 30 })).status).toBe(403);
    expect((await t.http().put(`${API}/admin/retention/policies/assessment_after_consent_revocation`).set(...bearer(operador)).send({ retentionDays: 30 })).status).toBe(200);
    const r = await t.http().post(`${API}/admin/retention/run`).set(...bearer(operador));
    expect(r.status).toBe(200);
    expect(r.body.assessment_after_consent_revocation).toBeGreaterThanOrEqual(1);
    const n = await t.ds.query(`SELECT count(*)::int AS n FROM platform.evidence WHERE student_user_id = $1`, [outro.id]);
    expect(n[0].n).toBe(0);
  });

  it('direito de exclusão: apaga dados pedagógicos, pseudonimiza a conta, encerra sessões e avisa o ai-sim-service', async () => {
    const r = await t.http().post(`${API}/users/${aluno.id}/deletion`).set(...bearer(resp));
    expect(r.status).toBe(200);
    expect(r.body.removed.evidence).toBe(1);
    const u = await t.ds.query(`SELECT name, email, status, password_hash FROM platform.app_user WHERE id = $1`, [aluno.id]);
    expect(u[0]).toMatchObject({ name: '[removido]', status: 'pseudonymized', password_hash: '!' });
    expect(u[0].email).not.toContain('student.');
    expect((await t.http().get(`${API}/auth/me`).set(...bearer(aluno))).status).toBe(401);
    await expect(login(t, aluno.email, SENHA_PADRAO)).rejects.toThrow(/401/);
    const ev = await t.ds.query(`SELECT 1 FROM platform.outbox_event WHERE event_type = 'TitularExcluido' AND aggregate_id = $1`, [aluno.id]);
    expect(ev).toHaveLength(1);
    // O audit_log continua íntegro e referencia o id (sem PII).
    const aud = await t.ds.query(`SELECT count(*)::int AS n FROM platform.audit_log WHERE entity_id = $1`, [aluno.id]);
    expect(aud[0].n).toBeGreaterThan(0);
  });
});
