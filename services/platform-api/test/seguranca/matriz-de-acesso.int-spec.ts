import { ServicoDeTokens } from '../../src/modules/identity/infrastructure/tokens';
import { rotasDeclaradas } from '../../src/shared/http/catalogo-de-rotas';
import { PAPEIS, type Papel } from '../../src/shared/kernel/papeis';
import { API, type AppDeTeste, bearer, criarApp, criarEscola, criarUsuario, type UsuarioDeTeste } from '../support/app';

/**
 * Matriz de acesso indevido (RNF-006), GERADA a partir das declarações das rotas:
 *  1. toda rota não pública sem token → 401;
 *  2. toda rota com papéis → um papel fora da lista recebe 403;
 *  3. toda rota com posse → ator de OUTRA escola, com papel permitido, recebe 404;
 *  4. rotas de serviço recusam token de usuário e aceitam só credencial de serviço.
 * Só contra a aplicação local de teste.
 */
describe('Matriz de acesso indevido (papel × escola × posse)', () => {
  let t: AppDeTeste;
  const atoresA: Partial<Record<Papel, UsuarioDeTeste>> = {};
  const atoresB: Partial<Record<Papel, UsuarioDeTeste>> = {};
  const recursosB: Record<string, string> = {};
  const relatorio: string[] = [];

  const rotas = rotasDeclaradas().filter((r) => r.contrato && !r.contrato.interna);

  beforeAll(async () => {
    t = await criarApp();
    const a = await criarEscola(t);
    const b = await criarEscola(t);
    for (const p of PAPEIS) {
      const escola = p === 'platform_admin' || p === 'researcher' || p === 'guardian' ? null : a;
      atoresA[p] = await criarUsuario(t, p, escola);
      if (escola) atoresB[p] = await criarUsuario(t, p, b);
    }
    // Recursos da escola B (com consentimento, para que só a posse decida).
    const profB = atoresB.teacher!;
    const alunoB = await criarUsuario(t, 'student', b, { isMinor: false });
    const turma = await t.http().post(`${API}/classes`).set(...bearer(profB)).send({ name: 'B1', trackLevel: 'medio' });
    await t.http().post(`${API}/classes/${turma.body.id as string}/students`).set(...bearer(profB)).send({ studentIds: [alunoB.id] });
    const missao = await t.http().post(`${API}/missions`).set(...bearer(profB)).send({ title: 'm', objective: 'o', trackLevel: 'medio', bnccCodes: ['EM13CNT203'], classIds: [turma.body.id] });
    const planeta = await t.http().post(`${API}/planets`).set(...bearer(alunoB)).send({ params: {} });
    expect(planeta.status).toBe(201);
    recursosB.usuario = alunoB.id;
    recursosB.turma = turma.body.id as string;
    recursosB.missao = missao.body.id as string;
    recursosB.planeta = planeta.body.planetId as string;
  });

  afterAll(async () => {
    // Saída legível do que foi verificado (vai para o relatório de segurança).
    process.stdout.write(`\n[matriz-de-acesso] ${relatorio.length} verificações:\n${relatorio.join('\n')}\n`);
    await t.fechar();
  });

  const caminhoCom = (caminho: string, valores: Record<string, string>) =>
    caminho.replace(/\{(\w+)\}/g, (_, k: string) => valores[k] ?? '00000000-0000-4000-8000-000000000000');

  const chamar = (metodo: string, caminho: string, token?: string, consulta: Record<string, string> = {}, corpo: unknown = {}) => {
    const http = t.http();
    const url = `${API}${caminho}`;
    const req = metodo === 'GET' ? http.get(url) : metodo === 'POST' ? http.post(url) : metodo === 'PATCH' ? http.patch(url) : metodo === 'PUT' ? http.put(url) : http.delete(url);
    if (token) req.set('Authorization', `Bearer ${token}`);
    return req.query(consulta).send(corpo as object);
  };

  it('1. sem token → 401 em TODA rota não pública', async () => {
    for (const r of rotas.filter((x) => !('publico' in x.autorizacao!))) {
      const res = await chamar(r.contrato!.metodo, caminhoCom(r.contrato!.caminho, { code: 'EF07CI13', category: 'evidence', slug: 'x' }));
      relatorio.push(`sem token        ${r.contrato!.metodo.padEnd(6)} ${r.contrato!.caminho} → ${res.status}`);
      expect([r.contrato!.caminho, res.status]).toEqual([r.contrato!.caminho, 401]);
    }
  });

  it('2. papel fora da lista → 403 em toda rota com papéis', async () => {
    for (const r of rotas) {
      const a = r.autorizacao!;
      if (!('papeis' in a)) continue;
      const proibido = PAPEIS.find((p) => !a.papeis.includes(p));
      if (!proibido) continue;
      const res = await chamar(r.contrato!.metodo, caminhoCom(r.contrato!.caminho, { id: recursosB.usuario!, studentId: recursosB.usuario!, code: 'EF07CI13', category: 'evidence', slug: 'x' }), atoresA[proibido]!.token);
      relatorio.push(`papel ${proibido.padEnd(14)} ${r.contrato!.metodo.padEnd(6)} ${r.contrato!.caminho} → ${res.status}`);
      expect([r.contrato!.caminho, proibido, res.status]).toEqual([r.contrato!.caminho, proibido, 403]);
    }
  });

  it('3. recurso de OUTRA escola → 404 (não revela existência) em toda rota com posse', async () => {
    for (const r of rotas) {
      const a = r.autorizacao!;
      if (!('papeis' in a) || !a.posse) continue;
      const tipo = a.posse.regra.split(':')[0]!;
      const alvo = recursosB[tipo];
      if (!alvo) throw new Error(`sem recurso de teste para a regra ${a.posse.regra}`);
      // Escolhe um papel permitido que pertença à escola A (o guardião não tem escola: usa o da escola A sem vínculo).
      const papel = a.papeis.find((p) => atoresA[p] && p !== 'platform_admin') ?? a.papeis[0]!;
      if (papel === 'platform_admin') continue; // operador é transversal por desenho (só gestão de contas)
      const parametro = a.posse.parametro ?? 'id';
      const origem = a.posse.origem ?? 'params';
      const caminho = caminhoCom(r.contrato!.caminho, { [parametro]: alvo, id: alvo });
      const consulta = origem === 'query' ? { [parametro]: alvo, format: 'csv' } : {};
      const corpo = origem === 'body' ? { [parametro]: alvo, contextRef: 'x', missionId: recursosB.missao } : {};
      const res = await chamar(r.contrato!.metodo, caminho, atoresA[papel]!.token, consulta, corpo);
      relatorio.push(`outra escola ${papel.padEnd(11)} ${r.contrato!.metodo.padEnd(6)} ${r.contrato!.caminho} (${a.posse.regra}) → ${res.status}`);
      expect([r.contrato!.caminho, papel, res.status]).toEqual([r.contrato!.caminho, papel, 404]);
    }
  });

  it('4. rotas de serviço: token de usuário → 401; credencial de serviço válida passa', async () => {
    const servico = await ServicoDeTokens.emitirTokenDeServico(t.config.SERVICE_TOKEN_SECRET, 'ai-sim-service');
    const desconhecido = await ServicoDeTokens.emitirTokenDeServico(t.config.SERVICE_TOKEN_SECRET, 'servico-intruso');
    const interno = `/internal/consent/${recursosB.usuario!}`;
    expect((await chamar('GET', interno, atoresA.admin!.token)).status).toBe(401);
    expect((await chamar('GET', interno, desconhecido)).status).toBe(401);
    const ok = await chamar('GET', interno, servico);
    expect(ok.status).toBe(200);
    expect(Object.keys(ok.body as object).sort()).toEqual(['consentRequired', 'purposes', 'userId']);
    relatorio.push('serviço: token de usuário → 401; serviço não permitido → 401; ai-sim-service → 200 (resposta sem PII)');
  });
});
