import { z } from 'zod';

import { definirEndpoint } from '../../../shared/http/contrato';
import {
  ConsultaPaginada,
  DataHora,
  Pagina,
  ParametroId,
  Uuid,
} from '../../../shared/http/esquemas-comuns';
import { EnvelopeConsumido } from '../domain/eventos';

const Competencia = z.object({
  code: z.string(),
  name: z.string(),
  probability: z.number(),
  uncertainty: z.number().nullable(),
  evidenceCount: z.number().int(),
  updatedAt: DataHora,
  synthetic: z.boolean().describe('true = dado sintético do adaptador falso'),
  lastEventId: z.string().nullable(),
  evidenceRef: z.string(),
});
const Perfil = z
  .object({
    studentId: Uuid,
    competencies: z.array(Competencia),
    disclaimer: z.string(),
  })
  .meta({ id: 'CognitiveProfile' });
const Evidencia = z
  .object({
    id: Uuid,
    eventId: z.string().nullable(),
    competencyCode: z.string().nullable(),
    bnccCode: z.string().nullable(),
    type: z.string(),
    payload: z.record(z.string(), z.unknown()),
    planetId: Uuid.nullable(),
    occurredAt: DataHora,
    synthetic: z.boolean(),
    source: z.string(),
  })
  .meta({ id: 'Evidence' });
const Bncc = z
  .object({
    studentId: Uuid,
    skills: z.array(
      z.object({
        code: z.string(),
        theme: z.string().nullable(),
        component: z.string().nullable(),
        validationStatus: z.string(),
        competencyCode: z.string(),
        mastery: z.number().nullable(),
        uncertainty: z.number().nullable(),
        evidenceCount: z.number().int(),
      }),
    ),
  })
  .meta({ id: 'BnccMastery' });
const Visao = z
  .object({
    classId: Uuid,
    students: z.array(
      z.object({
        id: Uuid,
        name: z.string(),
        consentPending: z.array(z.string()),
        planets: z.number().int(),
        evidenceCount: z.number().int().nullable(),
        lastActivity: DataHora.nullable(),
      }),
    ),
    totals: z.object({
      students: z.number().int(),
      consentPending: z.number().int(),
      withAssessmentConsent: z.number().int(),
    }),
  })
  .meta({ id: 'ClassOverview' });
const CompetenciasDaTurma = z
  .object({
    classId: Uuid,
    studentsIncluded: z.number().int(),
    studentsExcludedForConsent: z.number().int(),
    synthetic: z.boolean(),
    competencies: z.array(
      z.object({
        code: z.string(),
        name: z.string(),
        students: z.number().int(),
        avgMastery: z.number().nullable(),
        distribution: z.object({
          low: z.number().int(),
          medium: z.number().int(),
          high: z.number().int(),
        }),
      }),
    ),
  })
  .meta({ id: 'ClassCompetencies' });
const Alertas = z
  .object({
    classId: Uuid,
    thresholds: z.object({
      limiarDeDominio: z.number(),
      incertezaMaxima: z.number(),
      minimoDeEvidencias: z.number().int(),
      diasDeInatividade: z.number().int(),
      situacaoDaRevisao: z.string(),
      reviewStatus: z.string(),
    }),
    alerts: z.array(
      z.object({
        studentId: Uuid,
        kind: z.enum(['low_mastery', 'inactivity']),
        competencyCode: z.string().nullable(),
        probability: z.number().nullable(),
        uncertainty: z.number().nullable(),
        evidenceCount: z.number().int(),
        reason: z.string(),
        evidenceRef: z.string().nullable(),
      }),
    ),
    notice: z.string(),
  })
  .meta({ id: 'ClassAlerts' });
const ConsentimentosDaTurma = z
  .object({
    classId: Uuid,
    students: z.array(
      z.object({
        id: Uuid,
        name: z.string(),
        isMinor: z.boolean(),
        purposes: z.array(
          z.object({ purpose: z.string(), status: z.string() }),
        ),
      }),
    ),
  })
  .meta({ id: 'ClassConsents' });
const Agregado = z
  .object({
    schoolId: Uuid,
    rows: z.array(
      z.object({
        classId: Uuid,
        className: z.string(),
        competencyCode: z.string(),
        students: z.number().int(),
        avgMastery: z.number(),
      }),
    ),
  })
  .meta({ id: 'SchoolCompetencies' });
