import { createHash, randomBytes } from 'node:crypto';

import { Inject, Injectable } from '@nestjs/common';
import type { Redis } from 'ioredis';
import { createRemoteJWKSet, type JWTPayload, jwtVerify } from 'jose';
import { DataSource } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import {
  CONFIGURACAO,
  type Configuracao,
} from '../../../shared/config/configuracao';
import { PREFIXO_API } from '../../../shared/http/contrato';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import {
  ErroAcessoNegado,
  ErroDeConflito,
  ErroDeDependencia,
  ErroNaoAutenticado,
  ErroNaoEncontrado,
  ErroRequisicaoInvalida,
} from '../../../shared/kernel/erros';
import type { Papel } from '../../../shared/kernel/papeis';
import { ChavesRedis } from '../../../shared/redis/chaves';
import {
  exigirUrlExterna,
  PADRAO_VARIAVEL_DE_SEGREDO_OIDC,
} from '../../../shared/seguranca/url-externa';
import { REDIS } from '../../../shared/redis/redis';
import {
  MatriculaEntity,
  TurmaEntity,
} from '../../education/infrastructure/persistencia/turma.entity';
import {
  REPOSITORIO_DE_USUARIOS,
  type RepositorioDeUsuarios,
} from '../domain/portas';
import { PREFERENCIAS_PADRAO, type Usuario } from '../domain/usuario';
import {
  ContextoLtiEntity,
  IdentidadeExternaEntity,
  PlataformaLtiEntity,
  ProvedorOidcEntity,
} from '../infrastructure/persistencia/federacao.entity';
import {
  ServicoDeAutenticacao,
  type ResultadoDeLogin,
} from './autenticacao.service';

const LTI = 'https://purl.imsglobal.org/spec/lti/claim/';
const TTL_ESTADO = 600;

/**
 * Mapeamento conservador de papéis do LMS (LIS v2). Papel do LMS NUNCA promove um usuário
 * já existente: só vale no primeiro acesso (provisionamento). Admin do LMS vira coordenador.
 */
export function papelDoLms(papeis: string[]): Papel {
  const tem = (s: string) => papeis.some((p) => p.endsWith(s));
  if (
    tem('membership#Instructor') ||
    tem('membership#ContentDeveloper') ||
    tem('membership/Instructor#TeachingAssistant')
  )
    return 'teacher';
  if (tem('membership#Learner')) return 'student';
  if (
    tem('institution/person#Administrator') ||
    tem('membership#Administrator')
  )
    return 'coordinator';
  return 'student';
}

interface EstadoFederado {
  tipo: 'oidc' | 'lti';
  /** Hash do cookie que amarra o login ao navegador que o iniciou (anti-CSRF de login). */
  navegador?: string;
  referenciaId: string;
  nonce: string;
  verificador?: string;
}

interface Descoberta {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
}

@Injectable()
export class ServicoDeFederacao {
  private readonly jwks = new Map<
    string,
    ReturnType<typeof createRemoteJWKSet>
  >();
  private readonly descobertas = new Map<
    string,
    { d: Descoberta; em: number }
  >();

  constructor(
    private readonly ds: DataSource,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(REPOSITORIO_DE_USUARIOS)
    private readonly usuarios: RepositorioDeUsuarios,
    private readonly chaves: ChavesRedis,
    private readonly auth: ServicoDeAutenticacao,
    private readonly auditoria: Auditoria,
  ) {}

  private get producao(): boolean {
    return this.config.NODE_ENV === 'production';
  }

  private conjuntoDeChaves(url: string) {
    let j = this.jwks.get(url);
    if (!j) {
      j = createRemoteJWKSet(new URL(url), {
        timeoutDuration: 3000,
        cooldownDuration: 30_000,
      });
      this.jwks.set(url, j);
    }
    return j;
  }

  private async guardarEstado(
    e: EstadoFederado,
  ): Promise<{ estado: string; vinculo: string }> {
    const estado = randomBytes(24).toString('base64url');
    const vinculo = randomBytes(24).toString('base64url');
    await this.redis.set(
      this.chaves.estadoFederado(estado),
      JSON.stringify({
        ...e,
        navegador: createHash('sha256').update(vinculo).digest('hex'),
      }),
      'EX',
      TTL_ESTADO,
    );
    return { estado, vinculo };
  }

