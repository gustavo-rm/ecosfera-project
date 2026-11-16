/**
 * Smoke de ponta a ponta (Anexo B) contra um backend EM EXECUÇÃO. Imprime, passo a passo,
 * a requisição resumida, o status e o esperado × obtido. Sai com código 1 se algo falhar.
 *
 * Uso: SMOKE_BASE_URL=http://localhost:3000 pnpm smoke | tee ../../docs/backend/relatorios/SMOKE.txt
 * Requer: seed de dev aplicado (.credenciais-dev.json com o operador), servidor com SIGNED_URL_TTL_SECONDS curto
 * (ex.: 3), DATABASE_URL do papel da aplicação (para provar que ele não altera o audit_log) e os segredos do .env.
 */
import 'dotenv/config';

import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { jwtVerify, SignJWT } from 'jose';
import { Client } from 'pg';
import WebSocket from 'ws';

import { ServicoDeTokens } from '../src/modules/identity/infrastructure/tokens';

const BASE = (process.env.SMOKE_BASE_URL ?? 'http://localhost:3000').replace(/\/$/, '');
const API = `${BASE}/platform/api/v1`;
const cred = JSON.parse(readFileSync(join(__dirname, '..', '.credenciais-dev.json'), 'utf8')) as { usuarios: Record<string, { email: string; senha: string }> };
const sfx = randomBytes(3).toString('hex');
let falhas = 0;
let passo = '';
const pii: string[] = [];

function titulo(t: string) {
  passo = t;
  console.log(`\n━━ ${t}`);
}
function conferir(descricao: string, esperado: unknown, obtido: unknown, extra = '') {
  const ok = JSON.stringify(esperado) === JSON.stringify(obtido);
  if (!ok) falhas++;
  console.log(`  ${ok ? '✔' : '✘'} ${descricao} — esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}${extra ? ` ${extra}` : ''}`);
  return ok;
}

interface Resp {
  status: number;
  corpo: any;
  cabecalhos: Headers;
}
async function req(metodo: string, caminho: string, token?: string, corpo?: unknown, extra: Record<string, string> = {}): Promise<Resp> {
  const r = await fetch(`${API}${caminho}`, {
    method: metodo,
    headers: { ...(corpo !== undefined ? { 'content-type': 'application/json' } : {}), ...(token ? { authorization: `Bearer ${token}` } : {}), ...extra },
    body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    redirect: 'manual',
  });
  const texto = await r.text();
  let c: any = texto;
  try {
    c = texto ? JSON.parse(texto) : {};
  } catch {
    /* texto */
  }
  console.log(`    ${metodo.padEnd(5)} ${caminho.replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, '{id}')} → ${r.status}${c?.type ? ` ${c.type}` : ''}`);
  return { status: r.status, corpo: c, cabecalhos: r.headers };
}
async function login(email: string, senha: string): Promise<{ token: string; refresh: string }> {
  const r = await req('POST', '/auth/login', undefined, { email, senha }, { 'X-Refresh-Transport': 'body' });
  if (r.status !== 200) throw new Error(`login falhou para ${email}: ${r.status}`);
  return { token: r.corpo.accessToken, refresh: r.corpo.refreshToken };
}
const senha = () => `Smoke-${randomBytes(6).toString('hex')}-9`;

async function criarUsuario(token: string, papel: string, nome: string, extra: Record<string, unknown> = {}) {
  const email = `${papel}.${sfx}.${randomBytes(2).toString('hex')}@smoke.local`;
  const s = senha();
  const r = await req('POST', '/users', token, { name: nome, email, role: papel, password: s, ...extra });
  conferir(`cria ${papel} (${nome})`, 201, r.status);
  pii.push(email, nome, r.corpo.id);
  return { id: r.corpo.id as string, email, senha: s, ...(await login(email, s)) };
}

