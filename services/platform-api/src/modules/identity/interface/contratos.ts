import { z } from 'zod';

import { definirEndpoint } from '../../../shared/http/contrato';
import {
  ConsultaPaginada,
  Pagina,
  ParametroId,
} from '../../../shared/http/esquemas-comuns';
import {
  EsquemaCorrecao,
  EsquemaEsqueci,
  EsquemaLogin,
  EsquemaMudancaDePapel,
  EsquemaMudancaDePreferencias,
  EsquemaNovoUsuario,
  EsquemaPapel,
  EsquemaPerfil,
  EsquemaRedefinir,
  EsquemaRefresh,
  EsquemaRespostaLogin,
  EsquemaResumoDeAluno,
  EsquemaTokens,
  EsquemaVinculoResponsavel,
} from './esquemas';

const transporte = {
  'X-Refresh-Transport':
    '`body` para receber o refresh token no corpo (apps sem navegador). Padrão: cookie httpOnly.',
};

export const ContratosAuth = {
  login: definirEndpoint({
    operationId: 'login',
    metodo: 'POST',
    caminho: '/auth/login',
    tag: 'auth',
    resumo: 'Autentica e emite JWT (RF-003)',
    seguranca: 'publico',
    corpo: EsquemaLogin,
    sucesso: 200,
    cabecalhosDeEntrada: transporte,
    respostas: {
      200: {
        descricao: 'Autenticado',
        esquema: EsquemaRespostaLogin,
        cabecalhos: {
          'Set-Cookie': 'ecosfera_refresh (httpOnly, Secure, SameSite=Strict)',
        },
      },
      401: {
        descricao:
          'Credenciais inválidas (mensagem não revela se o e-mail existe)',
      },
    },
  }),
  refresh: definirEndpoint({
    operationId: 'refreshToken',
    metodo: 'POST',
    caminho: '/auth/refresh',
    tag: 'auth',
    resumo: 'Renova o access token com refresh rotativo',
    descricao:
      'Refresh vem do cookie ecosfera_refresh ou do corpo. Reuso de um refresh já usado revoga a sessão inteira.',
    seguranca: 'publico',
    corpo: EsquemaRefresh,
    sucesso: 200,
    cabecalhosDeEntrada: transporte,
    respostas: {
      200: {
        descricao: 'Novo access token (e novo refresh)',
        esquema: EsquemaTokens,
      },
      401: { descricao: 'Refresh inválido, expirado ou reutilizado' },
    },
  }),
  logout: definirEndpoint({
    operationId: 'logout',
    metodo: 'POST',
    caminho: '/auth/logout',
    tag: 'auth',
    resumo: 'Encerra a sessão (revoga access e refresh)',
    seguranca: 'bearer',
    sucesso: 204,
    respostas: { 204: { descricao: 'Sessão encerrada' } },
  }),
  eu: definirEndpoint({
    operationId: 'me',
    metodo: 'GET',
    caminho: '/auth/me',
    tag: 'auth',
    resumo: 'Perfil do usuário autenticado',
    seguranca: 'bearer',
    sucesso: 200,
    respostas: { 200: { descricao: 'Perfil', esquema: EsquemaPerfil } },
  }),
  esqueci: definirEndpoint({
    operationId: 'forgotPassword',
    metodo: 'POST',
    caminho: '/auth/password/forgot',
    tag: 'auth',
    resumo: 'Pede link de redefinição de senha (RF-006)',
    descricao: 'Sempre 202, exista ou não o e-mail.',
    seguranca: 'publico',
    corpo: EsquemaEsqueci,
    sucesso: 202,
    respostas: { 202: { descricao: 'Pedido aceito' } },
  }),
  redefinir: definirEndpoint({
    operationId: 'resetPassword',
    metodo: 'POST',
    caminho: '/auth/password/reset',
    tag: 'auth',
    resumo: 'Define nova senha com o código recebido (RF-006)',
    seguranca: 'publico',
    corpo: EsquemaRedefinir,
    sucesso: 204,
    respostas: {
      204: { descricao: 'Senha alterada; todas as sessões foram encerradas' },
      400: { descricao: 'Código inválido ou expirado' },
    },
  }),
};