export const EsquemaConfigAlerta = z
  .object({
    limiarDeDominio: z.number().min(0).max(1),
    incertezaMaxima: z.number().min(0).max(1),
    minimoDeEvidencias: z.number().int().min(0).max(1000),
    diasDeInatividade: z.number().int().min(1).max(365),
  })
  .strict()
  .meta({ id: 'AlertConfigRequest' });
const ConfigAlerta = EsquemaConfigAlerta.extend({
  situacaoDaRevisao: z.string(),
}).meta({ id: 'AlertConfig' });
export const EsquemaFeedback = z
  .object({
    content: z.string().trim().min(1).max(4000),
    assessmentId: Uuid.optional(),
  })
  .strict()
  .meta({ id: 'FeedbackRequest' });
const FeedbackCriado = z
  .object({ id: Uuid, studentId: Uuid, createdAt: DataHora })
  .meta({ id: 'FeedbackCreated' });
const MeusFeedbacks = z
  .object({
    items: z.array(
      z.object({
        id: Uuid,
        content: z.string(),
        authorUserId: Uuid.nullable(),
        createdAt: DataHora,
        readAt: DataHora.nullable(),
      }),
    ),
  })
  .meta({ id: 'MyFeedback' });
export const EsquemaNovaAvaliacao = z
  .object({
    kind: z.enum(['pre_test', 'post_test', 'rubric']),
    score: z.number().min(0).max(100),
    competencyCode: z.string().max(64).optional(),
    missionId: Uuid.optional(),
    details: z.record(z.string(), z.unknown()).optional(),
  })
  .strict()
  .meta({ id: 'RecordAssessmentRequest' });
const Avaliacao = z
  .object({
    id: Uuid,
    kind: z.string(),
    score: z.number().nullable(),
    competencyCode: z.string().nullable(),
    missionId: Uuid.nullable(),
    createdAt: DataHora,
  })
  .meta({ id: 'Assessment' });
const Exportacao = z
  .object({
    exportId: Uuid,
    format: z.string(),
    url: z.string(),
    expiresAt: DataHora,
    sizeBytes: z.number().int(),
  })
  .meta({ id: 'ExportLink' });
const Dataset = Exportacao.extend({
  anonymization: z.object({
    k: z.number().int(),
    suppressedGroups: z.number().int(),
    suppressedRows: z.number().int(),
    rows: z.number().int(),
    technique: z.string(),
  }),
}).meta({ id: 'ResearchDataset' });
const Aceito = z
  .object({ accepted: z.boolean(), outcome: z.string() })
  .meta({ id: 'EventAccepted' });

const ParamAluno = z.object({ id: Uuid });

