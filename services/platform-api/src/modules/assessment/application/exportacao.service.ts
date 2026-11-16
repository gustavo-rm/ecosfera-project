import { randomUUID } from 'node:crypto';

import { Inject, Injectable } from '@nestjs/common';
import PDFDocument from 'pdfkit';
import { DataSource } from 'typeorm';

import { OBJECT_STORAGE, type ObjectStorage, TIPOS_PERMITIDOS } from '../../../shared/armazenamento/portas';
import { Auditoria } from '../../../shared/auditoria/auditoria';
import { CONFIGURACAO, type Configuracao } from '../../../shared/config/configuracao';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroAcessoNegado, ErroCargaGrandeDemais, ErroDeValidacao } from '../../../shared/kernel/erros';
import { RELOGIO, type Relogio } from '../../../shared/kernel/relogio';
import { Pseudonimizador } from '../../../shared/seguranca/pseudonimizador';
import { ServicoDeEducacao } from '../../education/application/educacao.service';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import { anonimizar, procurarPII } from '../domain/anonimizacao';
import { ConsultasDeAvaliacao } from '../infrastructure/consultas';
import { RegistroDeExportacaoEntity } from '../infrastructure/persistencia/avaliacao.entity';

export const K_ANONIMATO = 5;

function csv(linhas: Record<string, unknown>[]): string {
  if (linhas.length === 0) return '';
  const colunas = Object.keys(linhas[0]!);
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    // Protege contra injeção de fórmula em planilhas.
    const seguro = /^[=+\-@]/.test(s) ? `'${s}` : s;
    return /[",\n]/.test(seguro) ? `"${seguro.replace(/"/g, '""')}"` : seguro;
  };
  return [colunas.join(','), ...linhas.map((l) => colunas.map((c) => esc(l[c])).join(','))].join('\n') + '\n';
}

function pdf(titulo: string, linhas: Record<string, unknown>[], nota: string): Promise<Buffer> {
  return new Promise((ok, falha) => {
    const doc = new PDFDocument({ size: 'A4', margin: 40, info: { Title: titulo, Producer: 'ECOSFERA platform-api' } });
    const partes: Buffer[] = [];
    doc.on('data', (b: Buffer) => partes.push(b));
    doc.on('end', () => ok(Buffer.concat(partes)));
    doc.on('error', falha);
    doc.fontSize(16).text(titulo);
    doc.moveDown().fontSize(9).fillColor('#555').text(nota).fillColor('#000');
    doc.moveDown();
    for (const l of linhas) doc.fontSize(10).text(Object.values(l).map((v) => (v === null ? '—' : String(v))).join('  |  '));
    doc.end();
  });
}

@Injectable()
export class ServicoDeExportacao {
  constructor(
    private readonly ds: DataSource,
    private readonly consultas: ConsultasDeAvaliacao,
    private readonly educacao: ServicoDeEducacao,
    private readonly consentimento: ServicoDeConsentimento,
    private readonly auditoria: Auditoria,
    @Inject(OBJECT_STORAGE) private readonly storage: ObjectStorage,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(RELOGIO) private readonly relogio: Relogio,
  ) {}

  private async guardar(ator: AtorUsuario, tipo: 'report' | 'dataset', formato: 'pdf' | 'csv' | 'json', corpo: Buffer, nome: string, escolaId: string | null) {
    const mime = formato === 'pdf' ? 'application/pdf' : formato === 'csv' ? 'text/csv' : 'application/json';
    if (!TIPOS_PERMITIDOS.has(mime)) throw new ErroDeValidacao('Formato não permitido');
    if (corpo.length > this.config.EXPORT_MAX_BYTES) throw new ErroCargaGrandeDemais('A exportação excede o tamanho máximo configurado');
    const bucket = tipo === 'report' ? this.config.S3_BUCKET_EXPORTS : this.config.S3_BUCKET_DATASETS;
    const chave = `${escolaId ?? 'global'}/${randomUUID()}.${formato}`;
    await this.storage.gravar(bucket, chave, corpo, mime);
    const reg = await this.ds.getRepository(RegistroDeExportacaoEntity).save({ schoolId: escolaId, requestedByUserId: ator.usuarioId, kind: tipo, format: formato, bucket, objectKey: chave, sizeBytes: corpo.length });
    const ttl = this.config.SIGNED_URL_TTL_SECONDS;
    const url = await this.storage.urlAssinada(bucket, chave, ttl, nome);
    return { exportId: reg.id, format: formato, url, expiresAt: new Date(this.relogio.agora().getTime() + ttl * 1000).toISOString(), sizeBytes: corpo.length };
  }

  /** RF-066: relatório da turma. Só alunos com consentimento de avaliação entram. */
  async relatorio(ator: AtorUsuario, turmaId: string, formato: 'pdf' | 'csv') {
    const turma = await this.educacao.exigirTurma(ator, turmaId, 'gerir');
    const alunos = await this.consultas.alunosDaTurma(turmaId, turma.escolaId);
    const permitidos: typeof alunos = [];
    for (const a of alunos) if (await this.consentimento.permite(a.id, 'learning_assessment')) permitidos.push(a);
    const est = await this.consultas.estimativasDosAlunos(permitidos.map((a) => a.id), turma.escolaId);
    const nomes = new Map(permitidos.map((a) => [a.id, a.name]));
    const linhas = est
      .map((e) => ({ aluno: nomes.get(e.alunoId) ?? '', competencia: e.competencia, dominio: Math.round(e.probabilidade * 100) / 100, incerteza: e.incerteza, evidencias: e.evidencias, sintetico: e.sintetico }))
      .sort((a, b) => a.aluno.localeCompare(b.aluno) || a.competencia.localeCompare(b.competencia));
    const nota = `Turma ${turma.nome}. ${alunos.length - permitidos.length} aluno(s) fora do relatório por falta de consentimento. Estimativas do serviço de avaliação: apoio à decisão do professor.`;
    const corpo = formato === 'csv' ? Buffer.from(csv(linhas), 'utf8') : await pdf(`Relatório de competências — ${turma.nome}`, linhas, nota);
    const r = await this.guardar(ator, 'report', formato, corpo, `relatorio-${turmaId.slice(0, 8)}.${formato}`, turma.escolaId);
    await this.auditoria.registrar({ acao: 'export.created', entidade: 'export', entidadeId: r.exportId, escolaId: turma.escolaId, dados: { kind: 'report', format: formato, classId: turmaId, students: permitidos.length } });
    return r;
  }

  /** RF-078: dataset anonimizado para pesquisa. Falha fechada se encontrar PII. */
  async dataset(ator: AtorUsuario, anonimizado: boolean, formato: 'json' | 'csv') {
    if (ator.papel !== 'researcher') throw new ErroAcessoNegado();
    if (!anonimizado) throw new ErroDeValidacao('Só é possível exportar o dataset anonimizado', [{ campo: 'query.anonymized', mensagem: 'deve ser true' }]);
    const brutas = await this.consultas.linhasDePesquisa(ator.escolaId);
    const r = anonimizar(brutas, K_ANONIMATO, Pseudonimizador.descartavel());
    const texto = formato === 'csv' ? csv(r.linhas as unknown as Record<string, unknown>[]) : JSON.stringify({ rows: r.linhas }, null, 0);
    // Varredura de PII com os identificadores reais que NÃO podem aparecer.
    const conhecidos = [...new Set(brutas.flatMap((b) => [b.alunoId, b.escolaId]))];
    const achados = procurarPII(texto, conhecidos);
    if (achados.length > 0) {
      await this.auditoria.registrar({ acao: 'research.dataset_blocked', entidade: 'export', resultado: 'failure', dados: { findings: achados } });
      throw new ErroDeValidacao('Exportação bloqueada: a verificação encontrou dado identificável');
    }
    const g = await this.guardar(ator, 'dataset', formato, Buffer.from(texto, 'utf8'), `dataset-ecosfera.${formato}`, ator.escolaId);
    const metodo = { k: K_ANONIMATO, suppressedGroups: r.gruposSuprimidos, suppressedRows: r.linhasSuprimidas, rows: r.linhas.length, technique: 'pseudônimo com sal descartável + generalização (semana, nível) + supressão de grupos < k' };
    await this.auditoria.registrar({ acao: 'research.dataset_exported', entidade: 'export', entidadeId: g.exportId, escolaId: ator.escolaId, dados: metodo });
    return { ...g, anonymization: metodo };
  }
}
