import { createHash, randomUUID } from 'node:crypto';

import type { Redis } from 'ioredis';
import type { Logger } from 'pino';

import { ErroDeValidacao, ErroNaoEncontrado, ErroPontosDeAcaoInsuficientes } from '../../../shared/kernel/erros';
import type { ChavesRedis } from '../../../shared/redis/chaves';
import type {
  ContextoDaChamada,
  EstadoDoPlaneta,
  Intervencao,
  PublicadorDoPlaneta,
  ResultadoDaIntervencao,
  ResultadoDoTick,
  SimulationGateway,
} from '../domain/portas';

/** PRNG determinístico (mulberry32) a partir do seed. */
function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const numeroDoSeed = (s: string) => createHash('sha256').update(s).digest().readUInt32BE(0);

interface EstadoFalso {
  seed: string;
  tick: number;
  era: number;
  actionPoints: number;
  indicators: Record<string, number>;
  series: Record<string, { tick: number; value: number }[]>;
  checkpoints: { checkpointId: string; tick: number; era: number }[];
  eras: { era: number; startedAtTick: number }[];
  events: { eventId: string; kind: string; tick: number; status: string; options: string[] }[];
  interventions: number;
}

/** Tabela de efeitos do FAKE (não é ciência: o real é o ai-sim-service). */
const ACOES: Record<string, { delta: Record<string, number>; tradeoffs: { gain: string; cost: string }[]; competencias: string[] }> = {
  INDUSTRIALIZE: { delta: { prosperity: 5, co2: 20, temperature: 0.3 }, tradeoffs: [{ gain: 'prosperity+', cost: 'co2+, temp+' }], competencias: ['DECISION_MAKING', 'CONSEQUENCE_ANALYSIS'] },
  REFOREST: { delta: { co2: -10, biodiversity: 3, prosperity: -1 }, tradeoffs: [{ gain: 'co2-, biodiversity+', cost: 'prosperity-' }], competencias: ['SYSTEMS_THINKING', 'CAUSE_EFFECT'] },
  PROTECT_AREA: { delta: { biodiversity: 5, prosperity: -2 }, tradeoffs: [{ gain: 'biodiversity+', cost: 'prosperity-' }], competencias: ['CONSEQUENCE_ANALYSIS'] },
  RENEWABLE_ENERGY: { delta: { co2: -15, prosperity: 1 }, tradeoffs: [{ gain: 'co2-', cost: 'energy cost' }], competencias: ['DECISION_MAKING', 'SCIENTIFIC_THINKING'] },
};
const PONTOS_INICIAIS = 5;
const MAX_PONTOS = 10;

/**
 * FAKE do SimulationGateway. Identificável (nome "FAKE"), log a cada criação, proibido em produção.
 * Estado no Redis (TTL 7 dias) para o processo continuar sem estado.
 * Emite EvidênciaGerada/CompetênciaAtualizada SINTÉTICAS no stream de avaliação, como faria o ai-sim-service.
 */
export class SimulacaoFalsa implements SimulationGateway {
  readonly nome = 'FAKE:SimulationGateway';

  constructor(
    private readonly redis: Redis,
    private readonly chaves: ChavesRedis,
    private readonly stream: PublicadorDoPlaneta,
    private readonly logger: Logger,
    private readonly streamDeAvaliacao: string,
  ) {}

  private async ler(id: string): Promise<EstadoFalso> {
    const s = await this.redis.get(this.chaves.simulacaoFalsa(id));
    if (!s) throw new ErroNaoEncontrado('Planeta (no serviço de simulação)');
    return JSON.parse(s) as EstadoFalso;
  }
  private async gravar(id: string, e: EstadoFalso): Promise<void> {
    await this.redis.set(this.chaves.simulacaoFalsa(id), JSON.stringify(e), 'EX', 7 * 24 * 3600);
  }

  private publico(e: EstadoFalso): EstadoDoPlaneta {
    return { state: { tick: e.tick, simulated: true, source: 'FAKE' }, era: e.era, indicators: e.indicators };
  }

