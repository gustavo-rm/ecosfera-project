import {
  applyDecorators,
  HttpCode,
  RequestMapping,
  RequestMethod,
  SetMetadata,
} from '@nestjs/common';
import type { z } from 'zod';

/**
 * Contrato de uma rota HTTP, declarado em código.
 * É a fonte do OpenAPI 3.1 congelado em packages/api-contracts
 * (scripts/gerar-openapi.ts) e da validação de borda (InterceptadorDeValidacao).
 */
export type MetodoHttp = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type Seguranca = 'publico' | 'bearer' | 'servico';

export interface RespostaDeclarada {
  descricao: string;
  esquema?: z.ZodType;
  /** Padrão: application/json. */
  tipoConteudo?: string;
  cabecalhos?: Record<string, string>;
}

export interface DefinicaoDeEndpoint {
  operationId: string;
  metodo: MetodoHttp;
  /** Caminho relativo ao prefixo /platform/api/v1, com parâmetros no estilo OpenAPI: /planets/{id} */
  caminho: string;
  tag: string;
  resumo: string;
  descricao?: string;
  seguranca: Seguranca;
  parametros?: z.ZodObject;
  consulta?: z.ZodObject;
  corpo?: z.ZodType;
  /** Status de sucesso padrão (o primeiro de `respostas` com 2xx, se omitido). */
  sucesso: number;
  respostas: Record<number, RespostaDeclarada>;
  /** Cabeçalhos aceitos (documentação). */
  cabecalhosDeEntrada?: Record<string, string>;
  /** Rota exclusiva de ambiente de desenvolvimento/teste (não entra no contrato). */
  interna?: boolean;
}

export const META_CONTRATO = 'ecosfera:contrato';
export const PREFIXO_API = 'platform/api/v1';

export function definirEndpoint<T extends DefinicaoDeEndpoint>(d: T): T {
  return d;
}

export function caminhoNest(caminhoOpenApi: string): string {
  return caminhoOpenApi.replace(/\{(\w+)\}/g, ':$1');
}

const METODOS: Record<MetodoHttp, RequestMethod> = {
  GET: RequestMethod.GET,
  POST: RequestMethod.POST,
  PUT: RequestMethod.PUT,
  PATCH: RequestMethod.PATCH,
  DELETE: RequestMethod.DELETE,
};

/** Liga a rota do Nest ao contrato: método, caminho, status e metadado. */
export function Endpoint(d: DefinicaoDeEndpoint): MethodDecorator {
  return applyDecorators(
    RequestMapping({ path: caminhoNest(d.caminho), method: METODOS[d.metodo] }),
    HttpCode(d.sucesso),
    SetMetadata(META_CONTRATO, d),
  );
}
