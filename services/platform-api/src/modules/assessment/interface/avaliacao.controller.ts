import { Body, Controller, Param } from '@nestjs/common';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { Endpoint } from '../../../shared/http/contrato';
import { Consulta, UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { ServicoDeExportacao } from '../application/exportacao.service';
import { ServicoLgpd } from '../application/lgpd.service';
import { ServicoDePainel } from '../application/painel.service';
import { ProjecaoDeAvaliacao } from '../application/projecao.service';
import { ContratosAvaliacao as C, ContratosLgpd as L, type EsquemaConfigAlerta, type EsquemaFeedback, type EsquemaNovaAvaliacao, type EsquemaPolitica } from './contratos';

const EQUIPE = ['teacher', 'coordinator', 'admin'] as const;
const pedagogico = { papeis: EQUIPE, posse: { regra: 'usuario:pedagogico' } };
const turma = { papeis: EQUIPE, posse: { regra: 'turma:gerir' } };

@Controller()
export class AvaliacaoController {
  constructor(
    private readonly painel: ServicoDePainel,
    private readonly exportacao: ServicoDeExportacao,
    private readonly projecao: ProjecaoDeAvaliacao,
    private readonly lgpd: ServicoLgpd,
  ) {}

  @Endpoint(C.eventos)
  @Autorizacao({ servico: true, servicos: ['ai-sim-service'] })
  async eventos(@Body() b: unknown) {
    const r = await this.projecao.tratar(b);
    return { accepted: r !== 'ignored', outcome: r };
  }

  @Endpoint(C.perfil)
  @Autorizacao(pedagogico)
  perfil(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.perfil(a, id);
  }

  @Endpoint(C.evidencias)
  @Autorizacao(pedagogico)
  evidencias(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string, @Consulta() q: { page: number; pageSize: number; competency?: string }) {
    return this.painel.evidencias(a, id, q.competency, q.page, q.pageSize);
  }

  @Endpoint(C.bncc)
  @Autorizacao(pedagogico)
  bncc(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.bncc(a, id);
  }

  @Endpoint(C.registrar)
  @Autorizacao({ papeis: ['teacher'], posse: { regra: 'usuario:pedagogico' } })
  registrar(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaNovaAvaliacao>) {
    return this.painel.registrarAvaliacao(a, id, b);
  }

  @Endpoint(C.avaliacoes)
  @Autorizacao(pedagogico)
  avaliacoes(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.avaliacoes(a, id);
  }

  @Endpoint(C.visao)
  @Autorizacao(turma)
  visao(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.visaoDaTurma(a, id);
  }

  @Endpoint(C.competencias)
  @Autorizacao(turma)
  competencias(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.competenciasDaTurma(a, id);
  }

  @Endpoint(C.alertas)
  @Autorizacao(turma)
  alertas(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.alertas(a, id);
  }

  @Endpoint(C.consentimentos)
  @Autorizacao(turma)
  consentimentos(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.consentimentosDaTurma(a, id);
  }

  @Endpoint(C.escola)
  @Autorizacao({ papeis: ['coordinator', 'admin'] })
  escola(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.painel.agregadoDaEscola(a, id);
  }

  @Endpoint(C.lerConfig)
  @Autorizacao({ papeis: ['coordinator', 'admin', 'teacher'] })
  lerConfig(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    if (a.escolaId !== id) throw new ErroNaoEncontrado('Escola');
    return this.painel.configuracaoDeAlerta(id);
  }

  @Endpoint(C.definirConfig)
  @Autorizacao({ papeis: ['coordinator', 'admin'] })
  definirConfig(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaConfigAlerta>) {
    return this.painel.definirConfiguracaoDeAlerta(a, id, b);
  }

  @Endpoint(C.feedback)
  @Autorizacao({ papeis: ['teacher'], posse: { regra: 'usuario:pedagogico' } })
  feedback(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaFeedback>) {
    return this.painel.enviarFeedback(a, id, b.content, b.assessmentId);
  }

  @Endpoint(C.meusFeedbacks)
  @Autorizacao({ papeis: ['student'] })
  meusFeedbacks(@UsuarioAtual() a: AtorUsuario) {
    return this.painel.meusFeedbacks(a);
  }

  @Endpoint(C.lido)
  @Autorizacao({ papeis: ['student'] })
  async lido(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    await this.painel.marcarLido(a, id);
  }

  @Endpoint(C.exportar)
  @Autorizacao({ papeis: ['teacher', 'coordinator', 'admin'], posse: { regra: 'turma:gerir', parametro: 'classId', origem: 'query' } })
  exportar(@UsuarioAtual() a: AtorUsuario, @Consulta() q: { format: 'pdf' | 'csv'; classId: string }) {
    return this.exportacao.relatorio(a, q.classId, q.format);
  }

  @Endpoint(C.dataset)
  @Autorizacao({ papeis: ['researcher'] })
  dataset(@UsuarioAtual() a: AtorUsuario, @Consulta() q: { anonymized: boolean; format: 'json' | 'csv' }) {
    return this.exportacao.dataset(a, q.anonymized, q.format);
  }

  @Endpoint(L.acesso)
  @Autorizacao({ papeis: ['guardian', 'admin', 'teacher', 'coordinator', 'researcher', 'platform_admin'] })
  acesso(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.lgpd.acesso(a, id);
  }

  @Endpoint(L.exclusao)
  @Autorizacao({ papeis: ['guardian', 'admin'] })
  exclusao(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.lgpd.exclusao(a, id);
  }

  @Endpoint(L.politicas)
  @Autorizacao({ papeis: ['platform_admin', 'admin'] })
  async politicas() {
    return { items: await this.lgpd.politicas() };
  }

  @Endpoint(L.definirPolitica)
  @Autorizacao({ papeis: ['platform_admin'] })
  definirPolitica(@UsuarioAtual() a: AtorUsuario, @Param('category') c: string, @Body() b: z.infer<typeof EsquemaPolitica>) {
    return this.lgpd.definirPolitica(a, c, b.retentionDays);
  }

  @Endpoint(L.executar)
  @Autorizacao({ papeis: ['platform_admin'] })
  executar() {
    return this.lgpd.executarRetencao();
  }
}
