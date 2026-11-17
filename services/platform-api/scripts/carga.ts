/**
 * Teste de carga básico (RNF-005: ≥ 40 alunos simultâneos por instância escolar; RNF-002: ação→feedback ≤ 1 s p95).
 * Roda contra um backend em execução (uma instância). Uso: SMOKE_BASE_URL=http://localhost:3000 pnpm carga
 */
import 'dotenv/config';

import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import WebSocket from 'ws';

const BASE = (process.env.SMOKE_BASE_URL ?? 'http://localhost:3000').replace(
  /\/$/,
  '',
);
const API = `${BASE}/platform/api/v1`;
const N = Number(process.env.CARGA_ALUNOS ?? 45);
const cred = JSON.parse(
  readFileSync(join(__dirname, '..', '.credenciais-dev.json'), 'utf8'),
) as { usuarios: Record<string, { email: string; senha: string }> };
const sfx = randomBytes(3).toString('hex');

async function chamar(
  metodo: string,
  caminho: string,
  token?: string,
  corpo?: unknown,
  extra: Record<string, string> = {},
) {
  const r = await fetch(`${API}${caminho}`, {
    method: metodo,
    headers: {
      ...(corpo ? { 'content-type': 'application/json' } : {}),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...extra,
    },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const t = await r.text();
  return { status: r.status, corpo: t ? JSON.parse(t) : {} };
}

function estatistica(nome: string, ms: number[], erros: number) {
  const o = [...ms].sort((a, b) => a - b);
  const p = (q: number) =>
    o[Math.min(o.length - 1, Math.ceil(q * o.length) - 1)] ?? NaN;
  const linha = `| ${nome} | ${o.length} | ${erros} | ${p(0.5).toFixed(0)} | ${p(0.95).toFixed(0)} | ${p(0.99).toFixed(0)} | ${(o[o.length - 1] ?? NaN).toFixed(0)} |`;
  console.log(linha);
  return { p95: p(0.95), linha };
}

async function medir(
  n: number,
  fn: (i: number) => Promise<{ status: number }>,
  esperado = 200,
) {
  const ms: number[] = [];
  let erros = 0;
  await Promise.all(
    Array.from({ length: n }, async (_, i) => {
      const t = performance.now();
      const r = await fn(i);
      ms.push(performance.now() - t);
      if (r.status !== esperado) erros++;
    }),
  );
  return { ms, erros };
}

async function principal() {
  console.log(
    `Carga ECOSFERA platform-api — ${new Date().toISOString()} — ${N} alunos — alvo ${BASE}\n`,
  );
  const login = async (email: string, senha: string) =>
    (
      await chamar(
        'POST',
        '/auth/login',
        undefined,
        { email, senha },
        { 'X-Refresh-Transport': 'body' },
      )
    ).corpo.accessToken as string;
  const op = await login(
    cred.usuarios.operador.email,
    cred.usuarios.operador.senha,
  );
  const senha = `Carga-${sfx}-senha-1`;
  const esc = await chamar('POST', '/schools', op, {
    name: `Escola Carga ${sfx}`,
    admin: {
      name: 'Admin',
      email: `adm.carga.${sfx}@x.local`,
      password: senha,
    },
  });
  const admin = await login(`adm.carga.${sfx}@x.local`, senha);
  const criar = async (papel: string, i: number, menor?: boolean) => {
    const email = `${papel}.${i}.${sfx}@carga.local`;
    const r = await chamar('POST', '/users', admin, {
      name: `${papel} ${i}`,
      email,
      role: papel,
      password: senha,
      isMinor: menor,
    });
    return { id: r.corpo.id as string, email };
  };
  const prof = await criar('teacher', 0);
  const resp = await criar('guardian', 0);
  const alunos: { id: string; email: string }[] = [];
  for (let i = 0; i < N; i++) alunos.push(await criar('student', i, true));
  const tProf = await login(prof.email, senha);
  const tResp = await login(resp.email, senha);
  const turma = (
    await chamar('POST', '/classes', tProf, {
      name: 'Carga',
      trackLevel: 'fundamental_ii',
    })
  ).corpo.id as string;
  await chamar('POST', `/classes/${turma}/students`, tProf, {
    studentIds: alunos.map((a) => a.id),
  });
  for (const a of alunos) {
    await chamar('POST', `/users/${a.id}/guardians`, admin, {
      guardianUserId: resp.id,
    });
    await chamar('POST', `/users/${a.id}/consent`, tResp, {
      purposes: ['platform_use', 'learning_assessment'],
      textVersion: '0.1-placeholder',
      accepted: true,
    });
  }
  void esc;
  console.log('Preparação concluída.\n');
  console.log(
    '| Cenário | Requisições | Erros | p50 (ms) | p95 (ms) | p99 (ms) | máx (ms) |',
  );
  console.log('|---|---|---|---|---|---|---|');

  // 1. Início de aula: todos entram ao mesmo tempo (mesmo IP, como atrás do NAT da escola).
  const tokens: string[] = new Array<string>(N);
  const l = await medir(N, async (i) => {
    const r = await chamar(
      'POST',
      '/auth/login',
      undefined,
      { email: alunos[i].email, senha },
      { 'X-Refresh-Transport': 'body' },
    );
    tokens[i] = r.corpo.accessToken;
    return r;
  });
  const rLogin = estatistica(`Login simultâneo (${N})`, l.ms, l.erros);

  // 2. Cada aluno cria o próprio planeta ao mesmo tempo.
  const planetas: string[] = new Array<string>(N);
  const c = await medir(
    N,
    async (i) => {
      const r = await chamar('POST', '/planets', tokens[i], {
        params: { mass: 1 },
      });
      planetas[i] = r.corpo.planetId;
      return r;
    },
    201,
  );
  estatistica(`Criar planeta simultâneo (${N})`, c.ms, c.erros);

  // 3. N WebSockets abertos; cada aluno intervém; mede ação → delta recebido no WebSocket.
  const sockets = await Promise.all(
    planetas.map(
      (p, i) =>
        new Promise<{ ws: WebSocket; esperando?: (t: number) => void }>(
          (ok, erro) => {
            const ws = new WebSocket(
              `${API.replace(/^http/, 'ws')}/planets/${p}/stream`,
              ['ecosfera.v1', `bearer.${tokens[i]}`],
            );
            const s: { ws: WebSocket; esperando?: (t: number) => void } = {
              ws,
            };
            ws.on('message', (d) => {
              const m = JSON.parse((d as Buffer).toString('utf8')) as {
                type: string;
              };
              if (m.type === 'delta') s.esperando?.(performance.now());
            });
            ws.on('open', () => ok(s));
            ws.on('error', erro);
          },
        ),
    ),
  );
  const ms: number[] = [];
  let errosWs = 0;
  for (let rodada = 0; rodada < 2; rodada++) {
    await Promise.all(
      sockets.map(async (s, i) => {
        const inicio = performance.now();
        const chegou = new Promise<number>((ok) => (s.esperando = ok));
        const r = await chamar(
          'POST',
          `/planets/${planetas[i]}/interventions`,
          tokens[i],
          {
            action: 'REFOREST',
            target: `r${rodada}`,
            cost: { actionPoints: 1 },
          },
        );
        if (r.status !== 200) errosWs++;
        const fim = await Promise.race([
          chegou,
          new Promise<number>((ok) => setTimeout(() => ok(NaN), 5000)),
        ]);
        if (Number.isNaN(fim)) errosWs++;
        else ms.push(fim - inicio);
      }),
    );
  }
  const rWs = estatistica(
    `Ação → delta no WebSocket (${N} conexões abertas)`,
    ms,
    errosWs,
  );

  // 4. Leitura do planeta e painel do professor sob concorrência.
  const g = await medir(N * 5, (i) =>
    chamar('GET', `/planets/${planetas[i % N]}`, tokens[i % N]),
  );
  estatistica(
    `GET planeta (${N * 5} disparadas ao mesmo tempo)`,
    g.ms,
    g.erros,
  );
  const d = await medir(40, (i) =>
    chamar(
      'GET',
      `/dashboard/classes/${turma}/${i % 2 ? 'overview' : 'competencies'}`,
      tProf,
    ),
  );
  const rPainel = estatistica(
    'Painel do professor (40 em paralelo)',
    d.ms,
    d.erros,
  );
  for (const s of sockets) s.ws.close();

  console.log(
    `\nMetas: login e painel sem erro; ação→delta p95 ≤ 1000 ms (RNF-002). Obtido: login p95=${rLogin.p95.toFixed(0)} ms, ação→delta p95=${rWs.p95.toFixed(0)} ms, painel p95=${rPainel.p95.toFixed(0)} ms.`,
  );
  process.exit(rWs.p95 <= 1000 && l.erros === 0 && errosWs === 0 ? 0 : 1);
}

principal().catch((e: unknown) => {
  console.error(e);
  process.exit(1);
});
