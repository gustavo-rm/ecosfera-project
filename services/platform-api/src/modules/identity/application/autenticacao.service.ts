import { randomBytes, randomUUID } from 'node:crypto';

import { Inject, Injectable } from '@nestjs/common';
import type { Redis } from 'ioredis';
import type { Logger } from 'pino';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import { carregarFatosDoAlvo } from '../../../shared/autorizacao/fatos';
import { CONFIGURACAO, type Configuracao } from '../../../shared/config/configuracao';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import {
  ErroAcessoNegado,
  ErroDeValidacao,
  ErroLimiteDeRequisicoes,
  ErroNaoAutenticado,
  ErroNaoEncontrado,
  ErroRequisicaoInvalida,
} from '../../../shared/kernel/erros';
import { decidirAcessoAoUsuario } from '../../../shared/kernel/politica-de-acesso';
import { VINCULOS_ESCOLARES, type VinculosEscolares } from '../../../shared/kernel/vinculos';
import { LOGGER } from '../../../shared/observabilidade/logger';
import { Metricas } from '../../../shared/observabilidade/metricas';
import { ChavesRedis } from '../../../shared/redis/chaves';
import { REDIS } from '../../../shared/redis/redis';
import { LimitadorDeTaxa } from '../../../shared/seguranca/limitador-de-taxa';
import { hashDeToken, Pseudonimizador } from '../../../shared/seguranca/pseudonimizador';
import { problemasDaSenha } from '../domain/politica-de-senha';
import {
  ARMAZEM_DE_SESSOES,
  type ArmazemDeSessoes,
  HASHER_DE_SENHA,
  type HasherDeSenha,
  MAILER,
  type Mailer,
  REPOSITORIO_DE_USUARIOS,
  type RepositorioDeUsuarios,
} from '../domain/portas';
import { normalizarEmail, type Usuario } from '../domain/usuario';
import { ServicoDeTokens } from '../infrastructure/tokens';

export interface ResultadoDeLogin {
  accessToken: string;
  expiresIn: number;
  refreshToken: string;
  usuario: Usuario;
}

const TTL_REDEFINICAO_SEGUNDOS = 30 * 60;
const MENSAGEM_LOGIN_INVALIDO = 'E-mail ou senha inválidos';

@Injectable()
export class ServicoDeAutenticacao {
  private iscaDeHash?: Promise<string>;

  constructor(
    @Inject(REPOSITORIO_DE_USUARIOS) private readonly usuarios: RepositorioDeUsuarios,
    @Inject(HASHER_DE_SENHA) private readonly hasher: HasherDeSenha,
    @Inject(ARMAZEM_DE_SESSOES) private readonly sessoes: ArmazemDeSessoes,
    @Inject(MAILER) private readonly mailer: Mailer,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(LOGGER) private readonly logger: Logger,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    private readonly chaves: ChavesRedis,
    private readonly tokens: ServicoDeTokens,
    private readonly limitador: LimitadorDeTaxa,
    private readonly auditoria: Auditoria,
    private readonly pseudo: Pseudonimizador,
    private readonly metricas: Metricas,
  ) {}

  /** RF-003: credencial válida concede sessão; inválida é negada E registrada. */
  async login(email: string, senha: string, ip: string): Promise<ResultadoDeLogin> {
    const emailN = normalizarEmail(email);
    const contaPseudo = this.pseudo.estavel(emailN, 'login');
    const porIp = await this.limitador.consumir('login-ip', ip, this.config.RATE_LIMIT_AUTH_IP_PER_MINUTE, 60);
    // Por conta contamos só FALHAS (não bloqueia quem acerta a senha várias vezes).
    const porConta = await this.limitador.excedido('login-falha', contaPseudo, this.config.RATE_LIMIT_LOGIN_PER_MINUTE);
    if (!porIp.permitido || !porConta.permitido) {
      await this.auditoria.registrar({
        acao: 'auth.login_rate_limited',
        entidade: 'session',
        resultado: 'denied',
        dados: { accountPseudonym: contaPseudo },
      });
      throw new ErroLimiteDeRequisicoes(Math.max(porIp.tentarEmSegundos, porConta.tentarEmSegundos));
    }

    const u = await this.usuarios.porEmail(emailN);
    // Sempre verifica um hash, para o tempo de resposta não revelar se o e-mail existe.
    const ok = u ? await this.hasher.verificar(u.senhaHash, senha) : await this.hasher.verificar(await this.isca(), senha);
    if (!u || !ok || !u.podeAutenticar()) {
      this.metricas.loginsFalhos.inc();
      await this.limitador.consumir('login-falha', contaPseudo, this.config.RATE_LIMIT_LOGIN_PER_MINUTE, 15 * 60);
      await this.auditoria.registrar({
        acao: 'auth.login_failed',
        entidade: 'session',
        entidadeId: u?.id ?? null,
        escolaId: u?.escolaId ?? null,
        resultado: 'denied',
        dados: { accountPseudonym: contaPseudo },
      });
      throw new ErroNaoAutenticado(MENSAGEM_LOGIN_INVALIDO);
    }
    await this.limitador.zerar('login-falha', contaPseudo);
    return this.abrirSessao(u);
  }

  /** Abre sessão para um usuário já autenticado (senha, OIDC ou LTI). */
  async abrirSessao(u: Usuario): Promise<ResultadoDeLogin> {
    const sessaoId = randomUUID();
    const segredo = this.tokens.novoSegredoDeRefresh();
    await this.sessoes.criar(sessaoId, u.id, segredo, this.config.REFRESH_TOKEN_TTL_SECONDS);
    const { token, expiraEm } = await this.tokens.emitirAcesso(u, sessaoId);
    return { accessToken: token, expiresIn: expiraEm, refreshToken: `${sessaoId}.${segredo}`, usuario: u };
  }