export const ContratosAvaliacao = {
  eventos: definirEndpoint({
    operationId: 'ingestAssessmentEvent',
    metodo: 'POST',
    caminho: '/assessment/events',
    tag: 'assessment',
    resumo: 'Ingesta de evidência/competência pelo serviço de IA (RF-071)',
    descricao:
      'Alternativa síncrona ao Redis Streams. Gate de consentimento aplicado.',
    seguranca: 'servico',
    corpo: EnvelopeConsumido.meta({ id: 'AssessmentEventEnvelope' }),
    sucesso: 202,
    respostas: {
      202: {
        descricao:
          'Aceito (processado, duplicado ou descartado por falta de consentimento)',
        esquema: Aceito,
      },
    },
  }),
  perfil: definirEndpoint({
    operationId: 'getCognitiveProfile',
    metodo: 'GET',
    caminho: '/assessment/students/{id}/profile',
    tag: 'assessment',
    resumo: 'Perfil por competência (RF-072/073) — só equipe da escola',
    seguranca: 'bearer',
    parametros: ParamAluno,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Perfil', esquema: Perfil },
      404: { descricao: 'Não encontrado' },
    },
  }),
  evidencias: definirEndpoint({
    operationId: 'listEvidence',
    metodo: 'GET',
    caminho: '/assessment/students/{id}/evidence',
    tag: 'assessment',
    resumo: 'Evidências rastreáveis (RF-076)',
    seguranca: 'bearer',
    parametros: ParamAluno,
    consulta: ConsultaPaginada.extend({
      competency: z.string().max(64).optional(),
    }),
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Evidências',
        esquema: Pagina(Evidencia, 'EvidencePage'),
      },
    },
  }),
  bncc: definirEndpoint({
    operationId: 'getBnccMastery',
    metodo: 'GET',
    caminho: '/assessment/students/{id}/bncc',
    tag: 'assessment',
    resumo: 'Domínio mapeado à BNCC',
    seguranca: 'bearer',
    parametros: ParamAluno,
    sucesso: 200,
    respostas: { 200: { descricao: 'Mapa', esquema: Bncc } },
  }),
  registrar: definirEndpoint({
    operationId: 'recordAssessment',
    metodo: 'POST',
    caminho: '/assessment/students/{id}/assessments',
    tag: 'assessment',
    resumo: 'Registra pré/pós-teste ou rubrica (RF-074/075)',
    seguranca: 'bearer',
    parametros: ParamAluno,
    corpo: EsquemaNovaAvaliacao,
    sucesso: 201,
    respostas: { 201: { descricao: 'Registrado', esquema: Avaliacao } },
  }),
  avaliacoes: definirEndpoint({
    operationId: 'listAssessments',
    metodo: 'GET',
    caminho: '/assessment/students/{id}/assessments',
    tag: 'assessment',
    resumo: 'Pré/pós-testes e rubricas do aluno',
    seguranca: 'bearer',
    parametros: ParamAluno,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Lista',
        esquema: z
          .object({ items: z.array(Avaliacao) })
          .meta({ id: 'AssessmentList' }),
      },
    },
  }),
  visao: definirEndpoint({
    operationId: 'classOverview',
    metodo: 'GET',
    caminho: '/dashboard/classes/{id}/overview',
    tag: 'dashboard',
    resumo: 'Visão da turma (RF-063)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Visão', esquema: Visao } },
  }),
  competencias: definirEndpoint({
    operationId: 'classCompetencies',
    metodo: 'GET',
    caminho: '/dashboard/classes/{id}/competencies',
    tag: 'dashboard',
    resumo: 'Progresso por competência',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Competências', esquema: CompetenciasDaTurma },
    },
  }),
  alertas: definirEndpoint({
    operationId: 'classAlerts',
    metodo: 'GET',
    caminho: '/dashboard/classes/{id}/alerts',
    tag: 'dashboard',
    resumo: 'Alertas de dificuldade (RF-077)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Alertas', esquema: Alertas } },
  }),
  consentimentos: definirEndpoint({
    operationId: 'classConsents',
    metodo: 'GET',
    caminho: '/dashboard/classes/{id}/consents',
    tag: 'dashboard',
    resumo: 'Status de consentimento da turma (RF-068)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Status', esquema: ConsentimentosDaTurma } },
  }),
  escola: definirEndpoint({
    operationId: 'schoolCompetencies',
    metodo: 'GET',
    caminho: '/dashboard/schools/{id}/competencies',
    tag: 'dashboard',
    resumo: 'Agregado por competência entre turmas (US-09)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Agregado', esquema: Agregado } },
  }),
  lerConfig: definirEndpoint({
    operationId: 'getAlertConfig',
    metodo: 'GET',
    caminho: '/dashboard/schools/{id}/alert-config',
    tag: 'dashboard',
    resumo: 'Limiares de alerta (placeholder pedagógico)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: { 200: { descricao: 'Configuração', esquema: ConfigAlerta } },
  }),
  definirConfig: definirEndpoint({
    operationId: 'setAlertConfig',
    metodo: 'PUT',
    caminho: '/dashboard/schools/{id}/alert-config',
    tag: 'dashboard',
    resumo: 'Define limiares de alerta',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaConfigAlerta,
    sucesso: 200,
    respostas: { 200: { descricao: 'Salvo', esquema: ConfigAlerta } },
  }),
  feedback: definirEndpoint({
    operationId: 'sendFeedback',
    metodo: 'POST',
    caminho: '/dashboard/students/{id}/feedback',
    tag: 'dashboard',
    resumo: 'Professor envia feedback ao aluno (RF-067)',
    seguranca: 'bearer',
    parametros: ParamAluno,
    corpo: EsquemaFeedback,
    sucesso: 201,
    respostas: { 201: { descricao: 'Enviado', esquema: FeedbackCriado } },
  }),
  meusFeedbacks: definirEndpoint({
    operationId: 'myFeedback',
    metodo: 'GET',
    caminho: '/feedback/me',
    tag: 'dashboard',
    resumo: 'Aluno vê o feedback recebido (sem notas)',
    seguranca: 'bearer',
    sucesso: 200,
    respostas: { 200: { descricao: 'Feedback', esquema: MeusFeedbacks } },
  }),
  lido: definirEndpoint({
    operationId: 'markFeedbackRead',
    metodo: 'POST',
    caminho: '/feedback/{id}/read',
    tag: 'dashboard',
    resumo: 'Marca feedback como lido',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 204,
    respostas: { 204: { descricao: 'Marcado' } },
  }),
  exportar: definirEndpoint({
    operationId: 'exportReport',
    metodo: 'GET',
    caminho: '/dashboard/reports/export',
    tag: 'dashboard',
    resumo:
      'Exporta relatório da turma em PDF/CSV (RF-066) — devolve URL assinada de curta duração',
    seguranca: 'bearer',
    consulta: z.object({ format: z.enum(['pdf', 'csv']), classId: Uuid }),
    sucesso: 200,
    respostas: { 200: { descricao: 'Link', esquema: Exportacao } },
  }),
  dataset: definirEndpoint({
    operationId: 'researchDataset',
    metodo: 'GET',
    caminho: '/research/dataset',
    tag: 'research',
    resumo: 'Dataset anonimizado para pesquisa (RF-078)',
    seguranca: 'bearer',
    consulta: z.object({
      anonymized: z.enum(['true', 'false']).transform((v) => v === 'true'),
      format: z.enum(['json', 'csv']).default('json'),
    }),
    sucesso: 200,
    respostas: {
      200: { descricao: 'Link do dataset', esquema: Dataset },
      422: { descricao: 'anonymized=false não é permitido' },
    },
  }),
};

