import { z } from 'zod';

/**
 * Eventos consumidos do ai-sim-service (contrato assíncrono, packages/api-contracts/asyncapi).
 * O cálculo é do serviço; o platform-api só projeta.
 */
export const DadosEvidenciaGerada = z.object({
  studentId: z.uuid(),
  planetId: z.uuid().optional(),
  competencyCode: z.string().min(1).max(64),
  bnccCode: z.string().max(20).optional(),
  type: z.string().min(1).max(64),
  payload: z.record(z.string(), z.unknown()).default({}),
  synthetic: z.boolean().default(false),
});

export const DadosCompetenciaAtualizada = z.object({
  studentId: z.uuid(),
  competencyCode: z.string().min(1).max(64),
  probability: z.number().min(0).max(1),
  uncertainty: z.number().min(0).max(1).optional(),
  synthetic: z.boolean().default(false),
});

export const DadosRubricaAvaliada = z.object({
  studentId: z.uuid(),
  competencyCode: z.string().min(1).max(64).optional(),
  missionId: z.uuid().optional(),
  score: z.number().min(0).max(100),
  details: z.record(z.string(), z.unknown()).default({}),
});

export const EnvelopeConsumido = z.object({
  eventId: z.string().min(8).max(100),
  type: z.enum(['EvidenciaGerada', 'CompetenciaAtualizada', 'RubricaAvaliada']),
  version: z.literal(1).default(1),
  occurredAt: z.iso.datetime({ offset: true }),
  traceId: z.string().max(64).optional(),
  producer: z.string().max(64).optional(),
  data: z.record(z.string(), z.unknown()),
});
export type EnvelopeConsumido = z.infer<typeof EnvelopeConsumido>;