export const ContratosUsuarios = {
  criar: definirEndpoint({
    operationId: 'createUser',
    metodo: 'POST',
    caminho: '/users',
    tag: 'users',
    resumo: 'Cria usuário com papel (RF-002)',
    seguranca: 'bearer',
    corpo: EsquemaNovoUsuario,
    sucesso: 201,
    respostas: {
      201: { descricao: 'Usuário criado', esquema: EsquemaPerfil },
      409: { descricao: 'E-mail já cadastrado' },
    },
  }),
  listar: definirEndpoint({
    operationId: 'listUsers',
    metodo: 'GET',
    caminho: '/users',
    tag: 'users',
    resumo: 'Lista usuários da escola do ator',
    seguranca: 'bearer',
    sucesso: 200,
    consulta: ConsultaPaginada.extend({ role: EsquemaPapel.optional() }),
    respostas: {
      200: {
        descricao: 'Página de usuários',
        esquema: Pagina(EsquemaPerfil, 'UserPage'),
      },
    },
  }),
  obter: definirEndpoint({
    operationId: 'getUser',
    metodo: 'GET',
    caminho: '/users/{id}',
    tag: 'users',
    resumo: 'Perfil de um usuário',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Perfil', esquema: EsquemaPerfil },
      404: { descricao: 'Não encontrado (ou de outra escola)' },
    },
  }),
  corrigir: definirEndpoint({
    operationId: 'rectifyUser',
    metodo: 'PATCH',
    caminho: '/users/{id}',
    tag: 'users',
    resumo: 'Corrige nome/e-mail (direito do titular, RNF-012)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaCorrecao,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Corrigido', esquema: EsquemaPerfil },
      404: { descricao: 'Não encontrado' },
      409: { descricao: 'E-mail em uso' },
    },
  }),
  preferencias: definirEndpoint({
    operationId: 'updatePreferences',
    metodo: 'PATCH',
    caminho: '/users/{id}/preferences',
    tag: 'users',
    resumo: 'Acessibilidade e idioma (RF-010)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaMudancaDePreferencias,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Preferências salvas', esquema: EsquemaPerfil },
    },
  }),
  papel: definirEndpoint({
    operationId: 'changeUserRole',
    metodo: 'PATCH',
    caminho: '/users/{id}/role',
    tag: 'users',
    resumo: 'Muda o papel (encerra as sessões do usuário; auditado)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaMudancaDePapel,
    sucesso: 200,
    respostas: {
      200: { descricao: 'Papel alterado', esquema: EsquemaPerfil },
      404: { descricao: 'Não encontrado' },
    },
  }),
  redefinicaoPeloAdmin: definirEndpoint({
    operationId: 'adminPasswordReset',
    metodo: 'POST',
    caminho: '/users/{id}/password-reset',
    tag: 'users',
    resumo: 'Admin envia link de redefinição ao usuário (RF-006)',
    seguranca: 'bearer',
    parametros: ParametroId,
    sucesso: 202,
    respostas: {
      202: { descricao: 'Link enviado' },
      404: { descricao: 'Não encontrado' },
      501: { descricao: 'E-mail não configurado' },
    },
  }),
  vincularResponsavel: definirEndpoint({
    operationId: 'linkGuardian',
    metodo: 'POST',
    caminho: '/users/{id}/guardians',
    tag: 'users',
    resumo: 'Vincula responsável a aluno menor (RF-007)',
    seguranca: 'bearer',
    parametros: ParametroId,
    corpo: EsquemaVinculoResponsavel,
    sucesso: 201,
    respostas: {
      201: { descricao: 'Vínculo criado' },
      404: { descricao: 'Aluno ou responsável não encontrado' },
      409: { descricao: 'Já vinculado' },
    },
  }),
  alunosDoResponsavel: definirEndpoint({
    operationId: 'myStudents',
    metodo: 'GET',
    caminho: '/guardians/me/students',
    tag: 'users',
    resumo: 'Alunos vinculados ao responsável autenticado',
    seguranca: 'bearer',
    sucesso: 200,
    respostas: {
      200: {
        descricao: 'Alunos',
        esquema: z
          .object({ items: z.array(EsquemaResumoDeAluno) })
          .meta({ id: 'StudentSummaryList' }),
      },
    },
  }),
};
