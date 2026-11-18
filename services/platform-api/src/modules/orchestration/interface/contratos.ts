import { z } from 'zod';

import { definirEndpoint } from '../../../shared/http/contrato';
import { ParametroId, Uuid } from '../../../shared/http/esquemas-comuns';

const Params = z.record(z.string(), z.unknown());
const Delta = z.record(z.string(), z.number());
const Indicadores = z.record(z.string(), z.number());

export const EsquemaEstado = z
  .object({
    state: z.record(z.string(), z.unknown()),
    era: z.number().int(),
    indicators: Indicadores,
  })
  .meta({ id: 'PlanetState' });
export const EsquemaNovoPlaneta = z
  .object({
    params: Params,
    seed: z.string().min(1).max(64).optional(),
    missionId: Uuid.optional(),
  })
  .strict()
  .meta({ id: 'CreatePlanetRequest' });
const EsquemaPlanetaCriado = z
  .object({ planetId: Uuid, seed: z.string(), state: EsquemaEstado })
  .meta({ id: 'PlanetCreated' });
const EsquemaPlaneta = EsquemaEstado.extend({
  planetId: Uuid,
  ownerId: Uuid,
  missionId: Uuid.nullable(),
}).meta({ id: 'Planet' });
export const EsquemaValidar = z
  .object({ params: Params })
  .strict()
  .meta({ id: 'ValidateParamsRequest' });
const EsquemaValidacao = z
  .object({ ok: z.boolean(), warnings: z.array(z.string()) })
  .meta({ id: 'ValidateParamsResult' });
export const EsquemaTick = z
  .object({
    steps: z.number().int().min(1).max(1000),
    speed: z.number().min(0.1).max(10).default(1),
  })
  .strict()
  .meta({ id: 'TickRequest' });
const EsquemaTickSincrono = z
  .object({ delta: Delta, era: z.number().int(), tickId: z.number().int() })
  .meta({ id: 'TickResult' });
const EsquemaTickAssincrono = z.object({ jobId: Uuid }).meta({
  id: 'TickJob',
  description: 'Resultado chega pelo WebSocket /planets/{id}/stream',
});
export const EsquemaIntervencao = z
  .object({
    action: z.string().regex(/^[A-Z_]{2,40}$/),
    target: z.string().min(1).max(64),
    cost: z
      .object({
        actionPoints: z.number().int().min(0).max(10),
        energy: z.number().min(0).max(1000).optional(),
      })
      .strict(),
  })
  .strict()
  .meta({ id: 'InterventionRequest' });
const EsquemaResultadoIntervencao = z
  .object({
    delta: Delta,
    tradeoffs: z.array(z.object({ gain: z.string(), cost: z.string() })),
    actionPoints: z.object({ remaining: z.number().int() }),
    tickId: z.number().int(),
  })
  .meta({ id: 'InterventionResult' });
const EsquemaLinhaDoTempo = z
  .object({
    eras: z.array(
      z.object({ era: z.number().int(), startedAtTick: z.number().int() }),
    ),
    checkpoints: z.array(
      z.object({
        checkpointId: z.string(),
        tick: z.number().int(),
        era: z.number().int(),
      }),
    ),
  })
  .meta({ id: 'Timeline' });
const EsquemaSerie = z
  .object({
    metric: z.string(),
    points: z.array(z.object({ tick: z.number().int(), value: z.number() })),
  })
  .meta({ id: 'Series' });
const EsquemaEventos = z
  .object({
    events: z.array(
      z.object({
        eventId: z.string(),
        kind: z.string(),
        tick: z.number().int(),
        status: z.string(),
        options: z.array(z.string()),
      }),
    ),
  })
  .meta({ id: 'PlanetEvents' });
export const EsquemaResposta = z
  .object({
    eventId: z.string().min(1).max(64),
    choice: z.string().min(1).max(40),
  })
  .strict()
  .meta({ id: 'RespondEventRequest' });
export const EsquemaSync = z
  .object({
    actions: z
      .array(
        z.object({
          idempotencyKey: z.string().min(8).max(100),
          type: z.enum(['intervention', 'checkpoint', 'tick']),
          payload: z.record(z.string(), z.unknown()).default({}),
          clientTimestamp: z.iso.datetime({ offset: true }),
        }),
      )
      .min(1)
      .max(100),
  })
  .strict()
  .meta({ id: 'SyncRequest' });
