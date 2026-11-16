import { createParamDecorator, type ExecutionContext } from '@nestjs/common';
import type { Request } from 'express';

import type { Ator, AtorServico, AtorUsuario } from '../kernel/ator';
import { ErroNaoAutenticado } from '../kernel/erros';

type ReqComAtor = Request & { ator?: Ator; consultaValidada?: unknown };

/** Query já validada pelo contrato (com coerção e defaults). */
export const Consulta = createParamDecorator(
  (_: unknown, ctx: ExecutionContext) => {
    return ctx.switchToHttp().getRequest<ReqComAtor>().consultaValidada ?? {};
  },
);

/** Usuário autenticado (garantido pelo guard central). */
export const UsuarioAtual = createParamDecorator(
  (_: unknown, ctx: ExecutionContext): AtorUsuario => {
    const ator = ctx.switchToHttp().getRequest<ReqComAtor>().ator;
    if (!ator || ator.tipo !== 'usuario') throw new ErroNaoAutenticado();
    return ator;
  },
);

/** Serviço autenticado por credencial de serviço. */
export const ServicoAtual = createParamDecorator(
  (_: unknown, ctx: ExecutionContext): AtorServico => {
    const ator = ctx.switchToHttp().getRequest<ReqComAtor>().ator;
    if (!ator || ator.tipo !== 'servico') throw new ErroNaoAutenticado();
    return ator;
  },
);