  async criarPlaneta(id: string, seed: string, params: Record<string, unknown>): Promise<EstadoDoPlaneta> {
    const r = prng(numeroDoSeed(seed));
    const massa = typeof params.mass === 'number' ? params.mass : 1;
    const e: EstadoFalso = {
      seed,
      tick: 0,
      era: 0,
      actionPoints: PONTOS_INICIAIS,
      indicators: {
        temperature: Math.round((14 + r() * 4 + (massa - 1) * 2) * 100) / 100,
        co2: Math.round(280 + r() * 40),
        biodiversity: Math.round(50 + r() * 20),
        prosperity: Math.round(10 + r() * 10),
      },
      series: {},
      checkpoints: [],
      eras: [{ era: 0, startedAtTick: 0 }],
      events: [],
      interventions: 0,
    };
    for (const [k, v] of Object.entries(e.indicators)) e.series[k] = [{ tick: 0, value: v }];
    await this.gravar(id, e);
    this.logger.info({ fake: this.nome, planetId: id }, '[FAKE] planeta criado pelo adaptador falso');
    return this.publico(e);
  }

  async estado(id: string) {
    return this.publico(await this.ler(id));
  }

  validar(_id: string, params: Record<string, unknown>) {
    const avisos: string[] = [];
    const massa = params.mass;
    if (massa !== undefined && (typeof massa !== 'number' || massa <= 0 || massa > 10)) {
      throw new ErroDeValidacao('Parâmetros fora da faixa permitida', [{ campo: 'body.params.mass', mensagem: 'massa fora da faixa permitida (0 < massa ≤ 10)' }]);
    }
    if (typeof massa === 'number' && massa > 5) avisos.push('Massa alta: gravidade intensa pode dificultar a vida complexa');
    const dist = params.orbitAu;
    if (typeof dist === 'number' && (dist < 0.8 || dist > 1.5)) avisos.push('Órbita fora da zona habitável estimada');
    return Promise.resolve({ ok: true, warnings: avisos });
  }

  private passar(e: EstadoFalso, passos: number): Record<string, number> {
    const r = prng(numeroDoSeed(`${e.seed}:${e.tick}`));
    const antes = { ...e.indicators };
    for (let i = 0; i < passos; i++) {
      e.tick += 1;
      e.indicators.temperature = Math.round((e.indicators.temperature! + (e.indicators.co2! - 300) * 0.001 + (r() - 0.5) * 0.05) * 100) / 100;
      e.indicators.biodiversity = Math.max(0, Math.round(e.indicators.biodiversity! - Math.max(0, e.indicators.temperature! - 18) * 0.5 + (r() - 0.5)));
      if (e.tick % 10 === 0) {
        e.era += 1;
        e.eras.push({ era: e.era, startedAtTick: e.tick });
        e.actionPoints = Math.min(MAX_PONTOS, e.actionPoints + 2);
        if (e.era % 2 === 1) e.events.push({ eventId: randomUUID(), kind: 'DROUGHT', tick: e.tick, status: 'open', options: ['IRRIGATE', 'WAIT'] });
      }
      for (const [k, v] of Object.entries(e.indicators)) (e.series[k] ??= []).push({ tick: e.tick, value: v });
    }
    return Object.fromEntries(Object.keys(antes).map((k) => [k, Math.round((e.indicators[k]! - antes[k]!) * 100) / 100]));
  }

  async avancar(id: string, passos: number, _vel: number, assincrono: boolean): Promise<ResultadoDoTick> {
    const e = await this.ler(id);
    if (!assincrono) {
      const delta = this.passar(e, passos);
      await this.gravar(id, e);
      await this.stream.publicar(id, { type: 'delta', payload: { delta, era: e.era, source: 'FAKE' }, tickId: e.tick });
      return { tipo: 'sincrono', delta, era: e.era, tickId: e.tick };
    }
    const jobId = randomUUID();
    setTimeout(() => {
      void (async () => {
        const atual = await this.ler(id);
        const delta = this.passar(atual, passos);
        await this.gravar(id, atual);
        await this.stream.publicar(id, { type: 'delta', payload: { delta, era: atual.era, jobId, source: 'FAKE' }, tickId: atual.tick });
      })().catch((err: Error) => this.logger.error({ err: err.message }, '[FAKE] tick assíncrono falhou'));
    }, 50).unref();
    return { tipo: 'assincrono', jobId };
  }

