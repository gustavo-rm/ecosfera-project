import { Body, Controller, Inject, Req, Res } from '@nestjs/common';
import type { CookieOptions, Request, Response } from 'express';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { CONFIGURACAO, type Configuracao } from '../../../shared/config/configuracao';
import { Endpoint, PREFIXO_API } from '../../../shared/http/contrato';
import { UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroNaoAutenticado, ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { ServicoDeAutenticacao, type ResultadoDeLogin } from '../application/autenticacao.service';
import { REPOSITORIO_DE_USUARIOS, type RepositorioDeUsuarios } from '../domain/portas';
import { ContratosAuth } from './contratos';
import type { EsquemaEsqueci, EsquemaLogin, EsquemaRedefinir, EsquemaRefresh } from './esquemas';
import { paraPerfil } from './esquemas';

export const COOKIE_REFRESH = 'ecosfera_refresh';

/** ADR 0009: navegador recebe cookie httpOnly; app nativo pede o refresh no corpo. */
export function querRefreshNoCorpo(req: Request): boolean {
  return String(req.headers['x-refresh-transport'] ?? '').toLowerCase() === 'body';
}

@Controller()
export class AuthController {
  constructor(
    private readonly auth: ServicoDeAutenticacao,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(REPOSITORIO_DE_USUARIOS) private readonly usuarios: RepositorioDeUsuarios,
  ) {}

  private opcoesDoCookie(): CookieOptions {
    return {
      httpOnly: true,
      secure: this.config.COOKIE_SECURE,
      sameSite: 'strict',
      path: `/${PREFIXO_API}/auth`,
      maxAge: this.config.REFRESH_TOKEN_TTL_SECONDS * 1000,
    };
  }

  private entregarTokens(r: ResultadoDeLogin, req: Request, res: Response) {
    const corpo = querRefreshNoCorpo(req);
    if (!corpo) res.cookie(COOKIE_REFRESH, r.refreshToken, this.opcoesDoCookie());
    res.setHeader('Cache-Control', 'no-store');
    return {
      accessToken: r.accessToken,
      tokenType: 'Bearer' as const,
      expiresIn: r.expiresIn,
      ...(corpo ? { refreshToken: r.refreshToken } : {}),
    };
  }

  @Endpoint(ContratosAuth.login)
  @Autorizacao({ publico: true, motivo: 'login' })
  async login(@Body() b: z.infer<typeof EsquemaLogin>, @Req() req: Request, @Res({ passthrough: true }) res: Response) {
    const r = await this.auth.login(b.email, b.senha, req.ip ?? 'desconhecido');
    return { ...this.entregarTokens(r, req, res), perfil: paraPerfil(r.usuario) };
  }

  @Endpoint(ContratosAuth.refresh)
  @Autorizacao({ publico: true, motivo: 'renovação por refresh token (autenticado pelo próprio refresh)' })
  async refresh(@Body() b: z.infer<typeof EsquemaRefresh>, @Req() req: Request, @Res({ passthrough: true }) res: Response) {
    const cookies = req.cookies as Record<string, string | undefined> | undefined;
    const token = b.refreshToken ?? cookies?.[COOKIE_REFRESH];
    if (!token) throw new ErroNaoAutenticado('Refresh token ausente');
    try {
      return this.entregarTokens(await this.auth.renovar(token), req, res);
    } catch (e) {
      res.clearCookie(COOKIE_REFRESH, { ...this.opcoesDoCookie(), maxAge: undefined });
      throw e;
    }
  }

  @Endpoint(ContratosAuth.logout)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian', 'researcher', 'platform_admin'] })
  async logout(@UsuarioAtual() ator: AtorUsuario, @Res({ passthrough: true }) res: Response) {
    await this.auth.encerrar(ator);
    res.clearCookie(COOKIE_REFRESH, { ...this.opcoesDoCookie(), maxAge: undefined });
  }

  @Endpoint(ContratosAuth.eu)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian', 'researcher', 'platform_admin'] })
  async eu(@UsuarioAtual() ator: AtorUsuario) {
    const u = await this.usuarios.porId(ator.usuarioId);
    if (!u) throw new ErroNaoEncontrado('Usuário');
    return paraPerfil(u);
  }

  @Endpoint(ContratosAuth.esqueci)
  @Autorizacao({ publico: true, motivo: 'recuperação de senha (sem enumeração)' })
  async esqueci(@Body() b: z.infer<typeof EsquemaEsqueci>, @Req() req: Request) {
    await this.auth.esqueciASenha(b.email, req.ip ?? 'desconhecido');
  }

  @Endpoint(ContratosAuth.redefinir)
  @Autorizacao({ publico: true, motivo: 'redefinição com código de uso único' })
  async redefinir(@Body() b: z.infer<typeof EsquemaRedefinir>) {
    await this.auth.redefinirSenha(b.token, b.newPassword);
  }
}
