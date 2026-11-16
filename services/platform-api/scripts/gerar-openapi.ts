/**
 * Gera o contrato congelado em packages/api-contracts a partir das rotas declaradas.
 *   pnpm openapi:gerar      → escreve o YAML, os tipos TS e a documentação HTML
 *   pnpm openapi:verificar  → falha (exit 1) se o arquivo congelado diverge do código
 */
import 'reflect-metadata';

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { stringify } from 'yaml';

import { gerarOpenApi } from '../src/shared/http/openapi';
import { gerarAsyncApi } from '../src/shared/eventos/asyncapi';
import { gerarHtmlDaDocumentacao } from './documentacao-html';

const CONTRATOS = join(__dirname, '..', '..', '..', 'packages', 'api-contracts');
const ARQ_OPENAPI = join(CONTRATOS, 'openapi', 'platform-api.v1.yaml');
const ARQ_ASYNC = join(CONTRATOS, 'asyncapi', 'platform-events.v1.yaml');

function gerar(): { openapi: string; asyncapi: string; doc: Record<string, unknown> } {
  const doc = gerarOpenApi();
  const cabecalho = '# GERADO por services/platform-api (pnpm openapi:gerar). Não edite à mão: mude o contrato no código.\n';
  return { openapi: cabecalho + stringify(doc, { lineWidth: 0, aliasDuplicateObjects: false }), asyncapi: cabecalho + stringify(gerarAsyncApi(), { lineWidth: 0, aliasDuplicateObjects: false }), doc };
}

const { openapi, asyncapi, doc } = gerar();
if (process.argv.includes('--verificar')) {
  const atual = existsSync(ARQ_OPENAPI) ? readFileSync(ARQ_OPENAPI, 'utf8') : '';
  const atualAsync = existsSync(ARQ_ASYNC) ? readFileSync(ARQ_ASYNC, 'utf8') : '';
  if (atual !== openapi || atualAsync !== asyncapi) {
    console.error('O contrato congelado em packages/api-contracts diverge do código. Rode `pnpm openapi:gerar` e revise o diff.');
    process.exit(1);
  }
  console.log('Contrato OpenAPI/AsyncAPI em dia com o código.');
} else {
  for (const d of ['openapi', 'asyncapi', 'src/generated', 'docs']) mkdirSync(join(CONTRATOS, d), { recursive: true });
  writeFileSync(ARQ_OPENAPI, openapi);
  writeFileSync(ARQ_ASYNC, asyncapi);
  writeFileSync(join(CONTRATOS, 'docs', 'platform-api.html'), gerarHtmlDaDocumentacao(doc));
  execFileSync(join(__dirname, '..', 'node_modules', '.bin', 'openapi-typescript'), [ARQ_OPENAPI, '-o', join(CONTRATOS, 'src', 'generated', 'platform-api.ts')], { stdio: 'inherit' });
  console.log(`Escrito: ${ARQ_OPENAPI}`);
}
