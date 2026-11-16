import { Body, Controller, Param, Req, Res } from '@nestjs/common';
import type { Request, Response } from 'express';
import { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { definirEndpoint, Endpoint } from '../../../shared/http/contrato';
import { Consulta, UsuarioAtual } from '../../../shared/http/decoradores';
import { Uuid } from '../../../shared/http/esquemas-comuns';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ServicoDeFederacao } from '../application/federacao.service';
import { AuthController } from './auth.controller';
import { EsquemaPapel, EsquemaTokens } from './esquemas';

const url = z.url().max(500);
const InicioLti = z.object({
  iss: z.string().min(1).max(500),
  login_hint: z.string().min(1).max(500),
  target_link_uri: z.string().max(1000).optional(),
  lti_message_hint: z.string().max(2000).optional(),
  client_id: z.string().max(200).optional(),
  lti_deployment_id: z.string().max(200).optional(),
});
const Launch = z
  .object({
    id_token: z.string().min(20).max(20000),
    state: z.string().min(10).max(200),
  })
  .meta({ id: 'LtiLaunchRequest' });
const RespostaLaunch = EsquemaTokens.extend({
  turma: z.object({ id: Uuid, name: z.string() }).nullable(),
}).meta({ id: 'LtiLaunchResponse' });
const NovaPlataforma = z
  .object({
    issuer: z.string().min(1).max(500),
    clientId: z.string().min(1).max(200),
    deploymentId: z.string().min(1).max(200),
    authLoginUrl: url,
    authTokenUrl: url.optional(),
    jwksUrl: url,
  })
  .strict()
  .meta({ id: 'RegisterLtiPlatformRequest' });
const Plataforma = z
  .object({
    id: Uuid,
    issuer: z.string(),
    clientId: z.string(),
    deploymentId: z.string(),
  })
  .meta({ id: 'LtiPlatform' });
const NovoProvedor = z
  .object({
    slug: z.string().regex(/^[a-z0-9-]{3,40}$/),
    issuer: url,
    clientId: z.string().min(1).max(200),
    clientSecretEnv: z
      .string()
      .regex(/^[A-Z][A-Z0-9_]{2,63}$/)
      .optional()
      .describe(
        'NOME da variável de ambiente com o segredo; o segredo nunca vai ao banco',
      ),
    defaultRole: EsquemaPapel,
    allowProvisioning: z.boolean().default(false),
  })
  .strict()
  .meta({ id: 'RegisterOidcProviderRequest' });
const Provedor = z
  .object({
    id: Uuid,
    slug: z.string(),
    issuer: z.string(),
    defaultRole: EsquemaPapel,
    allowProvisioning: z.boolean(),
  })
  .meta({ id: 'OidcProvider' });
const Slug = z.object({ slug: z.string().regex(/^[a-z0-9-]{3,40}$/) });

export const ContratosFederacao = {
  ltiLogin: definirEndpoint({
    operationId: 'ltiLoginInitiation',
    metodo: 'GET',
    caminho: '/auth/lti/login',
    tag: 'auth',
    resumo: 'Iniciação de login LTI 1.3 (redireciona ao LMS)',
    seguranca: 'publico',
    consulta: InicioLti,
    sucesso: 302,
    respostas: {
      302: { descricao: 'Redireciona ao endpoint de autorização do LMS' },
      404: { descricao: 'Plataforma não registrada' },
    },
  }),
  ltiLaunch: definirEndpoint({
    operationId: 'ltiLaunch',
    metodo: 'POST',
    caminho: '/auth/lti/launch',
    tag: 'auth',
    resumo: 'SSO via LTI 1.3 e importação da turma (RF-009)',
    seguranca: 'publico',
    corpo: Launch,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Sessão aberta', esquema: RespostaLaunch },
      401: { descricao: 'id_token, estado ou nonce inválido' },
    },
  }),
  registrarLti: definirEndpoint({
    operationId: 'registerLtiPlatform',
    metodo: 'POST',
    caminho: '/admin/lti/platforms',
    tag: 'federation',
    resumo: 'Registra plataforma LTI da escola',
    seguranca: 'bearer',
    corpo: NovaPlataforma,
    sucesso: 201,
    respostas: {
      201: { descricao: 'Registrada', esquema: Plataforma },
      409: { descricao: 'Já registrada' },
    },
  }),
  registrarOidc: definirEndpoint({
    operationId: 'registerOidcProvider',
    metodo: 'POST',
    caminho: '/admin/oidc/providers',
    tag: 'federation',
    resumo: 'Registra provedor OIDC da escola (Keycloak/Ory/…)',
    seguranca: 'bearer',
    corpo: NovoProvedor,
    sucesso: 201,
    respostas: {
      201: { descricao: 'Registrado', esquema: Provedor },
      409: { descricao: 'Slug em uso' },
    },
  }),
  oidcAutorizar: definirEndpoint({
    operationId: 'oidcAuthorize',
    metodo: 'GET',
    caminho: '/auth/oidc/{slug}/authorize',
    tag: 'auth',
    resumo: 'Início do login OIDC (código + PKCE)',
    seguranca: 'publico',
    parametros: Slug,
    sucesso: 302,
    respostas: {
      302: { descricao: 'Redireciona ao provedor' },
      404: { descricao: 'Provedor não registrado' },
      503: { descricao: 'Provedor indisponível' },
    },
  }),
  oidcCallback: definirEndpoint({
    operationId: 'oidcCallback',
    metodo: 'GET',
    caminho: '/auth/oidc/{slug}/callback',
    tag: 'auth',
    resumo: 'Retorno do provedor OIDC',
    seguranca: 'publico',
    parametros: Slug,
    consulta: z.object({
      code: z.string().min(1).max(2000),
      state: z.string().min(10).max(200),
    }),
    sucesso: 200,
    respostas: {
      200: { descricao: 'Sessão aberta', esquema: EsquemaTokens },
      401: { descricao: 'Login recusado' },
      403: { descricao: 'Conta não vinculada' },
    },
  }),
};

