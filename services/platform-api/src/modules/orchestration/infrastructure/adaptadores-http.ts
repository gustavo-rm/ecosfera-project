import { randomUUID } from 'node:crypto';

import { ErroDeDependencia } from '../../../shared/kernel/erros';
import type {
  ContextoDaChamada,
  EstadoDoPlaneta,
  Intervencao,
  ResultadoDaIntervencao,
  ResultadoDoTick,
  SimulationGateway,
  TutorGateway,
} from '../domain/portas';
import type { ClienteHttpDoServico } from './cliente-http';

/**
 * Adaptador REAL do SimulationGateway sobre HTTP. O contrato interno com o ai-sim-service
 * é uma PROPOSTA (docs/backend/PEDIDOS_A_OUTRAS_FRENTES.md, P4): base /simulation/api/v1.
 */
export class SimulacaoHttp implements SimulationGateway {
  readonly nome = 'http:ai-sim-service';
  constructor(private readonly c: ClienteHttpDoServico) {}

  private p(id: string, resto = '') {
    return `/simulation/api/v1/planets/${encodeURIComponent(id)}${resto}`;
  }

  criarPlaneta(id: string, seed: string, params: Record<string, unknown>, ctx: ContextoDaChamada) {
    return this.c.requisitar<EstadoDoPlaneta>('POST', '/simulation/api/v1/planets', { planetId: id, seed, params, context: ctx }, { idempotente: true, operacao: 'createPlanet' });
  }
  estado(id: string) {
    return this.c.requisitar<EstadoDoPlaneta>('GET', this.p(id), undefined, { operacao: 'getPlanet' });
  }
  validar(id: string, params: Record<string, unknown>) {
    return this.c.requisitar<{ ok: boolean; warnings: string[] }>('POST', this.p(id, '/validate'), { params }, { idempotente: true, operacao: 'validate' });
  }
  avancar(id: string, steps: number, speed: number, assincrono: boolean, ctx: ContextoDaChamada) {
    return this.c.requisitar<ResultadoDoTick>('POST', this.p(id, '/tick'), { steps, speed, async: assincrono, context: ctx, requestId: randomUUID() }, { operacao: 'tick' });
  }
  intervir(id: string, i: Intervencao, ctx: ContextoDaChamada) {
    return this.c.requisitar<ResultadoDaIntervencao>('POST', this.p(id, '/interventions'), { ...i, context: ctx }, { operacao: 'intervention' });
  }
  linhaDoTempo(id: string) {
    return this.c.requisitar<Awaited<ReturnType<SimulationGateway['linhaDoTempo']>>>('GET', this.p(id, '/timeline'), undefined, { operacao: 'timeline' });
  }
  salvarCheckpoint(id: string, ctx: ContextoDaChamada) {
    return this.c.requisitar<{ checkpointId: string }>('POST', this.p(id, '/checkpoints'), { context: ctx }, { operacao: 'checkpoint' });
  }
  series(id: string, metrica: string) {
    return this.c.requisitar<Awaited<ReturnType<SimulationGateway['series']>>>('GET', this.p(id, `/series?metric=${encodeURIComponent(metrica)}`), undefined, { operacao: 'series' });
  }
  eventos(id: string) {
    return this.c.requisitar<Awaited<ReturnType<SimulationGateway['eventos']>>>('GET', this.p(id, '/events'), undefined, { operacao: 'events' });
  }
  responderEvento(id: string, eventId: string, escolha: string, ctx: ContextoDaChamada) {
    return this.c.requisitar<{ outcome: string; delta: Record<string, number> }>('POST', this.p(id, '/events/respond'), { eventId, choice: escolha, context: ctx }, { operacao: 'respondEvent' });
  }
}

/** Adaptador REAL do TutorGateway. O SSE é lido em fluxo e repassado sem acumular. */
export class TutorHttp implements TutorGateway {
  readonly nome = 'http:ai-sim-service';
  constructor(private readonly c: ClienteHttpDoServico) {}

  async *explicar(p: { planetId: string; contextRef: string; question?: string }, ctx: ContextoDaChamada): AsyncIterable<string> {
    let res: Response;
    try {
      res = await this.c.fetch('POST', '/tutor/api/v1/explain', { ...p, context: ctx }, 'text/event-stream');
    } catch (e) {
      throw new ErroDeDependencia('tutor', (e as Error).name === 'TimeoutError');
    }
    if (!res.ok || !res.body) throw new ErroDeDependencia('tutor');
    const leitor = res.body.pipeThrough(new TextDecoderStream()).getReader();
    let resto = '';
    for (;;) {
      const { value, done } = await leitor.read();
      if (done) break;
      resto += value;
      const blocos = resto.split('\n\n');
      resto = blocos.pop() ?? '';
      for (const b of blocos) {
        const dados = b.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trimStart()).join('\n');
        if (!dados) continue;
        try {
          const j = JSON.parse(dados) as { text?: string };
          if (typeof j.text === 'string') yield j.text;
        } catch {
          yield dados;
        }
      }
    }
  }
  dica(p: { planetId: string; missionId: string }, ctx: ContextoDaChamada) {
    return this.c.requisitar<{ hint: string; level: number }>('POST', '/tutor/api/v1/hint', { ...p, context: ctx }, { operacao: 'hint' });
  }
  conselheiro(p: { role: string; query: string }, ctx: ContextoDaChamada) {
    return this.c.requisitar<{ advice: string }>('POST', '/tutor/api/v1/advisor', { ...p, context: ctx }, { operacao: 'advisor' });
  }
  adaptacao(ctx: ContextoDaChamada) {
    return this.c.requisitar<{ difficulty: string; unlocks: string[] }>('GET', `/tutor/api/v1/adaptation/${encodeURIComponent(ctx.alunoId)}`, undefined, { operacao: 'adaptation' });
  }
}
