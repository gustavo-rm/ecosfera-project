/**
 * Portas do gateway. O platform-api NÃO calcula o planeta nem a avaliação:
 * autoriza, registra, repassa e compõe. Quando o ai-sim-service existir, só os adaptadores mudam.
 */

/** Contexto enviado ao serviço. Só identificadores opacos; nunca nome, e-mail ou texto pessoal. */
export interface ContextoDaChamada {
  alunoId: string;
  escolaId: string | null;
  traceparent?: string;
}

export type Indicadores = Record<string, number>;

export interface EstadoDoPlaneta {
  state: Record<string, unknown>;
  era: number;
  indicators: Indicadores;
}

export interface Intervencao {
  action: string;
  target: string;
  cost: { actionPoints: number; energy?: number };
}

export interface ResultadoDaIntervencao {
  delta: Record<string, number>;
  tradeoffs: { gain: string; cost: string }[];
  actionPoints: { remaining: number };
  tickId: number;
}

export type ResultadoDoTick =
  | { tipo: 'sincrono'; delta: Record<string, number>; era: number; tickId: number }
  | { tipo: 'assincrono'; jobId: string };

export interface SimulationGateway {
  readonly nome: string;
  criarPlaneta(planetaId: string, seed: string, params: Record<string, unknown>, ctx: ContextoDaChamada): Promise<EstadoDoPlaneta>;
  estado(planetaId: string, ctx: ContextoDaChamada): Promise<EstadoDoPlaneta>;
  validar(planetaId: string, params: Record<string, unknown>, ctx: ContextoDaChamada): Promise<{ ok: boolean; warnings: string[] }>;
  avancar(planetaId: string, passos: number, velocidade: number, assincrono: boolean, ctx: ContextoDaChamada): Promise<ResultadoDoTick>;
  intervir(planetaId: string, i: Intervencao, ctx: ContextoDaChamada): Promise<ResultadoDaIntervencao>;
  linhaDoTempo(planetaId: string, ctx: ContextoDaChamada): Promise<{ eras: { era: number; startedAtTick: number }[]; checkpoints: { checkpointId: string; tick: number; era: number }[] }>;
  salvarCheckpoint(planetaId: string, ctx: ContextoDaChamada): Promise<{ checkpointId: string }>;
  series(planetaId: string, metrica: string, ctx: ContextoDaChamada): Promise<{ metric: string; points: { tick: number; value: number }[] }>;
  eventos(planetaId: string, ctx: ContextoDaChamada): Promise<{ events: { eventId: string; kind: string; tick: number; status: string; options: string[] }[] }>;
  responderEvento(planetaId: string, eventId: string, escolha: string, ctx: ContextoDaChamada): Promise<{ outcome: string; delta: Record<string, number> }>;
}
export const SIMULATION_GATEWAY = Symbol('SimulationGateway');

export interface TutorGateway {
  readonly nome: string;
  explicar(p: { planetId: string; contextRef: string; question?: string }, ctx: ContextoDaChamada): AsyncIterable<string>;
  dica(p: { planetId: string; missionId: string }, ctx: ContextoDaChamada): Promise<{ hint: string; level: number }>;
  conselheiro(p: { role: string; query: string }, ctx: ContextoDaChamada): Promise<{ advice: string }>;
  adaptacao(ctx: ContextoDaChamada): Promise<{ difficulty: string; unlocks: string[] }>;
}
export const TUTOR_GATEWAY = Symbol('TutorGateway');

export type TipoDeMensagemDoStream = 'delta' | 'event' | 'tutor' | 'alert';
export interface MensagemDoStream {
  type: TipoDeMensagemDoStream;
  payload: Record<string, unknown>;
  tickId: number;
}

/** Fan-out das mensagens do planeta para todas as réplicas (Redis pub/sub). */
export interface PublicadorDoPlaneta {
  publicar(planetaId: string, m: MensagemDoStream): Promise<void>;
}
export const PUBLICADOR_DO_PLANETA = Symbol('PublicadorDoPlaneta');