const EsquemaResultadoSync = z
  .object({
    results: z.array(
      z.object({
        idempotencyKey: z.string(),
        status: z.enum(['applied', 'duplicate', 'rejected']),
        result: z.unknown().optional(),
        error: z.string().optional(),
      }),
    ),
  })
  .meta({ id: 'SyncResult' });

const ConsultaSerie = z.object({
  metric: z.string().regex(/^[a-zA-Z_]{1,40}$/),
});
const idempotencia = {
  'Idempotency-Key':
    'Opcional. Reenvio com a mesma chave não duplica a intervenção.',
};

export const ContratosPlanetas = {
  criar: definirEndpoint({
    operationId: 'createPlanet',
    metodo: 'POST',
    caminho: '/planets',
    tag: 'planets',
    resumo: 'Cria planeta (RF-011) — exige consentimento do responsável',
    seguranca: 'bearer',
    corpo: EsquemaNovoPlaneta,
    sucesso: 201,
    respostas: {
      201: { descricao: 'Planeta criado', esquema: EsquemaPlanetaCriado },
      403: {
        descricao: 'Sem consentimento (consent-required) ou sem permissão',
      },
      503: { descricao: 'Serviço de simulação indisponível' },
    },
  }),
  obter: definirEndpoint({
    operationId: 'getPlanet',
    metodo: 'GET',
    caminho: '/planets/{id}',
    tag: 'planets',
    resumo: 'Estado atual',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Estado', esquema: EsquemaPlaneta },
      404: { descricao: 'Não encontrado (ou não é seu)' },
    },
  }),
  validar: definirEndpoint({
    operationId: 'validatePlanetParams',
    metodo: 'POST',
    caminho: '/planets/{id}/validate',
    tag: 'planets',
    resumo: 'Valida parâmetros (RF-012)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaValidar,
    sucesso: 200,
    respostas: { 200: { descricao: 'Resultado', esquema: EsquemaValidacao } },
  }),
  tick: definirEndpoint({
    operationId: 'tickPlanet',
    metodo: 'POST',
    caminho: '/planets/{id}/tick',
    tag: 'planets',
    resumo:
      'Avança o tempo (RF-013). Passos acima do limite viram job assíncrono (202).',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaTick,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Delta síncrono', esquema: EsquemaTickSincrono },
      202: { descricao: 'Job aceito', esquema: EsquemaTickAssincrono },
    },
  }),
  intervir: definirEndpoint({
    operationId: 'applyIntervention',
    metodo: 'POST',
    caminho: '/planets/{id}/interventions',
    tag: 'planets',
    resumo: 'Aplica intervenção/trade-off (RF-017/018)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaIntervencao,
    sucesso: 200,
    cabecalhosDeEntrada: idempotencia,
    respostas: {
      200: { descricao: 'Efeito', esquema: EsquemaResultadoIntervencao },
      409: { descricao: 'Pontos de ação insuficientes' },
      404: { descricao: 'Planeta não encontrado' },
    },
  }),
  linha: definirEndpoint({
    operationId: 'getTimeline',
    metodo: 'GET',
    caminho: '/planets/{id}/timeline',
    tag: 'planets',
    resumo: 'Linha do tempo e checkpoints (RF-015/016)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Linha do tempo', esquema: EsquemaLinhaDoTempo },
    },
  }),
  checkpoint: definirEndpoint({
    operationId: 'saveCheckpoint',
    metodo: 'POST',
    caminho: '/planets/{id}/checkpoints',
    tag: 'planets',
    resumo: 'Salva checkpoint (RF-015)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 201,
    respostas: {
      201: {
        descricao: 'Salvo',
        esquema: z
          .object({ checkpointId: z.string() })
          .meta({ id: 'Checkpoint' }),
      },
    },
  }),
  series: definirEndpoint({
    operationId: 'getSeries',
    metodo: 'GET',
    caminho: '/planets/{id}/series',
    tag: 'planets',
    resumo: 'Séries temporais (RF-021)',
    seguranca: 'bearer',
    parametros: ParametroId,
    consulta: ConsultaSerie,
    sucesso: 200,
    respostas: { 200: { descricao: 'Série', esquema: EsquemaSerie } },
  }),
  eventos: definirEndpoint({
    operationId: 'listPlanetEvents',
    metodo: 'GET',
    caminho: '/planets/{id}/events',
    tag: 'planets',
    resumo: 'Histórico de eventos',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Eventos', esquema: EsquemaEventos } },
  }),
  responder: definirEndpoint({
    operationId: 'respondPlanetEvent',
    metodo: 'POST',
    caminho: '/planets/{id}/events/respond',
    tag: 'planets',
    resumo: 'Responde a evento em curso',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaResposta,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Resultado',
        esquema: z
          .object({ outcome: z.string(), delta: Delta })
          .meta({ id: 'EventOutcome' }),
      },
      404: { descricao: 'Evento não encontrado' },
    },
  }),
  sync: definirEndpoint({
    operationId: 'syncOfflineActions',
    metodo: 'POST',
    caminho: '/planets/{id}/sync',
    tag: 'planets',
    resumo: 'Sincroniza ações feitas offline (RNF-021) — idempotente por ação',
    descricao:
      'Ponto de entrada reservado. O formato definitivo depende do contrato com o serviço de simulação.',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaSync,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Resultado por ação', esquema: EsquemaResultadoSync },
    },
  }),
};

