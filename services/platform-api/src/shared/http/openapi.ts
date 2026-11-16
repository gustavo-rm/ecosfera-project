import { z } from 'zod';

import type { DeclaracaoDeAutorizacao } from '../autorizacao/autorizacao.decorator';
import { EsquemaProblema } from './problemas';
import { rotasDeclaradas } from './catalogo-de-rotas';
import type { DefinicaoDeEndpoint } from './contrato';

type Json = Record<string, unknown>;

/** Converte um schema Zod em JSON Schema 2020-12, movendo $defs para components/schemas. */
function converter(schema: z.ZodType, io: 'input' | 'output', componentes: Record<string, Json>): Json {
  const js = z.toJSONSchema(schema, { io, unrepresentable: 'any', target: 'draft-2020-12' }) as Json;
  const defs = (js.$defs ?? {}) as Record<string, Json>;
  delete js.$defs;
  delete js.$schema;
  const reescrever = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(reescrever);
    if (v && typeof v === 'object') {
      const o: Json = {};
      for (const [k, x] of Object.entries(v as Json)) {
        if (k === '$ref' && typeof x === 'string') o[k] = x.replace('#/$defs/', '#/components/schemas/');
        else if (k === 'id' && typeof x === 'string' && (v as Json).type !== undefined) continue;
        else o[k] = reescrever(x);
      }
      return o;
    }
    return v;
  };
  for (const [id, d] of Object.entries(defs)) componentes[id] ??= reescrever(d) as Json;
  const raiz = reescrever(js) as Json;
  const id = z.globalRegistry.get(schema)?.id;
  if (typeof id === 'string') {
    componentes[id] ??= raiz;
    return { $ref: `#/components/schemas/${id}` };
  }
  return raiz;
}

const PROBLEMA = { $ref: '#/components/schemas/Problem' };
const respostaProblema = (descricao: string) => ({ description: descricao, content: { 'application/problem+json': { schema: PROBLEMA } } });

function extensaoDeAutorizacao(a: DeclaracaoDeAutorizacao | undefined): Json {
  if (!a) return { deny: true };
  if ('publico' in a) return { public: true, reason: a.motivo };
  if ('servico' in a) return { service: true, services: a.servicos ?? 'allowed list (SERVICE_ALLOWED_NAMES)' };
  return { roles: a.papeis, ...(a.posse ? { ownership: a.posse.regra, ownershipParam: `${a.posse.origem ?? 'params'}.${a.posse.parametro ?? 'id'}` } : {}), ...(a.consentimento ? { consentWhenActorIsMinor: a.consentimento } : {}) };
}

