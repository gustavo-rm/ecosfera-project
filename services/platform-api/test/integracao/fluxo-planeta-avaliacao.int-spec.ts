import http from 'node:http';
import type { AddressInfo } from 'node:net';

import WebSocket from 'ws';

import { ProjecaoDeAvaliacao } from '../../src/modules/assessment/application/projecao.service';

import {
  API,
  type AppDeTeste,
  bearer,
  criarApp,
  criarEscola,
  criarUsuario,
  type UsuarioDeTeste,
} from '../support/app';

const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function ate<T>(
  fn: () => T | undefined | Promise<T | undefined>,
  ms = 8000,
): Promise<T> {
  const fim = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v !== undefined) return v;
    if (Date.now() > fim) throw new Error('tempo esgotado esperando condição');
    await espera(100);
  }
}

describe('Fluxo: consentimento → planeta → tempo real → avaliação → painel → exportação', () => {
  let t: AppDeTeste;
  let porta: number;
  let escola: string;
  let admin: UsuarioDeTeste;
  let prof: UsuarioDeTeste;
  let aluno: UsuarioDeTeste;
  let outroAluno: UsuarioDeTeste;
  let resp: UsuarioDeTeste;
  let pesquisador: UsuarioDeTeste;
  let turma: string;
  let planeta: string;

  beforeAll(async () => {
    t = await criarApp({ SIGNED_URL_TTL_SECONDS: '2' });
    await t.app.listen(0);
    porta = (t.app.getHttpServer().address() as AddressInfo).port;
    escola = await criarEscola(t);
    admin = await criarUsuario(t, 'admin', escola);
    prof = await criarUsuario(t, 'teacher', escola);
    aluno = await criarUsuario(t, 'student', escola, { nome: 'Lucas Teste' });
    outroAluno = await criarUsuario(t, 'student', escola);
    resp = await criarUsuario(t, 'guardian', null);
    pesquisador = await criarUsuario(t, 'researcher', null);
    const r = await t
      .http()
      .post(`${API}/users/${aluno.id}/guardians`)
      .set(...bearer(admin))
      .send({ guardianUserId: resp.id });
    expect(r.status).toBe(201);
    turma = (
      await t
        .http()
        .post(`${API}/classes`)
        .set(...bearer(prof))
        .send({ name: '7B', trackLevel: 'fundamental_ii' })
    ).body.id;
    await t
      .http()
      .post(`${API}/classes/${turma}/students`)
      .set(...bearer(prof))
      .send({ studentIds: [aluno.id, outroAluno.id] });
  });
  afterAll(() => t.fechar());

  const consentir = (purposes: string[]) =>
    t
      .http()
      .post(`${API}/users/${aluno.id}/consent`)
      .set(...bearer(resp))
      .send({ purposes, textVersion: '0.1-placeholder', accepted: true });

  it('menor SEM consentimento não cria planeta (403 consent-required) e o painel mostra pendência', async () => {
    const r = await t
      .http()
      .post(`${API}/planets`)
      .set(...bearer(aluno))
      .send({ params: { mass: 1 } });
    expect(r.status).toBe(403);
    expect(r.body.type).toBe('/errors/consent-required');
    expect(r.body.finalidade).toBe('platform_use');
    const visao = await t
      .http()
      .get(`${API}/dashboard/classes/${turma}/overview`)
      .set(...bearer(prof));
    expect(visao.status).toBe(200);
    expect(
      visao.body.students.find((s: { id: string }) => s.id === aluno.id)
        .consentPending,
    ).toContain('platform_use');
  });

  it('só o responsável vinculado consente; versão de texto inexistente → 422', async () => {
    expect(
      (
        await t
          .http()
          .post(`${API}/users/${aluno.id}/consent`)
          .set(...bearer(prof))
          .send({
            purposes: ['platform_use'],
            textVersion: '0.1-placeholder',
            accepted: true,
          })
      ).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .post(`${API}/users/${aluno.id}/consent`)
          .set(...bearer(resp))
          .send({
            purposes: ['platform_use'],
            textVersion: '9.9',
            accepted: true,
          })
      ).status,
    ).toBe(422);
    const r = await consentir([
      'platform_use',
      'learning_assessment',
      'research',
    ]);
    expect(r.status).toBe(201);
    expect(
      r.body.purposes.every((p: { status: string }) => p.status === 'granted'),
    ).toBe(true);
    const aud = await t.ds.query(
      `SELECT data FROM platform.audit_log WHERE action = 'consent.granted' AND entity_id = $1`,
      [aluno.id],
    );
    expect(aud).toHaveLength(3);
  });

  it('com consentimento, o aluno cria planeta e aplica intervenção; o WebSocket entrega o delta', async () => {
    const c = await t
      .http()
      .post(`${API}/planets`)
      .set(...bearer(aluno))
      .send({ params: { mass: 1 }, seed: 'seed-fixo' });
    expect(c.status).toBe(201);
    planeta = c.body.planetId;
    expect(c.body.state.state.source).toBe('FAKE');

    const ws = new WebSocket(
      `ws://127.0.0.1:${porta}${API}/planets/${planeta}/stream`,
      ['ecosfera.v1', `bearer.${aluno.token}`],
    );
    const mensagens: {
      type: string;
      payload: Record<string, unknown>;
      tickId: number;
    }[] = [];
    ws.on('message', (d) =>
      mensagens.push(JSON.parse((d as Buffer).toString('utf8'))),
    );
    await new Promise((ok, erro) => {
      ws.once('open', ok);
      ws.once('error', erro);
    });
    await ate(() =>
      mensagens.some((m) => m.payload.kind === 'connected') ? true : undefined,
    );

    const i = await t
      .http()
      .post(`${API}/planets/${planeta}/interventions`)
      .set(...bearer(aluno))
      .set('Idempotency-Key', 'intv-0001')
      .send({
        action: 'INDUSTRIALIZE',
        target: 'region-7',
        cost: { actionPoints: 2, energy: 10 },
      });
    expect(i.status).toBe(200);
    expect(i.body.tradeoffs[0]).toEqual({
      gain: 'prosperity+',
      cost: 'co2+, temp+',
    });
    expect(i.body.actionPoints.remaining).toBe(3);
    const delta = await ate(() => mensagens.find((m) => m.type === 'delta'));
    expect(delta.payload.action).toBe('INDUSTRIALIZE');
    // Reenvio com a mesma chave não gasta pontos de novo.
    const repetida = await t
      .http()
      .post(`${API}/planets/${planeta}/interventions`)
      .set(...bearer(aluno))
      .set('Idempotency-Key', 'intv-0001')
      .send({
        action: 'INDUSTRIALIZE',
        target: 'region-7',
        cost: { actionPoints: 2, energy: 10 },
      });
    expect(repetida.body.actionPoints.remaining).toBe(3);
    // Pontos insuficientes → 409.
    const cara = await t
      .http()
      .post(`${API}/planets/${planeta}/interventions`)
      .set(...bearer(aluno))
      .send({ action: 'REFOREST', target: 'r', cost: { actionPoints: 9 } });
    expect(cara.status).toBe(409);
    expect(cara.body.type).toBe('/errors/insufficient-action-points');
    ws.close();
  });

  it('tick grande vira 202 com jobId; o resultado chega pelo WebSocket, com replay na reconexão', async () => {
    const r = await t
      .http()
      .post(`${API}/planets/${planeta}/tick`)
      .set(...bearer(aluno))
      .send({ steps: 30, speed: 1 });
    expect(r.status).toBe(202);
    await espera(400);
    const ws = new WebSocket(
      `ws://127.0.0.1:${porta}${API}/planets/${planeta}/stream?lastTickId=0`,
      ['ecosfera.v1', `bearer.${aluno.token}`],
    );
    const msgs: { payload: Record<string, unknown> }[] = [];
    ws.on('message', (d) =>
      msgs.push(JSON.parse((d as Buffer).toString('utf8'))),
    );
    const job = await ate(() =>
      msgs.find((m) => m.payload.jobId === r.body.jobId),
    );
    expect(job).toBeDefined();
    ws.close();
    const pequeno = await t
      .http()
      .post(`${API}/planets/${planeta}/tick`)
      .set(...bearer(aluno))
      .send({ steps: 2 });
    expect(pequeno.status).toBe(200);
    expect(pequeno.body.delta).toBeDefined();
  });

  it('posse: outro aluno não vê o planeta (404) nem abre o stream; professor lê, mas não age', async () => {
    expect(
      (
        await t
          .http()
          .get(`${API}/planets/${planeta}`)
          .set(...bearer(outroAluno))
      ).status,
    ).toBe(404);
    expect(
      (
        await t
          .http()
          .get(`${API}/planets/${planeta}`)
          .set(...bearer(prof))
      ).status,
    ).toBe(200);
    expect(
      (
        await t
          .http()
          .post(`${API}/planets/${planeta}/checkpoints`)
          .set(...bearer(prof))
      ).status,
    ).toBe(403);
    const ws = new WebSocket(
      `ws://127.0.0.1:${porta}${API}/planets/${planeta}/stream`,
      ['ecosfera.v1', `bearer.${outroAluno.token}`],
    );
    const status = await new Promise<number>((ok) =>
      ws.on('unexpected-response', (_req, res) => ok(res.statusCode ?? 0)),
    );
    expect(status).toBe(404);
    const semToken = new WebSocket(
      `ws://127.0.0.1:${porta}${API}/planets/${planeta}/stream`,
      ['ecosfera.v1'],
    );
    expect(
      await new Promise<number>((ok) =>
        semToken.on('unexpected-response', (_req, res) =>
          ok(res.statusCode ?? 0),
        ),
      ),
    ).toBe(401);
  });

  it('a projeção consome as evidências sintéticas do stream e o professor vê perfil, evidências, BNCC e alertas', async () => {
    const perfil = await ate(async () => {
      const r = await t
        .http()
        .get(`${API}/assessment/students/${aluno.id}/profile`)
        .set(...bearer(prof));
      return r.status === 200 && r.body.competencies.length > 0
        ? r.body
        : undefined;
    });
    expect(perfil.competencies[0].synthetic).toBe(true);
    const ev = await t
      .http()
      .get(`${API}/assessment/students/${aluno.id}/evidence`)
      .set(...bearer(prof));
    expect(ev.body.total).toBeGreaterThan(0);
    expect(ev.body.items[0].planetId).toBe(planeta);
    const bncc = await t
      .http()
      .get(`${API}/assessment/students/${aluno.id}/bncc`)
      .set(...bearer(prof));
    expect(
      bncc.body.skills.some(
        (s: { mastery: number | null }) => s.mastery !== null,
      ),
    ).toBe(true);
    const alertas = await t
      .http()
      .get(`${API}/dashboard/classes/${turma}/alerts`)
      .set(...bearer(prof));
    expect(alertas.status).toBe(200);
    expect(alertas.body.thresholds.reviewStatus).toBe(
      'pending_pedagogical_review',
    );
    // RP-004: o aluno não vê a própria pontuação.
    expect(
      (
        await t
          .http()
          .get(`${API}/assessment/students/${aluno.id}/profile`)
          .set(...bearer(aluno))
      ).status,
    ).toBe(403);
  });

  it('SSE do tutor chega em fluxo (primeiro trecho antes do fim) e a pergunta vai sem PII', async () => {
    const inicio = Date.now();
    const tempos: number[] = [];
    let texto = '';
    const tipo = await new Promise<string>((ok, erro) => {
      const corpo = JSON.stringify({
        planetId: planeta,
        contextRef: 'co2',
        question: 'Meu email é lucas@x.com, por que esquenta?',
      });
      const req = http.request(
        {
          host: '127.0.0.1',
          port: porta,
          path: `${API}/ai/explain`,
          method: 'POST',
          headers: {
            'content-type': 'application/json',
            authorization: `Bearer ${aluno.token}`,
          },
        },
        (res) => {
          res.on('data', (c: Buffer) => {
            tempos.push(Date.now() - inicio);
            texto += c.toString();
          });
          res.on('end', () => ok(String(res.headers['content-type'])));
        },
      );
      req.on('error', erro);
      req.end(corpo);
    });
    expect(tipo).toContain('text/event-stream');
    expect(tempos.length).toBeGreaterThan(2);
    expect(tempos[0]).toBeLessThan(tempos[tempos.length - 1] - 50);
    expect(texto).toContain('[SIMULADO]');
    expect(texto).toContain('event: end');
  });

  it('sincronização offline é idempotente por ação', async () => {
    const corpo = {
      actions: [
        {
          idempotencyKey: 'offline-0001',
          type: 'checkpoint',
          payload: {},
          clientTimestamp: '2026-11-16T10:00:00Z',
        },
      ],
    };
    const a = await t
      .http()
      .post(`${API}/planets/${planeta}/sync`)
      .set(...bearer(aluno))
      .send(corpo);
    const b = await t
      .http()
      .post(`${API}/planets/${planeta}/sync`)
      .set(...bearer(aluno))
      .send(corpo);
    expect(a.body.results[0].status).toBe('applied');
    expect(b.body.results[0].status).toBe('duplicate');
    expect(b.body.results[0].result).toEqual(a.body.results[0].result);
  });

  it('exportação devolve URL assinada que funciona e depois expira', async () => {
    const r = await t
      .http()
      .get(`${API}/dashboard/reports/export?format=csv&classId=${turma}`)
      .set(...bearer(prof));
    expect(r.status).toBe(200);
    const caminho = new URL(r.body.url as string);
    const ok = await t.http().get(`${caminho.pathname}${caminho.search}`);
    expect(ok.status).toBe(200);
    expect(ok.text).toContain('aluno,competencia');
    await espera(3100);
    expect(
      (await t.http().get(`${caminho.pathname}${caminho.search}`)).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .get(`${API}/dashboard/reports/export?format=csv&classId=${turma}`)
          .set(...bearer(aluno))
      ).status,
    ).toBe(403);
  });

  it('dataset de pesquisa: só anonimizado, sem PII, e com supressão de grupos pequenos (k=5)', async () => {
    expect(
      (
        await t
          .http()
          .get(`${API}/research/dataset?anonymized=false`)
          .set(...bearer(pesquisador))
      ).status,
    ).toBe(422);
    expect(
      (
        await t
          .http()
          .get(`${API}/research/dataset?anonymized=true`)
          .set(...bearer(prof))
      ).status,
    ).toBe(403);
    const r = await t
      .http()
      .get(`${API}/research/dataset?anonymized=true&format=json`)
      .set(...bearer(pesquisador));
    expect(r.status).toBe(200);
    // Um único aluno consentiu: o grupo dele tem < 5 alunos e é suprimido.
    expect(r.body.anonymization.suppressedGroups).toBeGreaterThanOrEqual(1);
    const u = new URL(r.body.url as string);
    const arquivo = await t.http().get(`${u.pathname}${u.search}`);
    expect(arquivo.text).not.toContain(aluno.id);
    expect(arquivo.text).not.toContain(aluno.email);
    expect(arquivo.text).not.toMatch(/Lucas/);
  });

  it('revogação: efeito imediato — aluno bloqueado, WebSocket fechado, nada novo projetado', async () => {
    const ws = new WebSocket(
      `ws://127.0.0.1:${porta}${API}/planets/${planeta}/stream`,
      ['ecosfera.v1', `bearer.${aluno.token}`],
    );
    await new Promise((ok) => ws.once('open', ok));
    const fechou = new Promise<number>((ok) =>
      ws.on('close', (codigo) => ok(codigo)),
    );
    const r = await t
      .http()
      .post(`${API}/users/${aluno.id}/consent/revoke`)
      .set(...bearer(resp))
      .send({ purposes: ['platform_use', 'learning_assessment'] });
    expect(r.status).toBe(200);
    expect(await fechou).toBe(4403);
    const bloqueado = await t
      .http()
      .post(`${API}/planets/${planeta}/interventions`)
      .set(...bearer(aluno))
      .send({ action: 'REFOREST', target: 'r', cost: { actionPoints: 1 } });
    expect(bloqueado.status).toBe(403);
    expect(bloqueado.body.type).toBe('/errors/consent-required');
    const antes: { n: number }[] = await t.ds.query(
      `SELECT count(*)::int AS n FROM platform.evidence WHERE student_user_id = $1`,
      [aluno.id],
    );
    const resultado = await t.app.get(ProjecaoDeAvaliacao).tratar({
      eventId: `evt-${Date.now()}`,
      type: 'EvidenciaGerada',
      version: 1,
      occurredAt: new Date().toISOString(),
      data: {
        studentId: aluno.id,
        competencyCode: 'CAUSE_EFFECT',
        type: 'intervention',
        payload: {},
      },
    });
    expect(resultado).toBe('skipped_no_consent');
    const depois: { n: number }[] = await t.ds.query(
      `SELECT count(*)::int AS n FROM platform.evidence WHERE student_user_id = $1`,
      [aluno.id],
    );
    expect(depois[0].n).toBe(antes[0].n);
    const outbox = await t.ds.query(
      `SELECT 1 FROM platform.outbox_event WHERE event_type = 'ConsentimentoRevogado' AND aggregate_id = $1`,
      [aluno.id],
    );
    expect(outbox.length).toBe(1);
  });
});
