import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import type { NextFunction, Request, Response } from 'express';
import { parse } from 'yaml';

/**
 * Teste de contrato: toda resposta produzida nos testes de integração é validada contra o
 * OpenAPI CONGELADO em packages/api-contracts. Status não declarado ou corpo fora do schema = violação.
 */
type Op = {
  responses: Record<string, { content?: Record<string, { schema?: unknown }> }>;
};
const ARQ = join(
  __dirname,
  '..',
  '..',
  '..',
  '..',
  'packages',
  'api-contracts',
  'openapi',
  'platform-api.v1.yaml',
);
const spec = parse(readFileSync(ARQ, 'utf8')) as {
  paths: Record<string, Record<string, Op>>;
  components: { schemas: Record<string, unknown> };
};

const ajv = new Ajv2020({
  strict: false,
  allErrors: true,
  validateFormats: true,
});
addFormats(ajv);
const reescrever = (v: unknown): unknown => {
  if (Array.isArray(v)) return v.map(reescrever);
  if (v && typeof v === 'object')
    return Object.fromEntries(
      Object.entries(v).map(([k, x]) => [
        k,
        k === '$ref' && typeof x === 'string'
          ? x.replace('#/components/schemas/', 'spec#/$defs/')
          : reescrever(x),
      ]),
    );
  return v;
};
ajv.addSchema({
  $id: 'spec',
  $defs: reescrever(spec.components.schemas) as Record<string, unknown>,
});

const rotas = Object.entries(spec.paths).map(([p, ops]) => ({
  re: new RegExp(`^/platform/api/v1${p.replace(/\{[^}]+\}/g, '[^/]+')}$`),
  ops,
}));

export const violacoes: string[] = [];
export const operacoesExercitadas = new Set<string>();

export function validar(
  metodo: string,
  caminho: string,
  status: number,
  tipo: string,
  corpo: string,
): void {
  const rota = rotas.find((r) => r.re.test(caminho));
  if (!rota) {
    if (status !== 404 && !caminho.endsWith('/files'))
      violacoes.push(
        `${metodo} ${caminho}: rota fora do contrato (status ${status})`,
      );
    return;
  }
  const op = rota.ops[metodo.toLowerCase()];
  if (!op) {
    if (status !== 404)
      violacoes.push(`${metodo} ${caminho}: método fora do contrato`);
    return;
  }
  operacoesExercitadas.add(`${metodo} ${rota.re.source}`);
  const r = op.responses[String(status)];
  if (!r) {
    violacoes.push(`${metodo} ${caminho}: status ${status} não declarado`);
    return;
  }
  const midia = Object.keys(r.content ?? {});
  if (midia.length === 0 || !tipo.includes('json') || !corpo) return;
  const esperado = midia.find((m) => tipo.startsWith(m)) ?? midia[0];
  const schema = r.content![esperado].schema;
  if (!schema) return;
  const v = ajv.compile(reescrever(schema) as object);
  if (!v(JSON.parse(corpo)))
    violacoes.push(
      `${metodo} ${caminho} → ${status}: ${ajv.errorsText(v.errors)}`,
    );
}

/** Middleware de TESTE: captura a resposta e valida no fim. */
export function middlewareDeContrato(
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  const enviar = res.send.bind(res);
  let corpo = '';
  res.send = (b?: unknown) => {
    if (typeof b === 'string') corpo = b;
    else if (Buffer.isBuffer(b)) corpo = '';
    else if (b !== undefined) corpo = JSON.stringify(b);
    return enviar(b);
  };
  res.on('finish', () => {
    try {
      validar(
        req.method,
        req.originalUrl.split('?')[0],
        res.statusCode,
        String(res.getHeader('content-type') ?? ''),
        corpo,
      );
    } catch (e) {
      violacoes.push(
        `${req.method} ${req.originalUrl}: erro ao validar (${(e as Error).message})`,
      );
    }
  });
  next();
}
