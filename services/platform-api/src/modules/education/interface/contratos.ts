import { z } from 'zod';

import { definirEndpoint } from '../../../shared/http/contrato';
import { ParametroId, Uuid } from '../../../shared/http/esquemas-comuns';
import { EsquemaPerfil } from '../../identity/interface/esquemas';
import { NIVEIS } from '../domain/educacao';

export const EsquemaNivel = z.enum(NIVEIS).meta({ id: 'TrackLevel', description: 'fundamental_ii | medio | tecnico' });

export const EsquemaEscola = z.object({ id: Uuid, name: z.string() }).meta({ id: 'School' });
export const EsquemaNovaEscola = z
  .object({
    name: z.string().trim().min(2).max(200),
    admin: z.object({ name: z.string().trim().min(1).max(200), email: z.email().max(254), password: z.string().min(1).max(256).optional() }).strict(),
  })
  .strict()
  .meta({ id: 'CreateSchoolRequest' });
const EsquemaEscolaCriada = z.object({ school: EsquemaEscola, admin: EsquemaPerfil }).meta({ id: 'SchoolCreated' });

export const EsquemaTurma = z
  .object({ id: Uuid, schoolId: Uuid, teacherUserId: Uuid.nullable(), name: z.string(), year: z.number().int().nullable(), trackLevel: EsquemaNivel.nullable() })
  .meta({ id: 'Class' });
export const EsquemaNovaTurma = z
  .object({ name: z.string().trim().min(1).max(120), year: z.number().int().min(1).max(20).optional(), trackLevel: EsquemaNivel.optional(), teacherUserId: Uuid.optional() })
  .strict()
  .meta({ id: 'CreateClassRequest' });
export const EsquemaMatricula = z.object({ studentIds: z.array(Uuid).min(1).max(200) }).strict().meta({ id: 'EnrollStudentsRequest' });
const EsquemaResultadoMatricula = z.object({ enrolled: z.array(Uuid), alreadyEnrolled: z.array(Uuid) }).meta({ id: 'EnrollStudentsResult' });
export const EsquemaTrilhaDaTurma = z.object({ level: EsquemaNivel }).strict().meta({ id: 'SetTrackRequest' });
const EsquemaAlunoDaTurma = z.object({ id: Uuid, name: z.string(), isMinor: z.boolean() }).meta({ id: 'ClassStudent' });

export const EsquemaMissao = z
  .object({
    id: Uuid,
    schoolId: Uuid.nullable(),
    authorUserId: Uuid.nullable(),
    title: z.string(),
    description: z.string().nullable(),
    objective: z.string().nullable(),
    trackLevel: EsquemaNivel,
    bnccCodes: z.array(z.string()),
    parameters: z.record(z.string(), z.unknown()),
    status: z.enum(['draft', 'published', 'archived']),
    classIds: z.array(Uuid),
  })
  .meta({ id: 'Mission' });
export const EsquemaNovaMissao = z
  .object({
    title: z.string().trim().min(1).max(200),
    description: z.string().max(4000).optional(),
    objective: z.string().trim().min(1).max(2000).describe('Objetivo pedagógico'),
    trackLevel: EsquemaNivel,
    bnccCodes: z.array(z.string().trim().min(4).max(20)).min(1).max(20).describe('Habilidades BNCC (RP-001: ao menos uma)'),
    parameters: z.record(z.string(), z.unknown()).optional().describe('Parâmetros repassados ao serviço de simulação'),
    classIds: z.array(Uuid).max(50).optional().describe('Publica já para estas turmas'),
  })
  .strict()
  .meta({ id: 'CreateMissionRequest' });
export const EsquemaPublicacao = z.object({ classIds: z.array(Uuid).min(1).max(50) }).strict().meta({ id: 'PublishMissionRequest' });

const EsquemaCompetencia = z
  .object({ code: z.string(), name: z.string(), description: z.string().nullable(), generalCompetencies: z.array(z.string()), validationStatus: z.string(), catalogVersion: z.string() })
  .meta({ id: 'Competency' });
export const EsquemaHabilidade = z
  .object({
    code: z.string(),
    description: z.string(),
    component: z.string().nullable(),
    theme: z.string().nullable(),
    stage: z.string().nullable(),
    competencyCode: z.string().nullable(),
    validationStatus: z.string().describe('pending_validation = aguardando especialista (RSK-06)'),
    catalogVersion: z.string(),
    active: z.boolean(),
  })
  .meta({ id: 'BnccSkill' });
