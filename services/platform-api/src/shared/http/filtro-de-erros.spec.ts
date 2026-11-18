import { HttpException, NotFoundException } from '@nestjs/common';

import {
  ErroConsentimentoAusente,
  ErroDeValidacao,
  ErroLimiteDeRequisicoes,
} from '../kernel/erros';
import { Metricas } from '../observabilidade/metricas';
import { FiltroDeErros } from './filtro-de-erros';

const filtro = new FiltroDeErros(
  { error: jest.fn() } as never,
  new Metricas(false),
);
const req = { originalUrl: '/platform/api/v1/x?token=segredo', url: '' };

describe('Filtro RFC 7807', () => {
  it('validação vira 422 com campos', () => {
    const p = filtro.paraProblema(
      new ErroDeValidacao('ruim', [{ campo: 'body.a', mensagem: 'm' }]),
      req,
    );
    expect(p).toMatchObject({
      type: '/errors/validation',
      status: 422,
      errors: [{ field: 'body.a', message: 'm' }],
    });
    expect(p.instance).toBe('/platform/api/v1/x'); // sem query string (nada de token em erro)
    expect(p.traceId).toMatch(/^[0-9a-f]{32}$/);
  });
  it('consentimento ausente vira 403 com tipo próprio', () => {
    expect(
      filtro.paraProblema(new ErroConsentimentoAusente('platform_use'), req),
    ).toMatchObject({
      type: '/errors/consent-required',
      status: 403,
      finalidade: 'platform_use',
    });
  });
  it('limite vira 429 com retryAfterSeconds', () =>
    expect(
      filtro.paraProblema(new ErroLimiteDeRequisicoes(30), req),
    ).toMatchObject({ status: 429, retryAfterSeconds: 30 }));
  it('HttpException do framework é traduzida', () => {
    expect(filtro.paraProblema(new NotFoundException(), req).type).toBe(
      '/errors/not-found',
    );
    expect(filtro.paraProblema(new HttpException('x', 413), req).type).toBe(
      '/errors/payload-too-large',
    );
  });
  it('erro desconhecido vira 500 sem vazar a mensagem interna', () => {
    const p = filtro.paraProblema(new Error('senha do banco: xyz'), req);
    expect(p.status).toBe(500);
    expect(p.detail).not.toContain('xyz');
  });
  it('JSON malformado e corpo grande demais', () => {
    expect(
      filtro.paraProblema({ type: 'entity.parse.failed' }, req).status,
    ).toBe(400);
    expect(filtro.paraProblema({ type: 'entity.too.large' }, req).status).toBe(
      413,
    );
  });
});
