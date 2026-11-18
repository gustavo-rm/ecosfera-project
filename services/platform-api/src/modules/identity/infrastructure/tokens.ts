import { randomBytes, randomUUID } from 'node:crypto';

import { errors, jwtVerify, SignJWT } from 'jose';

import type { VerificadorDeCredenciais } from '../../../shared/autorizacao/portas';
import type { Configuracao } from '../../../shared/config/configuracao';
import type { AtorServico, AtorUsuario } from '../../../shared/kernel/ator';
import { ErroNaoAutenticado } from '../../../shared/kernel/erros';
import { ehPapel } from '../../../shared/kernel/papeis';
import type { Relogio } from '../../../shared/kernel/relogio';
import type { ArmazemDeSessoes } from '../domain/portas';
import type { Usuario } from '../domain/usuario';

const AUDIENCIA = 'platform-api';

/**
 * Tokens de acesso: JWT HS256 de vida curta, com `sid` (sessão). A sessão no Redis
 * é conferida a cada requisição: logout e revogação valem na hora (ADR 0009).
 * Credenciais de serviço: JWT HS256 com outro segredo e `typ=service` (ADR 0008).
 */
export class ServicoDeTokens implements VerificadorDeCredenciais {
  private readonly chaveAcesso: Uint8Array;
  private readonly chaveServico: Uint8Array;

  constructor(
    private readonly config: Configuracao,
    private readonly sessoes: ArmazemDeSessoes,
    private readonly relogio: Relogio,
  ) {
    this.chaveAcesso = new TextEncoder().encode(config.JWT_ACCESS_SECRET);
    this.chaveServico = new TextEncoder().encode(config.SERVICE_TOKEN_SECRET);
  }

  async emitirAcesso(
    u: Usuario,
    sessaoId: string,
  ): Promise<{ token: string; expiraEm: number }> {
    const agora = Math.floor(this.relogio.agora().getTime() / 1000);
    const exp = agora + this.config.ACCESS_TOKEN_TTL_SECONDS;
    const token = await new SignJWT({
      typ: 'access',
      role: u.papel,
      sch: u.escolaId,
      min: u.menor,
      sid: sessaoId,
    })
      .setProtectedHeader({ alg: 'HS256', typ: 'JWT' })
      .setSubject(u.id)
      .setIssuer(this.config.JWT_ISSUER)
      .setAudience(AUDIENCIA)
      .setIssuedAt(agora)
      .setExpirationTime(exp)
      .setJti(randomUUID())
      .sign(this.chaveAcesso);
    return { token, expiraEm: this.config.ACCESS_TOKEN_TTL_SECONDS };
  }

  novoSegredoDeRefresh(): string {
    return randomBytes(32).toString('base64url');
  }

  async verificarAcesso(token: string): Promise<AtorUsuario> {
    let carga: Record<string, unknown>;
    try {
      const r = await jwtVerify(token, this.chaveAcesso, {
        issuer: this.config.JWT_ISSUER,
        audience: AUDIENCIA,
        algorithms: ['HS256'],
        currentDate: this.relogio.agora(),
      });
      carga = r.payload;
    } catch (e) {
      if (e instanceof errors.JWTExpired)
        throw new ErroNaoAutenticado('Token expirado');
      throw new ErroNaoAutenticado('Token inválido');
    }
    const { sub, role, sch, min, sid, typ } = carga;
    if (
      typ !== 'access' ||
      typeof sub !== 'string' ||
      !ehPapel(role) ||
      typeof sid !== 'string'
    ) {
      throw new ErroNaoAutenticado('Token inválido');
    }
    if (!(await this.sessoes.existe(sid)))
      throw new ErroNaoAutenticado('Sessão encerrada ou revogada');
    return {
      tipo: 'usuario',
      usuarioId: sub,
      papel: role,
      escolaId: typeof sch === 'string' ? sch : null,
      menor: min === true,
      sessaoId: sid,
    };
  }

  async verificarServico(token: string): Promise<AtorServico> {
    try {
      const { payload } = await jwtVerify(token, this.chaveServico, {
        audience: AUDIENCIA,
        algorithms: ['HS256'],
        currentDate: this.relogio.agora(),
        maxTokenAge: '15m',
      });
      if (payload.typ !== 'service' || typeof payload.sub !== 'string')
        throw new Error('typ');
      if (!this.config.SERVICE_ALLOWED_NAMES.includes(payload.sub))
        throw new Error('servico');
      return { tipo: 'servico', servico: payload.sub };
    } catch {
      throw new ErroNaoAutenticado('Credencial de serviço inválida');
    }
  }

  /** Para testes e para o script de emissão de credencial de serviço. */
  static async emitirTokenDeServico(
    segredo: string,
    servico: string,
    ttlSegundos = 300,
    agora = new Date(),
  ): Promise<string> {
    const iat = Math.floor(agora.getTime() / 1000);
    return new SignJWT({ typ: 'service' })
      .setProtectedHeader({ alg: 'HS256', typ: 'JWT' })
      .setSubject(servico)
      .setIssuer(servico)
      .setAudience(AUDIENCIA)
      .setIssuedAt(iat)
      .setExpirationTime(iat + ttlSegundos)
      .sign(new TextEncoder().encode(segredo));
  }
}
