import { Body, Controller, Param } from '@nestjs/common';
import { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { definirEndpoint, Endpoint } from '../../../shared/http/contrato';
import { Consulta, ServicoAtual, UsuarioAtual } from '../../../shared/http/decoradores';
import { DataHora, ParametroId, Uuid } from '../../../shared/http/esquemas-comuns';
import type { AtorServico, AtorUsuario } from '../../../shared/kernel/ator';
import { FINALIDADES, type Finalidade } from '../../../shared/kernel/finalidades';
import { ServicoDeConsentimento, type SituacaoDeConsentimento } from '../application/consentimento.service';

const EsquemaFinalidade = z.enum(FINALIDADES).meta({
  id: 'ConsentPurpose',
  description: 'platform_use=usar a plataforma; learning_assessment=evidências e avaliação; research=dataset anonimizado',
});

const EsquemaSituacao = z
  .object({
    studentId: Uuid,
    isMinor: z.boolean(),
    purposes: z.array(
      z.object({
        purpose: EsquemaFinalidade,
        status: z.enum(['pending', 'granted', 'revoked', 'not_required']),
        textVersion: z.string().nullable(),
        grantedAt: DataHora.nullable(),
        revokedAt: DataHora.nullable(),
      }),
    ),
  })
  .meta({ id: 'ConsentStatus' });

const EsquemaConceder = z
  .object({
    purposes: z.array(EsquemaFinalidade).min(1),
    textVersion: z.string().min(1).max(64),
    accepted: z.literal(true).describe('Confirmação explícita do responsável'),
  })
  .strict()
  .meta({ id: 'GrantConsentRequest' });

const EsquemaRevogar = z.object({ purposes: z.array(EsquemaFinalidade).min(1) }).strict().meta({ id: 'RevokeConsentRequest' });

const EsquemaTexto = z
  .object({
    purpose: z.string(),
    version: z.string(),
    locale: z.string(),
    body: z.string(),
    reviewStatus: z.string().describe('pending_legal_review = placeholder ainda não aprovado pelo DPO/jurídico'),
  })
  .meta({ id: 'ConsentText' });

const EsquemaConsentimentoInterno = z
  .object({
    userId: Uuid,
    consentRequired: z.boolean(),
    purposes: z.object({ platform_use: z.boolean(), learning_assessment: z.boolean(), research: z.boolean() }),
  })
  .meta({ id: 'InternalConsentStatus', description: 'Resposta mínima, sem PII' });

export const ContratosConsentimento = {
  registrar: definirEndpoint({
    operationId: 'grantConsent', metodo: 'POST', caminho: '/users/{id}/consent', tag: 'consent',
    resumo: 'Responsável registra consentimento (RF-008)', seguranca: 'bearer', parametros: ParametroId, corpo: EsquemaConceder, sucesso: 201,
    respostas: { 201: { descricao: 'Consentimento registrado', esquema: EsquemaSituacao }, 404: { descricao: 'Aluno não vinculado' }, 422: { descricao: 'Versão de texto inexistente' } },
  }),
  revogar: definirEndpoint({
    operationId: 'revokeConsent', metodo: 'POST', caminho: '/users/{id}/consent/revoke', tag: 'consent',
    resumo: 'Responsável revoga consentimento (efeito imediato)', seguranca: 'bearer', parametros: ParametroId, corpo: EsquemaRevogar, sucesso: 200,
    respostas: { 200: { descricao: 'Revogado', esquema: EsquemaSituacao }, 404: { descricao: 'Aluno não vinculado' }, 409: { descricao: 'Não havia consentimento ativo' } },
  }),
  situacao: definirEndpoint({
    operationId: 'getConsent', metodo: 'GET', caminho: '/users/{id}/consent', tag: 'consent',
    resumo: 'Status LGPD do aluno', seguranca: 'bearer', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Status por finalidade', esquema: EsquemaSituacao }, 404: { descricao: 'Não encontrado' } },
  }),
  textos: definirEndpoint({
    operationId: 'listConsentTexts', metodo: 'GET', caminho: '/consent-texts', tag: 'consent',
    resumo: 'Textos de consentimento vigentes (placeholders versionados)', seguranca: 'bearer', sucesso: 200,
    consulta: z.object({ version: z.string().max(64).optional() }),
    respostas: { 200: { descricao: 'Textos', esquema: z.object({ items: z.array(EsquemaTexto) }).meta({ id: 'ConsentTextList' }) } },
  }),
  interno: definirEndpoint({
    operationId: 'internalConsentStatus', metodo: 'GET', caminho: '/internal/consent/{id}', tag: 'internal',
    resumo: 'Consulta de consentimento para outros serviços (credencial de serviço)', descricao: 'Usado pelo ai-sim-service antes de coletar telemetria. Resposta mínima, sem PII.',
    seguranca: 'servico', parametros: ParametroId, sucesso: 200,
    respostas: { 200: { descricao: 'Situação', esquema: EsquemaConsentimentoInterno }, 404: { descricao: 'Usuário inexistente' } },
  }),
};

function paraResposta(s: SituacaoDeConsentimento) {
  return s;
}

@Controller()
export class ConsentimentoController {
  constructor(private readonly consentimento: ServicoDeConsentimento) {}

  @Endpoint(ContratosConsentimento.registrar)
  @Autorizacao({ papeis: ['guardian'], posse: { regra: 'usuario:ler' } })
  async registrar(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaConceder>) {
    return paraResposta(await this.consentimento.conceder(ator, id, b.purposes, b.textVersion));
  }

  @Endpoint(ContratosConsentimento.revogar)
  @Autorizacao({ papeis: ['guardian'], posse: { regra: 'usuario:ler' } })
  async revogar(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaRevogar>) {
    return paraResposta(await this.consentimento.revogar(ator, id, b.purposes));
  }

  @Endpoint(ContratosConsentimento.situacao)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian'], posse: { regra: 'usuario:ler' } })
  async situacao(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    return paraResposta(await this.consentimento.situacao(ator, id));
  }

  @Endpoint(ContratosConsentimento.textos)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian', 'researcher', 'platform_admin'] })
  async textos(@Consulta() q: { version?: string }) {
    const t = await this.consentimento.textos(q.version);
    return { items: t.map((x) => ({ purpose: x.purpose, version: x.version, locale: x.locale, body: x.body, reviewStatus: x.reviewStatus })) };
  }

  @Endpoint(ContratosConsentimento.interno)
  @Autorizacao({ servico: true })
  async interno(@ServicoAtual() servico: AtorServico, @Param('id') id: string) {
    const s = await this.consentimento.situacao(servico, id);
    const p = (f: Finalidade) => s.purposes.some((x) => x.purpose === f && (x.status === 'granted' || x.status === 'not_required'));
    return {
      userId: id,
      consentRequired: s.isMinor,
      purposes: { platform_use: p('platform_use'), learning_assessment: p('learning_assessment'), research: p('research') },
    };
  }
}
