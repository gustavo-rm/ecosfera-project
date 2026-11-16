import {
  type CanActivate,
  type ExecutionContext,
  Inject,
  Injectable,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';

import type { Ator } from '../kernel/ator';
import {
  ErroAcessoNegado,
  ErroConsentimentoAusente,
  ErroNaoAutenticado,
  ErroNaoEncontrado,
} from '../kernel/erros';
import { ehUuid } from '../kernel/ids';
import { contextoAtual } from '../observabilidade/contexto';
import {
  type DeclaracaoDeAutorizacao,
  META_AUTORIZACAO,
} from './autorizacao.decorator';
import {
  GATE_DE_CONSENTIMENTO,
  type GateDeConsentimento,
  VERIFICADOR_DE_CREDENCIAIS,
  type VerificadorDeCredenciais,
} from './portas';
import { RegistroDeRegrasDePosse } from './registro-de-posse';

export function extrairBearer(
  cabecalho: string | undefined,
): string | undefined {
  if (!cabecalho) return undefined;
  const [esquema, valor] = cabecalho.split(' ');
  if (esquema?.toLowerCase() !== 'bearer' || !valor) return undefined;
  return valor.trim();
}

/**
 * Guard global. Nega por padrão:
 *  1. rota sem @Autorizacao → acesso negado (e o teste de arquitetura falha);
 *  2. autentica (Bearer de usuário ou credencial de serviço);
 *  3. papel; 4. posse (404 se o recurso não existe ou é de outra escola);
 *  5. consentimento quando o próprio ator é menor.
 */
@Injectable()
export class GuardCentral implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    @Inject(VERIFICADOR_DE_CREDENCIAIS)
    private readonly credenciais: VerificadorDeCredenciais,
    @Inject(GATE_DE_CONSENTIMENTO)
    private readonly consentimento: GateDeConsentimento,
    private readonly posse: RegistroDeRegrasDePosse,
  ) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    if (ctx.getType() !== 'http') return true;
    const decl = this.reflector.getAllAndOverride<
      DeclaracaoDeAutorizacao | undefined
    >(META_AUTORIZACAO, [ctx.getHandler(), ctx.getClass()]);
    const req = ctx.switchToHttp().getRequest<Request & { ator?: Ator }>();
    if (!decl) {
      // Negar por padrão: rota esquecida não vira vazamento.
      throw new ErroAcessoNegado('Rota sem declaração de autorização');
    }
    if ('publico' in decl) return true;

    const token = extrairBearer(req.headers.authorization);
    if (!token) throw new ErroNaoAutenticado();

    if ('servico' in decl) {
      const servico = await this.credenciais.verificarServico(token);
      if (decl.servicos && !decl.servicos.includes(servico.servico))
        throw new ErroAcessoNegado();
      this.anexar(req, servico);
      return true;
    }

    const ator = await this.credenciais.verificarAcesso(token);
    this.anexar(req, ator);
    if (!decl.papeis.includes(ator.papel)) throw new ErroAcessoNegado();

    if (decl.posse) {
      const regra = this.posse.obter(decl.posse.regra);
      if (!regra)
        throw new ErroAcessoNegado(
          `Regra de posse desconhecida: ${decl.posse.regra}`,
        );
      const origem = decl.posse.origem ?? 'params';
      const fonte = (
        origem === 'params'
          ? req.params
          : origem === 'query'
            ? req.query
            : req.body
      ) as Record<string, unknown> | undefined;
      const valor = fonte?.[decl.posse.parametro ?? 'id'];
      if (!ehUuid(valor)) throw new ErroNaoEncontrado('Recurso');
      const r = await regra(ator, valor);
      if (r === 'inexistente') throw new ErroNaoEncontrado('Recurso');
      if (r === 'negado') throw new ErroAcessoNegado();
    }

    if (decl.consentimento && ator.menor) {
      const ok = await this.consentimento.permite(
        ator.usuarioId,
        decl.consentimento,
      );
      if (!ok) throw new ErroConsentimentoAusente(decl.consentimento);
    }
    return true;
  }

  private anexar(req: Request & { ator?: Ator }, ator: Ator): void {
    req.ator = ator;
    const ctx = contextoAtual();
    if (ctx) ctx.ator = ator;
  }
}