export const EsquemaRevisaoHabilidade = z
  .object({
    description: z.string().min(1).max(2000).optional(),
    component: z.string().max(100).optional(),
    theme: z.string().max(200).optional(),
    stage: z.enum(['fundamental', 'medio', 'tecnico']).optional(),
    competencyCode: z.string().max(64).optional(),
    validationStatus: z.enum(['pending_validation', 'validated', 'rejected']).optional(),
    catalogVersion: z.string().min(1).max(32).optional(),
    active: z.boolean().optional(),
  })
  .strict()
  .meta({ id: 'ReviewBnccSkillRequest' });
export const EsquemaNovaHabilidade = EsquemaRevisaoHabilidade.extend({ code: z.string().regex(/^E[FM]\d{2}[A-Z]{2,3}\d{2,3}$/), description: z.string().min(1).max(2000) }).meta({ id: 'CreateBnccSkillRequest' });

const ParametroCodigo = z.object({ code: z.string().min(4).max(20) });

export const ContratosEducacao = {
  criarEscola: definirEndpoint({
    operationId: 'createSchool', metodo: 'POST', caminho: '/schools', tag: 'schools',
    resumo: 'Cadastra escola e gera admin inicial (RF-001)', seguranca: 'bearer', corpo: EsquemaNovaEscola, sucesso: 201,
    respostas: { 201: { descricao: 'Escola criada', esquema: EsquemaEscolaCriada }, 409: { descricao: 'E-mail do admin já existe' } },
  }),
  escola: definirEndpoint({
    operationId: 'getSchool', metodo: 'GET', caminho: '/schools/{id}', tag: 'schools',
    resumo: 'Dados da escola', seguranca: 'bearer', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Escola', esquema: EsquemaEscola }, 404: { descricao: 'Não encontrada' } },
  }),
  criarTurma: definirEndpoint({
    operationId: 'createClass', metodo: 'POST', caminho: '/classes', tag: 'classes',
    resumo: 'Cria turma (RF-005)', seguranca: 'bearer', corpo: EsquemaNovaTurma, sucesso: 201,
    respostas: { 201: { descricao: 'Turma criada', esquema: EsquemaTurma }, 404: { descricao: 'Professor não encontrado' } },
  }),
  turmas: definirEndpoint({
    operationId: 'listClasses', metodo: 'GET', caminho: '/classes', tag: 'classes',
    resumo: 'Turmas visíveis ao ator (aluno vê só as suas)', seguranca: 'bearer', sucesso: 200,
    respostas: { 200: { descricao: 'Turmas', esquema: z.object({ items: z.array(EsquemaTurma) }).meta({ id: 'ClassList' }) } },
  }),
  turma: definirEndpoint({
    operationId: 'getClass', metodo: 'GET', caminho: '/classes/{id}', tag: 'classes',
    resumo: 'Dados da turma', seguranca: 'bearer', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Turma', esquema: EsquemaTurma }, 404: { descricao: 'Não encontrada' } },
  }),
  matricular: definirEndpoint({
    operationId: 'enrollStudents', metodo: 'POST', caminho: '/classes/{id}/students', tag: 'classes',
    resumo: 'Vincula alunos à turma (RF-005)', seguranca: 'bearer', parametros: ParametroId, corpo: EsquemaMatricula, sucesso: 200,
    respostas: { 200: { descricao: 'Matrículas', esquema: EsquemaResultadoMatricula }, 404: { descricao: 'Turma não encontrada' } },
  }),
  alunos: definirEndpoint({
    operationId: 'listClassStudents', metodo: 'GET', caminho: '/classes/{id}/students', tag: 'classes',
    resumo: 'Alunos da turma', seguranca: 'bearer', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Alunos', esquema: z.object({ items: z.array(EsquemaAlunoDaTurma) }).meta({ id: 'ClassStudentList' }) } },
  }),
  desmatricular: definirEndpoint({
    operationId: 'removeStudent', metodo: 'DELETE', caminho: '/classes/{id}/students/{studentId}', tag: 'classes',
    resumo: 'Remove aluno da turma', seguranca: 'bearer', parametros: z.object({ id: Uuid, studentId: Uuid }), sucesso: 204,
    respostas: { 204: { descricao: 'Removido' }, 404: { descricao: 'Não encontrado' } },
  }),
  trilha: definirEndpoint({
    operationId: 'setClassTrack', metodo: 'PATCH', caminho: '/classes/{id}/track', tag: 'classes',
    resumo: 'Define trilha EF/Médio/Técnico (RF-061)', seguranca: 'bearer', parametros: ParametroId, corpo: EsquemaTrilhaDaTurma, sucesso: 200,
    respostas: { 200: { descricao: 'Turma atualizada', esquema: EsquemaTurma } },
  }),
  trilhas: definirEndpoint({
    operationId: 'listTracks', metodo: 'GET', caminho: '/tracks', tag: 'classes',
    resumo: 'Trilhas disponíveis', seguranca: 'bearer', sucesso: 200,
    respostas: { 200: { descricao: 'Trilhas', esquema: z.object({ items: z.array(z.object({ level: EsquemaNivel, name: z.string() })) }).meta({ id: 'TrackList' }) } },
  }),
  criarMissao: definirEndpoint({
    operationId: 'createMission', metodo: 'POST', caminho: '/missions', tag: 'missions',
    resumo: 'Cria missão ancorada à BNCC (RF-062, RP-001)', seguranca: 'bearer', corpo: EsquemaNovaMissao, sucesso: 201,
    respostas: { 201: { descricao: 'Missão criada', esquema: EsquemaMissao }, 422: { descricao: 'Código BNCC inexistente ou dados inválidos' } },
  }),
  missoes: definirEndpoint({
    operationId: 'listMissions', metodo: 'GET', caminho: '/missions', tag: 'missions',
    resumo: 'Missões da turma (aluno vê só as publicadas)', seguranca: 'bearer', consulta: z.object({ classId: Uuid }), sucesso: 200,
    respostas: { 200: { descricao: 'Missões', esquema: z.object({ items: z.array(EsquemaMissao) }).meta({ id: 'MissionList' }) }, 404: { descricao: 'Turma não encontrada' } },
  }),
  missao: definirEndpoint({
    operationId: 'getMission', metodo: 'GET', caminho: '/missions/{id}', tag: 'missions',
    resumo: 'Detalhe da missão', seguranca: 'bearer', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Missão', esquema: EsquemaMissao }, 404: { descricao: 'Não encontrada' } },
  }),
  publicar: definirEndpoint({
    operationId: 'publishMission', metodo: 'POST', caminho: '/missions/{id}/publish', tag: 'missions',
    resumo: 'Publica a missão para turmas', seguranca: 'bearer', parametros: ParametroId, corpo: EsquemaPublicacao, sucesso: 200,
    respostas: { 200: { descricao: 'Publicada', esquema: EsquemaMissao }, 404: { descricao: 'Não encontrada' }, 409: { descricao: 'Missão arquivada' } },
  }),
  competencias: definirEndpoint({
    operationId: 'listCompetencies', metodo: 'GET', caminho: '/curriculum/competencies', tag: 'curriculum',
    resumo: 'Competências do modelo pedagógico', seguranca: 'bearer', sucesso: 200,
    respostas: { 200: { descricao: 'Competências', esquema: z.object({ items: z.array(EsquemaCompetencia) }).meta({ id: 'CompetencyList' }) } },
  }),
  habilidades: definirEndpoint({
    operationId: 'listBnccSkills', metodo: 'GET', caminho: '/curriculum/bncc-skills', tag: 'curriculum',
    resumo: 'Catálogo BNCC (dado versionado)', seguranca: 'bearer', sucesso: 200,
    consulta: z.object({ stage: z.enum(['fundamental', 'medio', 'tecnico']).optional(), competency: z.string().max(64).optional() }),
    respostas: { 200: { descricao: 'Habilidades', esquema: z.object({ items: z.array(EsquemaHabilidade) }).meta({ id: 'BnccSkillList' }) } },
  }),
  criarHabilidade: definirEndpoint({
    operationId: 'createBnccSkill', metodo: 'POST', caminho: '/curriculum/bncc-skills', tag: 'curriculum',
    resumo: 'Inclui habilidade no catálogo (sem novo deploy)', seguranca: 'bearer', corpo: EsquemaNovaHabilidade, sucesso: 201,
    respostas: { 201: { descricao: 'Criada', esquema: EsquemaHabilidade }, 409: { descricao: 'Já existe' } },
  }),
  revisarHabilidade: definirEndpoint({
    operationId: 'reviewBnccSkill', metodo: 'PATCH', caminho: '/curriculum/bncc-skills/{code}', tag: 'curriculum',
    resumo: 'Revisa habilidade (validação por especialista, RSK-06)', seguranca: 'bearer', parametros: ParametroCodigo, corpo: EsquemaRevisaoHabilidade, sucesso: 200,
    respostas: { 200: { descricao: 'Revisada', esquema: EsquemaHabilidade }, 404: { descricao: 'Não encontrada' } },
  }),
};