@Controller()
export class FederacaoController {
  constructor(
    private readonly fed: ServicoDeFederacao,
    private readonly auth: AuthController,
  ) {}

  @Endpoint(ContratosFederacao.ltiLogin)
  @Autorizacao({
    publico: true,
    motivo: 'iniciação de login LTI (o LMS chama)',
  })
  async ltiLogin(
    @Consulta() q: z.infer<typeof InicioLti>,
    @Res() res: Response,
  ) {
    res.redirect(302, await this.fed.iniciarLti(q));
  }

  @Endpoint(ContratosFederacao.ltiLaunch)
  @Autorizacao({
    publico: true,
    motivo: 'launch LTI autenticado pelo id_token assinado do LMS',
  })
  async ltiLaunch(
    @Body() b: z.infer<typeof Launch>,
    @Req() req: Request,
    @Res({ passthrough: true }) res: Response,
  ) {
    const r = await this.fed.launchLti(b.id_token, b.state);
    return { ...this.auth.entregar(r.login, req, res), turma: r.turma };
  }

  @Endpoint(ContratosFederacao.registrarLti)
  @Autorizacao({ papeis: ['admin'] })
  async registrarLti(
    @UsuarioAtual() a: AtorUsuario,
    @Body() b: z.infer<typeof NovaPlataforma>,
  ) {
    const p = await this.fed.registrarPlataformaLti(a, b);
    return {
      id: p.id,
      issuer: p.issuer,
      clientId: p.clientId,
      deploymentId: p.deploymentId,
    };
  }

  @Endpoint(ContratosFederacao.registrarOidc)
  @Autorizacao({ papeis: ['admin'] })
  async registrarOidc(
    @UsuarioAtual() a: AtorUsuario,
    @Body() b: z.infer<typeof NovoProvedor>,
  ) {
    const p = await this.fed.registrarProvedorOidc(a, b);
    return {
      id: p.id,
      slug: p.slug,
      issuer: p.issuer,
      defaultRole: p.defaultRole,
      allowProvisioning: p.allowProvisioning,
    };
  }

  @Endpoint(ContratosFederacao.oidcAutorizar)
  @Autorizacao({ publico: true, motivo: 'início do login federado' })
  async oidcAutorizar(@Param('slug') slug: string, @Res() res: Response) {
    res.redirect(302, await this.fed.autorizarOidc(slug));
  }

  @Endpoint(ContratosFederacao.oidcCallback)
  @Autorizacao({
    publico: true,
    motivo: 'retorno do provedor, autenticado por code + state + PKCE',
  })
  async oidcCallback(
    @Param('slug') slug: string,
    @Consulta() q: { code: string; state: string },
    @Req() req: Request,
    @Res({ passthrough: true }) res: Response,
  ) {
    return this.auth.entregar(
      await this.fed.callbackOidc(slug, q.code, q.state),
      req,
      res,
    );
  }
}