  /** Refresh rotativo. Reuso de um refresh já usado revoga a família inteira. */
  async renovar(refreshToken: string): Promise<ResultadoDeLogin> {
    const [sessaoId, segredo] = refreshToken.split('.');
    if (!sessaoId || !segredo) throw new ErroNaoAutenticado('Refresh token inválido');
    const novo = this.tokens.novoSegredoDeRefresh();
    const r = await this.sessoes.rotacionar(sessaoId, segredo, novo, this.config.REFRESH_TOKEN_TTL_SECONDS);
    if (r.tipo === 'reuso') {
      await this.auditoria.registrar({
        acao: 'auth.refresh_reuse_detected',
        entidade: 'session',
        entidadeId: sessaoId,
        resultado: 'denied',
        dados: { userId: r.usuarioId, familyRevoked: true },
      });
      throw new ErroNaoAutenticado('Refresh token reutilizado: a sessão foi encerrada por segurança');
    }
    if (r.tipo === 'invalido') throw new ErroNaoAutenticado('Refresh token inválido ou expirado');
    const u = await this.usuarios.porId(r.usuarioId);
    if (!u || !u.podeAutenticar()) {
      await this.sessoes.revogar(sessaoId);
      throw new ErroNaoAutenticado('Conta indisponível');
    }
    const { token, expiraEm } = await this.tokens.emitirAcesso(u, sessaoId);
    return { accessToken: token, expiresIn: expiraEm, refreshToken: `${sessaoId}.${novo}`, usuario: u };
  }

  async encerrar(ator: AtorUsuario): Promise<void> {
    await this.sessoes.revogar(ator.sessaoId);
  }

  /** RF-006: sempre 202, exista ou não o e-mail (sem enumeração). */
  async esqueciASenha(email: string, ip: string): Promise<void> {
    const r = await this.limitador.consumir('pwforgot-ip', ip, this.config.RATE_LIMIT_AUTH_IP_PER_MINUTE, 60);
    if (!r.permitido) throw new ErroLimiteDeRequisicoes(r.tentarEmSegundos);
    const u = await this.usuarios.porEmail(normalizarEmail(email));
    if (!u || !u.podeAutenticar()) return;
    await this.enviarLinkDeRedefinicao(u, 'forgot');
  }

  async redefinirSenha(token: string, novaSenha: string): Promise<void> {
    const chave = this.chaves.redefinicaoDeSenha(hashDeToken(token));
    const usuarioId = await this.redis.get(chave);
    if (!usuarioId) throw new ErroRequisicaoInvalida('Link de redefinição inválido ou expirado');
    const u = await this.usuarios.porId(usuarioId);
    if (!u || !u.podeAutenticar()) throw new ErroRequisicaoInvalida('Link de redefinição inválido ou expirado');
    const problemas = problemasDaSenha(novaSenha, u.email);
    if (problemas.length > 0) {
      throw new ErroDeValidacao('A nova senha não atende à política', problemas.map((m) => ({ campo: 'body.newPassword', mensagem: m })));
    }
    u.senhaHash = await this.hasher.gerar(novaSenha);
    await this.usuarios.salvar(u);
    await this.redis.del(chave);
    const revogadas = await this.sessoes.revogarTodasDoUsuario(u.id);
    await this.auditoria.registrar({
      acao: 'auth.password_reset',
      entidade: 'user',
      entidadeId: u.id,
      escolaId: u.escolaId,
      dados: { sessionsRevoked: revogadas },
    });
  }

  /** RF-006 "por admin": o admin da escola dispara o link para o usuário. */
  async iniciarRedefinicaoPeloAdmin(ator: AtorUsuario, alvoId: string): Promise<void> {
    const fatos = await carregarFatosDoAlvo(this.vinculos, ator, alvoId);
    const d = decidirAcessoAoUsuario(ator, fatos, 'gerir');
    if (d === 'inexistente') throw new ErroNaoEncontrado('Usuário');
    if (d === 'negado') throw new ErroAcessoNegado();
    const u = await this.usuarios.porId(alvoId);
    if (!u || !u.podeAutenticar()) throw new ErroNaoEncontrado('Usuário');
    await this.enviarLinkDeRedefinicao(u, 'admin');
    await this.auditoria.registrar({
      acao: 'auth.password_reset_requested',
      entidade: 'user',
      entidadeId: u.id,
      escolaId: u.escolaId,
      dados: { by: 'admin' },
    });
  }

  async enviarLinkDeRedefinicao(u: Usuario, motivo: 'forgot' | 'admin' | 'activation'): Promise<void> {
    const token = randomBytes(32).toString('base64url');
    await this.redis.set(this.chaves.redefinicaoDeSenha(hashDeToken(token)), u.id, 'EX', TTL_REDEFINICAO_SEGUNDOS);
    const assunto = motivo === 'activation' ? 'Ative sua conta ECOSFERA' : 'Redefinição de senha ECOSFERA';
    try {
      await this.mailer.enviar({
        para: u.email,
        assunto,
        texto: `Use este código em até 30 minutos para definir sua senha: ${token}`,
        sensivel: true,
      });
    } catch (e) {
      // Sem enumeração: a resposta HTTP não muda. Registramos para a operação.
      this.logger.warn({ err: (e as Error).message, motivo }, 'link de redefinição não enviado');
      if (motivo === 'admin') throw e;
    }
  }

  private isca(): Promise<string> {
    this.iscaDeHash ??= this.hasher.gerar(randomBytes(16).toString('hex'));
    return this.iscaDeHash;
  }
}
