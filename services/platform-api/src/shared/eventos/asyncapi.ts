import { z } from 'zod';

import {
  DadosCompetenciaAtualizada,
  DadosEvidenciaGerada,
  DadosRubricaAvaliada,
} from '../../modules/assessment/domain/eventos';

const js = (s: z.ZodType) => {
  const r = z.toJSONSchema(s, {
    io: 'input',
    unrepresentable: 'any',
  }) as Record<string, unknown>;
  delete r.$schema;
  return r;
};

const envelope = (dados: Record<string, unknown>) => ({
  type: 'object',
  required: ['eventId', 'type', 'version', 'occurredAt', 'data'],
  properties: {
    eventId: {
      type: 'string',
      description: 'Chave de idempotência do consumidor',
    },
    type: { type: 'string' },
    version: { const: 1 },
    occurredAt: { type: 'string', format: 'date-time' },
    traceId: { type: 'string' },
    producer: { type: 'string' },
    data: dados,
  },
});

/** Contrato assíncrono (AsyncAPI 3.0) entre platform-api e ai-sim-service sobre Redis Streams. */
export function gerarAsyncApi(): Record<string, unknown> {
  const uuid = { type: 'string', format: 'uuid' };
  const publicados: Record<string, Record<string, unknown>> = {
    PlanetaCriado: {
      type: 'object',
      properties: {
        planetId: uuid,
        studentId: uuid,
        schoolId: uuid,
        missionId: { type: ['string', 'null'] },
        seed: { type: 'string' },
      },
    },
    IntervencaoAplicada: {
      type: 'object',
      properties: {
        planetId: uuid,
        studentId: uuid,
        action: { type: 'string' },
        target: { type: 'string' },
        cost: { type: 'object' },
        tickId: { type: 'integer' },
      },
    },
    ConsentimentoConcedido: {
      type: 'object',
      properties: {
        studentId: uuid,
        purposes: { type: 'array', items: { type: 'string' } },
        textVersion: { type: 'string' },
        at: { type: 'string', format: 'date-time' },
      },
    },
    ConsentimentoRevogado: {
      type: 'object',
      description:
        'Ao receber, pare de coletar dados do aluno para as finalidades indicadas.',
      properties: {
        studentId: uuid,
        purposes: { type: 'array', items: { type: 'string' } },
        at: { type: 'string', format: 'date-time' },
      },
    },
    MissaoPublicada: {
      type: 'object',
      properties: {
        missionId: uuid,
        classIds: { type: 'array', items: uuid },
        bnccCodes: { type: 'array', items: { type: 'string' } },
      },
    },
    TitularExcluido: {
      type: 'object',
      description:
        'Direito de exclusão: apague estado e telemetria do titular.',
      properties: {
        subjectId: uuid,
        planetIds: { type: 'array', items: uuid },
      },
    },
  };
  const consumidos: Record<string, Record<string, unknown>> = {
    EvidenciaGerada: js(DadosEvidenciaGerada),
    CompetenciaAtualizada: js(DadosCompetenciaAtualizada),
    RubricaAvaliada: js(DadosRubricaAvaliada),
  };
  const mensagens = (m: Record<string, Record<string, unknown>>) =>
    Object.fromEntries(
      Object.entries(m).map(([k, v]) => [
        k,
        {
          name: k,
          payload: envelope(v),
          headers: { type: 'object', properties: { type: { const: k } } },
        },
      ]),
    );
  return {
    asyncapi: '3.0.0',
    info: {
      title: 'ECOSFERA — eventos de domínio',
      version: '1.0.0',
      description:
        'Transporte: Redis Streams (campo `envelope` com o JSON). Trocável por NATS (ADR 0010). Entrega pelo menos uma vez: deduplique por eventId.',
    },
    channels: {
      platformEvents: {
        address: 'ecosfera.events.platform',
        description: 'Publicado pelo platform-api (outbox transacional)',
        messages: mensagens(publicados),
      },
      assessmentEvents: {
        address: 'ecosfera.events.assessment',
        description:
          'Publicado pelo ai-sim-service; consumido pelo platform-api (grupo platform-api)',
        messages: mensagens(consumidos),
      },
    },
    operations: {
      publicarEventosDaPlataforma: {
        action: 'send',
        channel: { $ref: '#/channels/platformEvents' },
      },
      consumirEventosDeAvaliacao: {
        action: 'receive',
        channel: { $ref: '#/channels/assessmentEvents' },
      },
    },
  };
}