  /** Estado é de uso único (GETDEL) e amarrado ao navegador por cookie: protege contra CSRF de login e repetição. */
  private async consumirEstado(
    estado: string,
    tipo: EstadoFederado['tipo'],
    vinculo: string | undefined,
  ): Promise<EstadoFederado> {
    const bruto = await this.redis.getdel(this.chaves.estadoFederado(estado));
    if (!bruto)
      throw new ErroNaoAutenticado('Estado de login inválido ou expirado');
    const e = JSON.parse(bruto) as EstadoFederado;
    if (e.tipo !== tipo)
      throw new ErroNaoAutenticado('Estado de login inválido');
    if (
      !vinculo ||
      createHash('sha256').update(vinculo).digest('hex') !== e.navegador
    ) {
      throw new ErroNaoAutenticado(
        'Login iniciado em outro navegador; comece de novo',
      );
    }
    return e;
  }

  private async nonceUnico(nonce: string): Promise<void> {
    if (
      (await this.redis.set(
        this.chaves.nonceUsado(nonce),
        '1',
        'EX',
        3600,
        'NX',
      )) !== 'OK'
    ) {
      throw new ErroNaoAutenticado('Nonce reutilizado');
    }
  }

  private async provisionar(
    issuer: string,
    subject: string,
    tipo: 'oidc' | 'lti',
    escolaId: string,
    papel: Papel,
    claims: JWTPayload,
    permitirCriacao: boolean,
  ): Promise<{ usuario: Usuario; novo: boolean }> {
    const repo = this.ds.getRepository(IdentidadeExternaEntity);
    const vinculo = await repo.findOneBy({ issuer, subject });
    if (vinculo) {
      const u = await this.usuarios.porId(vinculo.userId);
      if (!u || !u.podeAutenticar())
        throw new ErroNaoAutenticado('Conta indisponível');
      if (u.escolaId !== escolaId)
        throw new ErroAcessoNegado('Identidade externa ligada a outra escola');
      return { usuario: u, novo: false };
    }
    if (!permitirCriacao)
      throw new ErroAcessoNegado(
        'Conta não vinculada. Peça ao admin da escola para liberar o acesso.',
      );
    // Minimização: só o nome (para o professor reconhecer o aluno). E-mail do LMS não é guardado;
    // usamos um identificador técnico não roteável.
    const nome =
      typeof claims.given_name === 'string'
        ? claims.given_name
        : typeof claims.name === 'string'
          ? claims.name
          : papel === 'student'
            ? 'Estudante'
            : 'Educador';
    const tecnico = createHash('sha256')
      .update(`${issuer}|${subject}`)
      .digest('hex')
      .slice(0, 24);
    const u = await this.usuarios.inserir({
      escolaId,
      nome: nome.slice(0, 200),
      email: `${tipo}-${tecnico}@federado.invalid`,
      papel,
      menor: papel === 'student', // conta de aluno nasce restrita até o consentimento do responsável
      situacao: 'active',
      preferencias: PREFERENCIAS_PADRAO,
      senhaHash: '!',
    });
    await repo.insert({ userId: u.id, providerKind: tipo, issuer, subject });
    await this.auditoria.registrar({
      acao: 'user.federated_provisioned',
      entidade: 'user',
      entidadeId: u.id,
      escolaId,
      dados: { provider: tipo, role: papel },
    });
    return { usuario: u, novo: true };
  }

  // ── LTI 1.3 ──────────────────────────────────────────────────────────────
  async registrarPlataformaLti(
    ator: AtorUsuario,
    d: {
      issuer: string;
      clientId: string;
      deploymentId: string;
      authLoginUrl: string;
      authTokenUrl?: string;
      jwksUrl: string;
    },
  ) {
    if (ator.papel !== 'admin' || !ator.escolaId) throw new ErroAcessoNegado();
    for (const [campo, u] of [
      ['body.authLoginUrl', d.authLoginUrl],
      ['body.jwksUrl', d.jwksUrl],
      ['body.authTokenUrl', d.authTokenUrl],
    ] as const) {
      if (u) await exigirUrlExterna(u, this.producao, campo);
    }
    try {
      const p = await this.ds.getRepository(PlataformaLtiEntity).save({
        ...d,
        authTokenUrl: d.authTokenUrl ?? null,
        schoolId: ator.escolaId,
      });
      await this.auditoria.registrar({
        acao: 'lti.platform_registered',
        entidade: 'lti_platform',
        entidadeId: p.id,
        escolaId: ator.escolaId,
        dados: { issuer: d.issuer, clientId: d.clientId },
      });
      return p;
    } catch (e) {
      if ((e as { code?: string }).code === '23505')
        throw new ErroDeConflito('Plataforma já registrada');
      throw e;
    }
  }