export const EsquemaExplicar = z
  .object({
    planetId: Uuid,
    contextRef: z
      .string()
      .regex(/^[A-Za-z0-9:_./-]{1,200}$/)
      .describe(
        'Identificador do contexto (ex.: indicador co2); texto livre não é aceito',
      ),
    question: z.string().max(1000).optional(),
  })
  .strict()
  .meta({ id: 'ExplainRequest' });
export const EsquemaDica = z
  .object({ planetId: Uuid, missionId: Uuid })
  .strict()
  .meta({ id: 'HintRequest' });
export const EsquemaConselheiro = z
  .object({
    role: z.enum(['scientist', 'economist', 'ecologist', 'citizen']),
    query: z.string().min(1).max(1000),
  })
  .strict()
  .meta({ id: 'AdvisorRequest' });

export const ContratosIA = {
  explicar: definirEndpoint({
    operationId: 'explain',
    metodo: 'POST',
    caminho: '/ai/explain',
    tag: 'ai',
    resumo: 'Explicação causal em fluxo SSE (RF-033/039)',
    descricao:
      'Cada evento SSE `data` é JSON {"text": "..."}; termina com `event: end`.',
    seguranca: 'bearer',
    corpo: EsquemaExplicar,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Fluxo de texto', tipoConteudo: 'text/event-stream' },
    },
  }),
  dica: definirEndpoint({
    operationId: 'hint',
    metodo: 'POST',
    caminho: '/ai/hint',
    tag: 'ai',
    resumo: 'Dica personalizada (RF-035)',
    seguranca: 'bearer',
    corpo: EsquemaDica,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Dica',
        esquema: z
          .object({ hint: z.string(), level: z.number().int() })
          .meta({ id: 'Hint' }),
      },
    },
  }),
  conselheiro: definirEndpoint({
    operationId: 'advisor',
    metodo: 'POST',
    caminho: '/ai/advisor',
    tag: 'ai',
    resumo: 'Conselheiro-agente (RF-036)',
    seguranca: 'bearer',
    corpo: EsquemaConselheiro,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Conselho',
        esquema: z.object({ advice: z.string() }).meta({ id: 'Advice' }),
      },
    },
  }),
  adaptacao: definirEndpoint({
    operationId: 'adaptation',
    metodo: 'GET',
    caminho: '/ai/adaptation/{studentId}',
    tag: 'ai',
    resumo: 'Parâmetros adaptativos (equipe da escola)',
    seguranca: 'bearer',
    parametros: z.object({ studentId: Uuid }),
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Parâmetros',
        esquema: z
          .object({ difficulty: z.string(), unlocks: z.array(z.string()) })
          .meta({ id: 'Adaptation' }),
      },
      404: { descricao: 'Aluno não encontrado' },
    },
  }),
};
