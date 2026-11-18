import type { EnvelopeDeEvento } from './eventos';

/** Porta de publicação no barramento. Redis Streams hoje; NATS depois (ADR 0010). */
export interface EventPublisher {
  publicar(topico: string, e: EnvelopeDeEvento): Promise<string>;
}
export const EVENT_PUBLISHER = Symbol('EventPublisher');

export type ResultadoDoTratamento =
  'processed' | 'duplicate' | 'skipped_no_consent' | 'ignored';
export type TratadorDeEvento = (
  e: EnvelopeDeEvento,
) => Promise<ResultadoDoTratamento>;

/** Porta de consumo dos eventos de avaliação vindos do ai-sim-service. */
export interface AssessmentEventSource {
  iniciar(tratador: TratadorDeEvento): Promise<void>;
  parar(): Promise<void>;
}
export const ASSESSMENT_EVENT_SOURCE = Symbol('AssessmentEventSource');