function abrirStream(planeta: string, token: string): Promise<{ ws: WebSocket; mensagens: any[]; status?: number }> {
  return new Promise((ok) => {
    const ws = new WebSocket(`${API.replace(/^http/, 'ws')}/planets/${planeta}/stream`, ['ecosfera.v1', `bearer.${token}`]);
    const mensagens: any[] = [];
    ws.on('message', (d) => mensagens.push(JSON.parse((d as Buffer).toString('utf8'))));
    ws.on('open', () => ok({ ws, mensagens }));
    ws.on('unexpected-response', (_q, res) => ok({ ws, mensagens, status: res.statusCode }));
  });
}
async function esperar<T>(fn: () => Promise<T | undefined> | T | undefined, ms = 10000): Promise<T | undefined> {
  const fim = Date.now() + ms;
  while (Date.now() < fim) {
    const v = await fn();
    if (v !== undefined) return v;
    await new Promise((r) => setTimeout(r, 200));
  }
  return undefined;
}

async function principal(): Promise<void> {
  console.log(`Smoke ECOSFERA platform-api — ${new Date().toISOString()} — alvo ${BASE}`);
  const ready = await req('GET', '/ready');
  console.log(`  adaptadores falsos ativos: ${JSON.stringify(ready.corpo.fakeAdapters)}`);

  titulo('1. Escola, admin e usuários; responsável vinculado ao aluno menor');
  const op = await login(cred.usuarios.operador!.email, cred.usuarios.operador!.senha);
  const senhaAdmin = senha();
  const emailAdmin = `admin.${sfx}@smoke.local`;
  const esc = await req('POST', '/schools', op.token, { name: `Escola Smoke ${sfx}`, admin: { name: 'Admin Smoke', email: emailAdmin, password: senhaAdmin } });
  conferir('operador cria escola com admin inicial', 201, esc.status);
  const escolaA = esc.corpo.school.id as string;
  const admin = await login(emailAdmin, senhaAdmin);
  const prof = await criarUsuario(admin.token, 'teacher', 'Marina Smoke');
  const coord = await criarUsuario(admin.token, 'coordinator', 'Beatriz Smoke');
  const aluno = await criarUsuario(admin.token, 'student', 'Lucas Smoke', { isMinor: true });
  const colega = await criarUsuario(admin.token, 'student', 'Joana Smoke', { isMinor: false });
  const resp = await criarUsuario(admin.token, 'guardian', 'Helena Smoke');
  const pesq = await criarUsuario(op.token, 'researcher', 'Pesquisa Smoke');
  conferir('admin vincula responsável ao aluno', 201, (await req('POST', `/users/${aluno.id}/guardians`, admin.token, { guardianUserId: resp.id })).status);

  titulo('2. Aluno menor SEM consentimento é bloqueado; painel mostra pendência');
  const bloqueado = await req('POST', '/planets', aluno.token, { params: { mass: 1 } });
  conferir('criar planeta sem consentimento', [403, '/errors/consent-required'], [bloqueado.status, bloqueado.corpo.type], `— "${bloqueado.corpo.detail}"`);
  const turma = await req('POST', '/classes', prof.token, { name: `7º A ${sfx}`, year: 7 });
  conferir('professor cria turma', 201, turma.status);
  const turmaId = turma.corpo.id as string;
  conferir('professor vincula alunos', 200, (await req('POST', `/classes/${turmaId}/students`, prof.token, { studentIds: [aluno.id, colega.id] })).status);
  const visao = await req('GET', `/dashboard/classes/${turmaId}/consents`, prof.token);
  const st = visao.corpo.students.find((s: any) => s.id === aluno.id).purposes.find((p: any) => p.purpose === 'platform_use').status;
  conferir('painel do professor: consentimento do aluno', 'pending', st);

  titulo('3. Responsável consente; aluno cria planeta, intervém e o WebSocket entrega o delta');
  const textos = await req('GET', '/consent-texts', resp.token);
  console.log(`    texto vigente: versão ${textos.corpo.items[0].version} (${textos.corpo.items[0].reviewStatus})`);
  conferir('responsável registra consentimento (3 finalidades)', 201, (await req('POST', `/users/${aluno.id}/consent`, resp.token, { purposes: ['platform_use', 'learning_assessment', 'research'], textVersion: textos.corpo.items[0].version, accepted: true })).status);
  const planeta = await req('POST', '/planets', aluno.token, { params: { mass: 1, orbitAu: 1 }, seed: `smoke-${sfx}` });
  conferir('aluno cria planeta (adaptador falso)', 201, planeta.status);
  const planetaId = planeta.corpo.planetId as string;
  const s = await abrirStream(planetaId, aluno.token);
  conferir('WebSocket autenticado abre', undefined, s.status);
  const intv = await req('POST', `/planets/${planetaId}/interventions`, aluno.token, { action: 'INDUSTRIALIZE', target: 'region-7', cost: { actionPoints: 2, energy: 10 } });
  conferir('intervenção com trade-off', [200, 'prosperity+'], [intv.status, intv.corpo.tradeoffs?.[0]?.gain]);
  const delta = await esperar(() => s.mensagens.find((m) => m.type === 'delta'));
  conferir('WebSocket recebeu delta', 'delta', delta?.type, `tickId=${delta?.tickId}`);
  s.ws.close();

  titulo('5. Trilha e missão ancorada à BNCC');
  conferir('define trilha Fundamental II', 200, (await req('PATCH', `/classes/${turmaId}/track`, prof.token, { level: 'fundamental_ii' })).status);
  const ruim = await req('POST', '/missions', prof.token, { title: 'Estufa', objective: 'CO2 e temperatura', trackLevel: 'fundamental_ii', bnccCodes: ['EF99XX99'] });
  conferir('código BNCC inexistente', 422, ruim.status, `— ${ruim.corpo.errors?.[0]?.message}`);
  const missao = await req('POST', '/missions', prof.token, { title: 'Estufa', objective: 'CO2 e temperatura', trackLevel: 'fundamental_ii', bnccCodes: ['EF07CI13'], classIds: [turmaId] });
  conferir('missão criada e publicada para a turma', [201, 'published'], [missao.status, missao.corpo.status]);
  const vistas = await req('GET', `/missions?classId=${turmaId}`, aluno.token);
  conferir('aluno vê a missão publicada', 1, vistas.corpo.items?.length);

  titulo('6. Evidências sintéticas projetadas; professor vê perfil, evidências, alertas e mapa BNCC');
  const perfil = await esperar(async () => {
    const r = await fetch(`${API}/assessment/students/${aluno.id}/profile`, { headers: { authorization: `Bearer ${prof.token}` } });
    const j = (await r.json()) as any;
    return r.status === 200 && j.competencies.length > 0 ? j : undefined;
  });
  conferir('perfil por competência projetado (sintético)', true, perfil?.competencies?.[0]?.synthetic);
  const ev = await req('GET', `/assessment/students/${aluno.id}/evidence`, prof.token);
  conferir('evidências rastreáveis ligadas ao planeta', planetaId, ev.corpo.items?.[0]?.planetId);
  const alertas = await req('GET', `/dashboard/classes/${turmaId}/alerts`, prof.token);
  conferir('alertas (limiares placeholder pedagógico)', [200, 'pending_pedagogical_review'], [alertas.status, alertas.corpo.thresholds?.reviewStatus]);
  const bncc = await req('GET', `/assessment/students/${aluno.id}/bncc`, prof.token);
  conferir('mapa BNCC com domínio estimado', true, bncc.corpo.skills?.some((x: any) => x.mastery !== null));
  conferir('aluno NÃO vê a própria pontuação (RP-004)', 403, (await req('GET', `/assessment/students/${aluno.id}/profile`, aluno.token)).status);
  conferir('coordenação vê agregado da escola', 200, (await req('GET', `/dashboard/schools/${escolaA}/competencies`, coord.token)).status);

  titulo('7. Exportação: URL assinada de curta duração que expira');
  const exp = await req('GET', `/dashboard/reports/export?format=csv&classId=${turmaId}`, prof.token);
  conferir('relatório CSV gerado', 200, exp.status, `— expira em ${exp.corpo.expiresAt}`);
  const baixa = await fetch(exp.corpo.url as string);
  conferir('download pela URL assinada', 200, baixa.status);
  const espera = new Date(exp.corpo.expiresAt as string).getTime() - Date.now() + 1500;
  console.log(`    aguardando ${Math.round(espera / 1000)} s para a URL expirar…`);
  await new Promise((r) => setTimeout(r, Math.max(espera, 0)));
  const expirada = await fetch(exp.corpo.url as string);
  conferir('URL expirada é recusada', true, expirada.status === 403 || expirada.status === 400, `(status ${expirada.status})`);

  titulo('8. Dataset anonimizado para pesquisa, com varredura de PII');
  console.log('    preparando: mais 5 alunos consentidos na mesma turma (para o grupo passar de k=5)');
  for (let i = 0; i < 5; i++) {
    const extra = await criarUsuario(admin.token, 'student', `Aluno Extra ${i} Smoke`, { isMinor: true });
    await req('POST', `/users/${extra.id}/guardians`, admin.token, { guardianUserId: resp.id });
    await req('POST', `/classes/${turmaId}/students`, prof.token, { studentIds: [extra.id] });
    await req('POST', `/users/${extra.id}/consent`, resp.token, { purposes: ['platform_use', 'learning_assessment', 'research'], textVersion: textos.corpo.items[0].version, accepted: true });
    const pl = await req('POST', '/planets', extra.token, { params: { mass: 1 } });
    await req('POST', `/planets/${pl.corpo.planetId as string}/interventions`, extra.token, { action: 'REFOREST', target: 'r1', cost: { actionPoints: 1 } });
  }
  await new Promise((r) => setTimeout(r, 2500));
  conferir('anonymized=false recusado', 422, (await req('GET', '/research/dataset?anonymized=false', pesq.token)).status);
  const ds = await req('GET', '/research/dataset?anonymized=true&format=csv', pesq.token);
  conferir('dataset gerado e NÃO vazio', [200, true], [ds.status, (ds.corpo.anonymization?.rows ?? 0) > 0], `— k=${ds.corpo.anonymization?.k}, linhas=${ds.corpo.anonymization?.rows}, grupos suprimidos=${ds.corpo.anonymization?.suppressedGroups}`);
  const conteudo = await (await fetch(ds.corpo.url as string)).text();
  const achados = pii.filter((v) => v && conteudo.includes(v));
  const uuids = conteudo.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi) ?? [];
  const emails = conteudo.match(/[\w.+-]+@[\w-]+\.[\w.]+/g) ?? [];
  console.log(`    varredura de PII: ${pii.length} valores conhecidos (nomes, e-mails, ids) procurados; ${achados.length} achados; UUIDs: ${uuids.length}; e-mails: ${emails.length}`);
  conferir('nenhuma PII no dataset', [0, 0, 0], [achados.length, uuids.length, emails.length]);

  titulo('9. Casos negativos');
  conferir('aluno lê planeta de outro aluno', 404, (await req('GET', `/planets/${planetaId}`, colega.token)).status);
  const senhaB = senha();
  const emailB = `adminb.${sfx}@smoke.local`;
  const escB = await req('POST', '/schools', op.token, { name: `Escola B ${sfx}`, admin: { name: 'Admin B', email: emailB, password: senhaB } });
  const adminB = await login(emailB, senhaB);
  const profB = await criarUsuario(adminB.token, 'teacher', 'Prof B');
  const turmaB = await req('POST', '/classes', profB.token, { name: 'B1' });
  conferir('professor da escola A lê turma da escola B', 404, (await req('GET', `/classes/${turmaB.corpo.id as string}`, prof.token)).status);
  conferir('professor da escola A lê dashboard da escola B', 404, (await req('GET', `/dashboard/classes/${turmaB.corpo.id as string}/overview`, prof.token)).status);
  void escB;
  conferir('aluno chama endpoint de professor', 403, (await req('POST', '/missions', aluno.token, { title: 'x', objective: 'y', trackLevel: 'medio', bnccCodes: ['EF07CI13'] })).status);
  const segredo = process.env.JWT_ACCESS_SECRET;
  if (segredo) {
    const chave = new TextEncoder().encode(segredo);
    const { payload } = await jwtVerify(prof.token, chave);
    const velho = await new SignJWT({ ...payload }).setProtectedHeader({ alg: 'HS256' }).setExpirationTime(Math.floor(Date.now() / 1000) - 60).sign(chave);
    const r = await req('GET', '/auth/me', velho);
    conferir('token expirado', [401, 'Token expirado'], [r.status, r.corpo.detail]);
  } else console.log('  · token expirado: pulado (JWT_ACCESS_SECRET ausente no ambiente do smoke)');
  const sessao = await login(coord.email, coord.senha);
  const r1 = await req('POST', '/auth/refresh', undefined, { refreshToken: sessao.refresh }, { 'X-Refresh-Transport': 'body' });
  const reuso = await req('POST', '/auth/refresh', undefined, { refreshToken: sessao.refresh }, { 'X-Refresh-Transport': 'body' });
  conferir('refresh reutilizado é recusado', 401, reuso.status, `— "${reuso.corpo.detail}"`);
  conferir('família revogada: o refresh novo também morre', 401, (await req('POST', '/auth/refresh', undefined, { refreshToken: r1.corpo.refreshToken }, { 'X-Refresh-Transport': 'body' })).status);
  const tentativas: number[] = [];
  for (let i = 0; i < 7; i++) tentativas.push((await req('POST', '/auth/login', undefined, { email: colega.email, senha: 'errada-0000x' })).status);
  conferir('excesso de tentativas de login vira 429', true, tentativas.includes(429), `(sequência ${tentativas.join(',')})`);

  titulo('4. Revogação: aluno volta a ser bloqueado; nada novo é projetado');
  const antes = (await req('GET', `/assessment/students/${aluno.id}/evidence`, prof.token)).corpo.total as number;
  conferir('responsável revoga uso e avaliação', 200, (await req('POST', `/users/${aluno.id}/consent/revoke`, resp.token, { purposes: ['platform_use', 'learning_assessment'] })).status);
  const depois = await req('POST', `/planets/${planetaId}/interventions`, aluno.token, { action: 'REFOREST', target: 'r', cost: { actionPoints: 1 } });
  conferir('aluno bloqueado após revogação', [403, '/errors/consent-required'], [depois.status, depois.corpo.type]);
  const servico = process.env.SERVICE_TOKEN_SECRET ? await ServicoDeTokens.emitirTokenDeServico(process.env.SERVICE_TOKEN_SECRET, 'ai-sim-service') : undefined;
  if (servico) {
    const ingest = await req('POST', '/assessment/events', servico, { eventId: `smoke-${sfx}-1`, type: 'EvidenciaGerada', version: 1, occurredAt: new Date().toISOString(), data: { studentId: aluno.id, competencyCode: 'CAUSE_EFFECT', type: 'intervention', payload: {} } });
    conferir('evento de avaliação após revogação é descartado', 'skipped_no_consent', ingest.corpo.outcome);
  }
  const painel = await req('GET', `/assessment/students/${aluno.id}/evidence`, prof.token);
  conferir('professor não lê mais dados pedagógicos do aluno', 403, painel.status, `(antes: ${antes} evidências)`);

  titulo('10. Auditoria imutável');
  const db = new Client({ connectionString: process.env.DATABASE_URL });
  await db.connect();
  const acoes = await db.query(
    `SELECT action, outcome, count(*)::int AS n FROM platform.audit_log WHERE created_at > now() - interval '1 hour'
     AND action IN ('consent.granted','consent.revoked','export.created','research.dataset_exported','auth.login_failed','auth.refresh_reuse_detected','minor_data.accessed')
     GROUP BY action, outcome ORDER BY action`,
  );
  for (const l of acoes.rows) console.log(`    audit_log: ${l.action} (${l.outcome}) × ${l.n}`);
  for (const a of ['consent.granted', 'consent.revoked', 'export.created', 'research.dataset_exported', 'auth.login_failed', 'auth.refresh_reuse_detected']) {
    conferir(`registrado: ${a}`, true, acoes.rows.some((l) => l.action === a));
  }
  const papel = (await db.query('SELECT current_user')).rows[0].current_user as string;
  for (const sql of ['UPDATE platform.audit_log SET action = action', 'DELETE FROM platform.audit_log', 'TRUNCATE platform.audit_log']) {
    let erro = '';
    try {
      await db.query(sql);
    } catch (e) {
      erro = (e as Error).message;
    }
    conferir(`papel "${papel}" não consegue: ${sql.split(' ')[0]}`, true, erro.length > 0, `— ${erro}`);
  }
  await db.end();

  console.log(`\nResultado: ${falhas === 0 ? 'TUDO OK' : `${falhas} FALHA(S)`} (último passo: ${passo})`);
  process.exit(falhas === 0 ? 0 : 1);
}

principal().catch((e: unknown) => {
  console.error(`\nFALHA INESPERADA no passo "${passo}":`, e);
  process.exit(1);
});
