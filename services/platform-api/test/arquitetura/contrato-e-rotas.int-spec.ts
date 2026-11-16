import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { ModulesContainer } from '@nestjs/core';
import { stringify } from 'yaml';

import { CONTROLADORES, rotasDeclaradas } from '../../src/shared/http/catalogo-de-rotas';
import { gerarOpenApi } from '../../src/shared/http/openapi';
import { type AppDeTeste, criarApp } from '../support/app';
import { validar, violacoes } from '../support/contrato';

describe('Arquitetura e contrato (TASK-0023/0025/0027, princípio "negue por padrão")', () => {
  let t: AppDeTeste;
  beforeAll(async () => {
    t = await criarApp();
  });
  afterAll(() => t.fechar());

  it('TODA rota tem @Endpoint (contrato) e @Autorizacao (declaração explícita)', () => {
    const rotas = rotasDeclaradas();
    expect(rotas.length).toBeGreaterThan(80);
    const semContrato = rotas.filter((r) => !r.contrato).map((r) => `${r.controlador}.${r.metodoDaClasse}`);
    const semAutorizacao = rotas.filter((r) => !r.autorizacao).map((r) => `${r.controlador}.${r.metodoDaClasse}`);
    expect(semContrato).toEqual([]);
    expect(semAutorizacao).toEqual([]);
  });

  it('rotas públicas são só as justificadas (lista fechada)', () => {
    const publicas = rotasDeclaradas()
      .filter((r) => r.autorizacao && 'publico' in r.autorizacao)
      .map((r) => `${r.contrato!.metodo} ${r.contrato!.caminho}`)
      .sort();
    expect(publicas).toEqual([
      'GET /auth/lti/login', 'GET /auth/oidc/{slug}/authorize', 'GET /auth/oidc/{slug}/callback', 'GET /files', 'GET /health', 'GET /metrics', 'GET /ready',
      'POST /auth/login', 'POST /auth/lti/launch', 'POST /auth/password/forgot', 'POST /auth/password/reset', 'POST /auth/refresh',
    ]);
  });

  it('a lista de controladores do catálogo é exatamente a registrada no app', () => {
    const noApp = new Set<string>();
    for (const m of t.app.get(ModulesContainer).values()) for (const c of m.controllers.keys()) noApp.add((c as { name: string }).name);
    expect([...noApp].sort()).toEqual(CONTROLADORES.map((c) => c.name).sort());
  });

  it('o OpenAPI congelado em packages/api-contracts está em dia com o código', () => {
    const arq = join(__dirname, '..', '..', '..', '..', 'packages', 'api-contracts', 'openapi', 'platform-api.v1.yaml');
    const atual = readFileSync(arq, 'utf8').split('\n').slice(1).join('\n');
    expect(atual).toBe(stringify(gerarOpenApi(), { lineWidth: 0, aliasDuplicateObjects: false }));
  });

  it('o validador de contrato detecta corpo e status fora do contrato', () => {
    const antes = violacoes.length;
    validar('GET', '/platform/api/v1/health', 200, 'application/json', JSON.stringify({ status: 'quebrado' }));
    validar('GET', '/platform/api/v1/health', 418, 'application/json', '{}');
    validar('POST', '/platform/api/v1/auth/login', 200, 'application/json', JSON.stringify({ accessToken: 1 }));
    expect(violacoes.length - antes).toBe(3);
    violacoes.splice(antes);
  });

  it('rota inexistente responde 404 RFC 7807', async () => {
    const r = await t.http().get('/platform/api/v1/nao-existe');
    expect(r.status).toBe(404);
    expect(r.body.type).toBe('/errors/not-found');
  });
});
