import http from 'node:http';
import type { AddressInfo } from 'node:net';

import {
  ErroDeDependencia,
  ErroPontosDeAcaoInsuficientes,
} from '../../../shared/kernel/erros';
import { Metricas } from '../../../shared/observabilidade/metricas';
import type { SimulationGateway } from '../domain/portas';
import { SimulacaoHttp } from './adaptadores-http';
import { ClienteHttpDoServico } from './cliente-http';

describe('Adaptador HTTP do ai-sim-service: timeout, repetição limitada, degradação graciosa', () => {
  let servidor: http.Server;
  let url: string;
  const chamadas: string[] = [];
  let modo: 'ok' | 'lento' | '500' | '409' = 'ok';

  beforeAll(async () => {
    servidor = http.createServer((req, res) => {
      chamadas.push(
        `${req.method} ${req.url} tp=${req.headers.traceparent ? 's' : 'n'} auth=${req.headers.authorization ? 's' : 'n'}`,
      );
      if (modo === 'lento') return setTimeout(() => res.end('{}'), 500);
      if (modo === '500') return res.writeHead(500).end('{}');
      if (modo === '409')
        return res.writeHead(409, { 'content-type': 'application/json' }).end(
          JSON.stringify({
            type: '/errors/insufficient-action-points',
            actionPoints: { remaining: 1, required: 3 },
          }),
        );
      res
        .writeHead(200, { 'content-type': 'application/json' })
        .end(JSON.stringify({ state: {}, era: 2, indicators: { co2: 300 } }));
    });
    await new Promise<void>((ok) => servidor.listen(0, '127.0.0.1', ok));
    url = `http://127.0.0.1:${(servidor.address() as AddressInfo).port}`;
  });
  afterAll(() => new Promise((ok) => servidor.close(ok)));
  beforeEach(() => (chamadas.length = 0));

  const sim = (): SimulationGateway =>
    new SimulacaoHttp(
      new ClienteHttpDoServico(
        {
          baseUrl: url,
          timeoutMs: 100,
          repeticoes: 2,
          nomeDaDependencia: 'ai-sim-service',
          token: () => Promise.resolve('t'),
        },
        new Metricas(false),
      ),
    );
  const ctx = { alunoId: 'a', escolaId: 'e' };

  it('sucesso repassa a resposta e envia credencial de serviço', async () => {
    modo = 'ok';
    await expect(sim().estado('p1', ctx)).resolves.toMatchObject({ era: 2 });
    expect(chamadas[0]).toContain('auth=s');
  });
  it('timeout em GET: repete (2x) e termina em 504 tratado', async () => {
    modo = 'lento';
    const e = await sim()
      .estado('p1', ctx)
      .catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ErroDeDependencia);
    expect((e as ErroDeDependencia).tipo).toBe('dependency-timeout');
    expect(chamadas).toHaveLength(3);
  });
  it('5xx em POST não idempotente: NÃO repete e vira 503', async () => {
    modo = '500';
    const e = await sim()
      .intervir(
        'p1',
        { action: 'X', target: 't', cost: { actionPoints: 1 } },
        ctx,
      )
      .catch((x: unknown) => x);
    expect((e as ErroDeDependencia).tipo).toBe('dependency-unavailable');
    expect(chamadas).toHaveLength(1);
  });
  it('409 do serviço vira pontos de ação insuficientes', async () => {
    modo = '409';
    await expect(
      sim().intervir(
        'p1',
        { action: 'X', target: 't', cost: { actionPoints: 3 } },
        ctx,
      ),
    ).rejects.toBeInstanceOf(ErroPontosDeAcaoInsuficientes);
  });
  it('serviço fora do ar vira 503', async () => {
    const off: SimulationGateway = new SimulacaoHttp(
      new ClienteHttpDoServico(
        {
          baseUrl: 'http://127.0.0.1:1',
          timeoutMs: 200,
          repeticoes: 0,
          nomeDaDependencia: 'ai-sim-service',
        },
        new Metricas(false),
      ),
    );
    await expect(off.estado('p', ctx)).rejects.toBeInstanceOf(
      ErroDeDependencia,
    );
  });
});