const Politica = z
  .object({
    dataCategory: z.string(),
    retentionDays: z.number().int(),
    action: z.string(),
    reviewStatus: z.string(),
    updatedAt: DataHora,
  })
  .meta({ id: 'RetentionPolicy' });
export const EsquemaPolitica = z
  .object({ retentionDays: z.number().int().min(1).max(36500) })
  .strict()
  .meta({ id: 'RetentionPolicyRequest' });

export const ContratosLgpd = {
  acesso: definirEndpoint({
    operationId: 'dataSubjectAccess',
    metodo: 'GET',
    caminho: '/users/{id}/data-export',
    tag: 'lgpd',
    resumo: 'Direito de acesso: todos os dados pessoais do titular (RNF-012)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Dados do titular',
        esquema: z
          .record(z.string(), z.unknown())
          .meta({ id: 'DataSubjectExport' }),
      },
      404: { descricao: 'Não encontrado' },
    },
  }),
  exclusao: definirEndpoint({
    operationId: 'dataSubjectDeletion',
    metodo: 'POST',
    caminho: '/users/{id}/deletion',
    tag: 'lgpd',
    resumo: 'Direito de exclusão: apaga dados e pseudonimiza a conta',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Concluído',
        esquema: z
          .object({
            requestId: Uuid,
            status: z.string(),
            removed: z.record(z.string(), z.number()),
          })
          .meta({ id: 'DeletionResult' }),
      },
    },
  }),
  politicas: definirEndpoint({
    operationId: 'listRetentionPolicies',
    metodo: 'GET',
    caminho: '/admin/retention/policies',
    tag: 'lgpd',
    resumo: 'Política de retenção (prazos placeholder do DPO)',
    seguranca: 'bearer',
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Políticas',
        esquema: z
          .object({ items: z.array(Politica) })
          .meta({ id: 'RetentionPolicyList' }),
      },
    },
  }),
  definirPolitica: definirEndpoint({
    operationId: 'setRetentionPolicy',
    metodo: 'PUT',
    caminho: '/admin/retention/policies/{category}',
    tag: 'lgpd',
    resumo: 'Ajusta prazo de retenção (sem novo deploy)',
    seguranca: 'bearer',
    parametros: z.object({ category: z.string().regex(/^[a-z_]{3,64}$/) }),
    corpo: EsquemaPolitica,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Ajustada', esquema: Politica },
      404: { descricao: 'Categoria inexistente' },
    },
  }),
  executar: definirEndpoint({
    operationId: 'runRetention',
    metodo: 'POST',
    caminho: '/admin/retention/run',
    tag: 'lgpd',
    resumo: 'Executa o expurgo agora',
    seguranca: 'bearer',
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Contagem por categoria',
        esquema: z
          .record(z.string(), z.number())
          .meta({ id: 'RetentionRunResult' }),
      },
    },
  }),
};