  /** Iniciação de login de terceiros (OIDC third-party initiated login) → redireciona ao LMS. */
  async iniciarLti(q: {
    iss: string;
    login_hint: string;
    target_link_uri?: string;
    lti_message_hint?: string;
    client_id?: string;
    lti_deployment_id?: string;
  }): Promise<{ url: string; vinculo: string }> {
    const where = {
      issuer: q.iss,
      ...(q.client_id ? { clientId: q.client_id } : {}),
      ...(q.lti_deployment_id ? { deploymentId: q.lti_deployment_id } : {}),
    };
    const p = await this.ds.getRepository(PlataformaLtiEntity).findOneBy(where);
    if (!p) throw new ErroNaoEncontrado('Plataforma LTI');
    const nonce = randomBytes(16).toString('base64url');
    const { estado, vinculo } = await this.guardarEstado({
      tipo: 'lti',
      referenciaId: p.id,
      nonce,
    });
    const u = new URL(p.authLoginUrl);
    const params: Record<string, string> = {
      scope: 'openid',
      response_type: 'id_token',
      response_mode: 'form_post',
      prompt: 'none',
      client_id: p.clientId,
      redirect_uri: `${this.config.PUBLIC_BASE_URL}/${PREFIXO_API}/auth/lti/launch`,
      login_hint: q.login_hint,
      state: estado,
      nonce,
    };
    if (q.lti_message_hint) params.lti_message_hint = q.lti_message_hint;
    for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    return { url: u.toString(), vinculo };
  }

  /** Launch: valida o id_token do LMS, provisiona, importa a turma e abre sessão. */
  async launchLti(
    idToken: string,
    estado: string,
    vinculo: string | undefined,
  ): Promise<{
    login: ResultadoDeLogin;
    turma: { id: string; name: string } | null;
  }> {
    const e = await this.consumirEstado(estado, 'lti', vinculo);
    const p = await this.ds
      .getRepository(PlataformaLtiEntity)
      .findOneByOrFail({ id: e.referenciaId });
    let c: JWTPayload;
    try {
      ({ payload: c } = await jwtVerify(
        idToken,
        this.conjuntoDeChaves(p.jwksUrl),
        {
          issuer: p.issuer,
          audience: p.clientId,
          algorithms: ['RS256', 'RS384', 'RS512', 'ES256'],
          maxTokenAge: '10m',
        },
      ));
    } catch (err) {
      await this.auditoria.registrar({
        acao: 'auth.lti_launch_failed',
        entidade: 'lti_platform',
        entidadeId: p.id,
        escolaId: p.schoolId,
        resultado: 'denied',
        dados: { reason: (err as Error).name },
      });
      throw new ErroNaoAutenticado('id_token do LMS inválido');
    }
    if (c.nonce !== e.nonce) throw new ErroNaoAutenticado('Nonce não confere');
    await this.nonceUnico(String(c.nonce));
    if (c[`${LTI}version`] !== '1.3.0')
      throw new ErroRequisicaoInvalida('Versão LTI não suportada');
    if (c[`${LTI}message_type`] !== 'LtiResourceLinkRequest')
      throw new ErroRequisicaoInvalida('Tipo de mensagem LTI não suportado');
    if (c[`${LTI}deployment_id`] !== p.deploymentId)
      throw new ErroNaoAutenticado('deployment_id não confere');
    if (typeof c.sub !== 'string' || c.sub.length === 0)
      throw new ErroNaoAutenticado('id_token sem sub');
    const papeis = Array.isArray(c[`${LTI}roles`])
      ? (c[`${LTI}roles`] as string[])
      : [];
    const papel = papelDoLms(papeis);
    const { usuario } = await this.provisionar(
      p.issuer,
      c.sub,
      'lti',
      p.schoolId,
      papel,
      c,
      true,
    );

    const contexto = c[`${LTI}context`] as
      { id?: string; title?: string; label?: string } | undefined;
    let turma: { id: string; name: string } | null = null;
    if (contexto?.id) turma = await this.importarTurma(p, contexto, usuario);
    await this.auditoria.registrar({
      acao: 'auth.lti_launch',
      entidade: 'session',
      entidadeId: usuario.id,
      escolaId: p.schoolId,
      dados: {
        platformId: p.id,
        classId: turma?.id ?? null,
        role: usuario.papel,
      },
    });
    return { login: await this.auth.abrirSessao(usuario), turma };
  }