  async intervir(id: string, i: Intervencao, ctx: ContextoDaChamada): Promise<ResultadoDaIntervencao> {
    const efeito = ACOES[i.action];
    if (!efeito) throw new ErroDeValidacao('Ação desconhecida', [{ campo: 'body.action', mensagem: `ações: ${Object.keys(ACOES).join(', ')}` }]);
    const e = await this.ler(id);
    if (e.actionPoints < i.cost.actionPoints) throw new ErroPontosDeAcaoInsuficientes(e.actionPoints, i.cost.actionPoints);
    e.actionPoints -= i.cost.actionPoints;
    for (const [k, v] of Object.entries(efeito.delta)) e.indicators[k] = Math.round(((e.indicators[k] ?? 0) + v) * 100) / 100;
    e.interventions += 1;
    e.tick += 1;
    for (const [k, v] of Object.entries(e.indicators)) (e.series[k] ??= []).push({ tick: e.tick, value: v });
    await this.gravar(id, e);
    await this.stream.publicar(id, { type: 'delta', payload: { delta: efeito.delta, action: i.action, source: 'FAKE' }, tickId: e.tick });
    await this.emitirAvaliacaoSintetica(id, e, i, efeito.competencias, ctx);
    return { delta: efeito.delta, tradeoffs: efeito.tradeoffs, actionPoints: { remaining: e.actionPoints }, tickId: e.tick };
  }

  /** Simula o que o ai-sim-service faria: evidência + estimativa, marcadas como sintéticas. */
  private async emitirAvaliacaoSintetica(planetaId: string, e: EstadoFalso, i: Intervencao, competencias: string[], ctx: ContextoDaChamada) {
    const r = prng(numeroDoSeed(`${e.seed}:av:${e.interventions}`));
    const agora = new Date().toISOString();
    for (const c of competencias) {
      const envelopes = [
        {
          eventId: randomUUID(), type: 'EvidenciaGerada', version: 1, occurredAt: agora, traceId: '', producer: 'FAKE:ai-sim-service',
          data: { studentId: ctx.alunoId, planetId: planetaId, competencyCode: c, type: 'intervention', payload: { action: i.action, target: i.target }, synthetic: true },
        },
        {
          eventId: randomUUID(), type: 'CompetenciaAtualizada', version: 1, occurredAt: agora, traceId: '', producer: 'FAKE:ai-sim-service',
          data: { studentId: ctx.alunoId, competencyCode: c, probability: Math.round(r() * 10000) / 10000, uncertainty: Math.round((0.1 + r() * 0.3) * 10000) / 10000, synthetic: true },
        },
      ];
      for (const env of envelopes) await this.redis.xadd(this.streamDeAvaliacao, '*', 'envelope', JSON.stringify(env), 'type', env.type);
    }
  }

  async linhaDoTempo(id: string) {
    const e = await this.ler(id);
    return { eras: e.eras, checkpoints: e.checkpoints };
  }

  async salvarCheckpoint(id: string) {
    const e = await this.ler(id);
    const c = { checkpointId: randomUUID(), tick: e.tick, era: e.era };
    e.checkpoints.push(c);
    await this.gravar(id, e);
    return { checkpointId: c.checkpointId };
  }

  async series(id: string, metrica: string) {
    const e = await this.ler(id);
    const s = e.series[metrica];
    if (!s) throw new ErroDeValidacao('Métrica desconhecida', [{ campo: 'query.metric', mensagem: `métricas: ${Object.keys(e.series).join(', ')}` }]);
    return { metric: metrica, points: s };
  }

  async eventos(id: string) {
    return { events: (await this.ler(id)).events };
  }

  async responderEvento(id: string, eventId: string, escolha: string) {
    const e = await this.ler(id);
    const ev = e.events.find((x) => x.eventId === eventId);
    if (!ev) throw new ErroNaoEncontrado('Evento');
    if (ev.status !== 'open') throw new ErroDeValidacao('Evento já respondido', [{ campo: 'body.eventId', mensagem: 'encerrado' }]);
    if (!ev.options.includes(escolha)) throw new ErroDeValidacao('Opção inválida', [{ campo: 'body.choice', mensagem: `opções: ${ev.options.join(', ')}` }]);
    ev.status = 'resolved';
    const delta: Record<string, number> = escolha === 'IRRIGATE' ? { prosperity: -1, biodiversity: 1 } : { biodiversity: -2 };
    for (const [k, v] of Object.entries(delta)) e.indicators[k] = (e.indicators[k] ?? 0) + v;
    await this.gravar(id, e);
    await this.stream.publicar(id, { type: 'event', payload: { eventId, outcome: escolha, delta, source: 'FAKE' }, tickId: e.tick });
    return { outcome: escolha, delta };
  }
}