function operacao(d: DefinicaoDeEndpoint, a: DeclaracaoDeAutorizacao | undefined, componentes: Record<string, Json>): Json {
  const parametros: Json[] = [];
  const adicionar = (onde: 'path' | 'query', s: z.ZodObject | undefined) => {
    if (!s) return;
    const js = converter(s, 'input', componentes) as { properties?: Record<string, Json>; required?: string[] };
    for (const [nome, sch] of Object.entries(js.properties ?? {})) {
      parametros.push({ name: nome, in: onde, required: onde === 'path' || (js.required ?? []).includes(nome), schema: sch });
    }
  };
  adicionar('path', d.parametros);
  adicionar('query', d.consulta);
  for (const [nome, desc] of Object.entries(d.cabecalhosDeEntrada ?? {})) parametros.push({ name: nome, in: 'header', required: false, description: desc, schema: { type: 'string' } });

  const respostas: Json = {};
  for (const [status, r] of Object.entries(d.respostas)) {
    const n = Number(status);
    const tipo = r.tipoConteudo ?? (n >= 400 ? 'application/problem+json' : 'application/json');
    const schema = r.esquema ? converter(r.esquema, 'output', componentes) : n >= 400 ? PROBLEMA : undefined;
    respostas[status] = {
      description: r.descricao,
      ...(schema || r.tipoConteudo ? { content: { [tipo]: schema ? { schema } : {} } } : {}),
      ...(r.cabecalhos ? { headers: Object.fromEntries(Object.entries(r.cabecalhos).map(([h, desc]) => [h, { description: desc, schema: { type: 'string' } }])) } : {}),
    };
  }
  const tem = (s: number) => respostas[String(s)] !== undefined;
  if (d.seguranca !== 'publico' && !tem(401)) respostas['401'] = respostaProblema('Não autenticado (token ausente, expirado ou revogado)');
  if (d.seguranca !== 'publico' && !tem(403)) respostas['403'] = respostaProblema('Sem permissão para esta ação');
  if ((d.corpo || d.consulta || d.parametros) && !tem(422)) respostas['422'] = respostaProblema('Dados inválidos');
  if (!tem(429)) respostas['429'] = respostaProblema('Limite de requisições excedido');
  if (!tem(500)) respostas['500'] = respostaProblema('Erro interno (com traceId)');

  return {
    operationId: d.operationId,
    tags: [d.tag],
    summary: d.resumo,
    ...(d.descricao ? { description: d.descricao } : {}),
    security: d.seguranca === 'publico' ? [] : d.seguranca === 'servico' ? [{ servico: [] }] : [{ bearer: [] }],
    ...(parametros.length ? { parameters: parametros } : {}),
    ...(d.corpo
      ? {
          requestBody: {
            required: true,
            content: {
              'application/json': { schema: converter(d.corpo, 'input', componentes) },
              ...(d.operationId === 'ltiLaunch' ? { 'application/x-www-form-urlencoded': { schema: converter(d.corpo, 'input', componentes) } } : {}),
            },
          },
        }
      : {}),
    responses: respostas,
    'x-authorization': extensaoDeAutorizacao(a),
  };
}

/** Monta o documento OpenAPI 3.1 a partir dos contratos declarados nas rotas. */
export function gerarOpenApi(versao = '1.0.0'): Json {
  const componentes: Record<string, Json> = {};
  converter(EsquemaProblema, 'output', componentes);
  const paths: Record<string, Record<string, Json>> = {};
  const rotas = rotasDeclaradas()
    .filter((r) => r.contrato && !r.contrato.interna)
    .sort((a, b) => a.contrato!.caminho.localeCompare(b.contrato!.caminho) || a.contrato!.metodo.localeCompare(b.contrato!.metodo));
  for (const r of rotas) {
    const d = r.contrato!;
    (paths[d.caminho] ??= {})[d.metodo.toLowerCase()] = operacao(d, r.autorizacao, componentes);
  }
  const ordenados = Object.fromEntries(Object.entries(componentes).sort(([a], [b]) => a.localeCompare(b)));
  return {
    openapi: '3.1.0',
    jsonSchemaDialect: 'https://json-schema.org/draft/2020-12/schema',
    info: {
      title: 'ECOSFERA platform-api',
      version: versao,
      description:
        'API da plataforma educacional ECOSFERA (identidade, educação, avaliação em modo leitura e gateway de simulação/tutor). ' +
        'Erros em RFC 7807 com traceId. A extensão x-authorization descreve, por operação, papéis, regra de posse e consentimento exigidos. ' +
        'WebSocket: GET /planets/{id}/stream (subprotocolos "ecosfera.v1" e "bearer.<jwt>"), mensagens {type: delta|event|tutor|alert, payload, tickId}.',
      license: { name: 'MIT' },
    },
    servers: [{ url: '/platform/api/v1' }],
    tags: [...new Set(rotas.map((r) => r.contrato!.tag))].sort().map((t) => ({ name: t })),
    paths,
    components: {
      schemas: ordenados,
      securitySchemes: {
        bearer: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT', description: 'Access token de vida curta emitido por /auth/login' },
        servico: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT', description: 'Credencial de serviço (typ=service), para o ai-sim-service' },
      },
    },
  };
}