  /** Importação de turma (RF-009): o curso do LMS vira turma; alunos entram ao lançar. */
  private async importarTurma(
    p: PlataformaLtiEntity,
    ctx: { id?: string; title?: string; label?: string },
    u: Usuario,
  ) {
    return this.ds.transaction(async (em) => {
      let mapa = await em
        .getRepository(ContextoLtiEntity)
        .findOneBy({ platformId: p.id, contextId: ctx.id! });
      if (!mapa) {
        const t = await em.getRepository(TurmaEntity).save({
          schoolId: p.schoolId,
          name: (ctx.title ?? ctx.label ?? 'Turma LTI').slice(0, 120),
          teacherUserId: u.papel === 'teacher' ? u.id : null,
        });
        await em
          .getRepository(ContextoLtiEntity)
          .insert({ platformId: p.id, contextId: ctx.id!, classId: t.id });
        mapa = await em
          .getRepository(ContextoLtiEntity)
          .findOneByOrFail({ platformId: p.id, contextId: ctx.id! });
      }
      const t = await em
        .getRepository(TurmaEntity)
        .findOneByOrFail({ id: mapa.classId });
      if (u.papel === 'teacher' && !t.teacherUserId)
        await em.update(TurmaEntity, { id: t.id }, { teacherUserId: u.id });
      if (u.papel === 'student')
        await em
          .createQueryBuilder()
          .insert()
          .into(MatriculaEntity)
          .values({ classId: t.id, studentUserId: u.id })
          .orIgnore()
          .execute();
      return { id: t.id, name: t.name };
    });
  }

  // ── OIDC ─────────────────────────────────────────────────────────────────
  async registrarProvedorOidc(
    ator: AtorUsuario,
    d: {
      slug: string;
      issuer: string;
      clientId: string;
      clientSecretEnv?: string;
      defaultRole: Papel;
      allowProvisioning: boolean;
    },
  ) {
    if (ator.papel !== 'admin' || !ator.escolaId) throw new ErroAcessoNegado();
    // O segredo do cliente vem de variável DEDICADA: nunca um segredo do próprio servidor.
    if (
      d.clientSecretEnv &&
      !PADRAO_VARIAVEL_DE_SEGREDO_OIDC.test(d.clientSecretEnv)
    ) {
      throw new ErroAcessoNegado(
        'clientSecretEnv precisa começar com OIDC_CLIENT_SECRET_',
      );
    }
    await exigirUrlExterna(d.issuer, this.producao, 'body.issuer');
    if (!['student', 'teacher'].includes(d.defaultRole))
      throw new ErroAcessoNegado('Papel padrão só pode ser aluno ou professor');
    try {
      const p = await this.ds.getRepository(ProvedorOidcEntity).save({
        ...d,
        clientSecretEnv: d.clientSecretEnv ?? null,
        schoolId: ator.escolaId,
      });
      await this.auditoria.registrar({
        acao: 'oidc.provider_registered',
        entidade: 'oidc_provider',
        entidadeId: p.id,
        escolaId: ator.escolaId,
        dados: { slug: d.slug, issuer: d.issuer },
      });
      return p;
    } catch (e) {
      if ((e as { code?: string }).code === '23505')
        throw new ErroDeConflito('Slug já em uso');
      throw e;
    }
  }

  private async descobrir(issuer: string): Promise<Descoberta> {
    await exigirUrlExterna(issuer, this.producao, 'issuer');
    const c = this.descobertas.get(issuer);
    if (c && Date.now() - c.em < 3600_000) return c.d;
    let d: Descoberta;
    try {
      const r = await fetch(
        `${issuer.replace(/\/$/, '')}/.well-known/openid-configuration`,
        { signal: AbortSignal.timeout(3000) },
      );
      if (!r.ok) throw new Error(String(r.status));
      d = (await r.json()) as Descoberta;
    } catch {
      throw new ErroDeDependencia('provedor OIDC');
    }
    if (d.issuer !== issuer) throw new ErroDeDependencia('provedor OIDC');
    this.descobertas.set(issuer, { d, em: Date.now() });
    return d;
  }

  async autorizarOidc(slug: string): Promise<{ url: string; vinculo: string }> {
    const p = await this.ds
      .getRepository(ProvedorOidcEntity)
      .findOneBy({ slug });
    if (!p) throw new ErroNaoEncontrado('Provedor OIDC');
    const d = await this.descobrir(p.issuer);
    const verificador = randomBytes(32).toString('base64url');
    const nonce = randomBytes(16).toString('base64url');
    const { estado, vinculo } = await this.guardarEstado({
      tipo: 'oidc',
      referenciaId: p.id,
      nonce,
      verificador,
    });
    const u = new URL(d.authorization_endpoint);
    u.search = new URLSearchParams({
      response_type: 'code',
      client_id: p.clientId,
      redirect_uri: `${this.config.PUBLIC_BASE_URL}/${PREFIXO_API}/auth/oidc/${slug}/callback`,
      scope: 'openid profile',
      state: estado,
      nonce,
      code_challenge: createHash('sha256')
        .update(verificador)
        .digest('base64url'),
      code_challenge_method: 'S256',
    }).toString();
    return { url: u.toString(), vinculo };
  }

  async callbackOidc(
    slug: string,
    codigo: string,
    estado: string,
    vinculo: string | undefined,
  ): Promise<ResultadoDeLogin> {
    const e = await this.consumirEstado(estado, 'oidc', vinculo);
    const p = await this.ds
      .getRepository(ProvedorOidcEntity)
      .findOneByOrFail({ id: e.referenciaId });
    if (p.slug !== slug)
      throw new ErroNaoAutenticado('Estado de login inválido');
    const d = await this.descobrir(p.issuer);
    await exigirUrlExterna(d.token_endpoint, this.producao, 'token_endpoint');
    await exigirUrlExterna(d.jwks_uri, this.producao, 'jwks_uri');
    const corpo = new URLSearchParams({
      grant_type: 'authorization_code',
      code: codigo,
      redirect_uri: `${this.config.PUBLIC_BASE_URL}/${PREFIXO_API}/auth/oidc/${slug}/callback`,
      client_id: p.clientId,
      code_verifier: e.verificador!,
    });
    const segredo =
      p.clientSecretEnv &&
      PADRAO_VARIAVEL_DE_SEGREDO_OIDC.test(p.clientSecretEnv)
        ? process.env[p.clientSecretEnv]
        : undefined;
    if (segredo) corpo.set('client_secret', segredo);
    let tokens: { id_token?: string };
    try {
      const r = await fetch(d.token_endpoint, {
        method: 'POST',
        body: corpo,
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        signal: AbortSignal.timeout(5000),
      });
      if (r.status >= 500) throw new ErroDeDependencia('provedor OIDC');
      tokens = (await r.json()) as { id_token?: string };
      if (!r.ok || !tokens.id_token)
        throw new ErroNaoAutenticado('Código de autorização recusado');
    } catch (err) {
      if (err instanceof ErroNaoAutenticado) throw err;
      throw new ErroDeDependencia('provedor OIDC');
    }
    let c: JWTPayload;
    try {
      ({ payload: c } = await jwtVerify(
        tokens.id_token,
        this.conjuntoDeChaves(d.jwks_uri),
        { issuer: p.issuer, audience: p.clientId, maxTokenAge: '10m' },
      ));
    } catch {
      throw new ErroNaoAutenticado('id_token do provedor inválido');
    }
    if (c.nonce !== e.nonce) throw new ErroNaoAutenticado('Nonce não confere');
    await this.nonceUnico(String(c.nonce));
    if (typeof c.sub !== 'string' || c.sub.length === 0)
      throw new ErroNaoAutenticado('id_token sem sub');
    const { usuario } = await this.provisionar(
      p.issuer,
      c.sub,
      'oidc',
      p.schoolId,
      p.defaultRole,
      c,
      p.allowProvisioning,
    );
    await this.auditoria.registrar({
      acao: 'auth.oidc_login',
      entidade: 'session',
      entidadeId: usuario.id,
      escolaId: p.schoolId,
      dados: { provider: slug },
    });
    return this.auth.abrirSessao(usuario);
  }
}
