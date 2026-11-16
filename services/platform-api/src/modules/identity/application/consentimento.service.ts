import { Inject, Injectable } from '@nestjs/common';
import type { Redis } from 'ioredis';
import { DataSource, type EntityManager } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import type { GateDeConsentimento } from '../../../shared/autorizacao/portas';
import { registrarNoOutbox } from '../../../shared/eventos/eventos';
import type { AtorServico, AtorUsuario } from '../../../shared/kernel/ator';
import { ErroAcessoNegado, ErroConsentimentoAusente, ErroDeValidacao, ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { FINALIDADES, type Finalidade } from '../../../shared/kernel/finalidades';
import { RELOGIO, type Relogio } from '../../../shared/kernel/relogio';
import { VINCULOS_ESCOLARES, type VinculosEscolares } from '../../../shared/kernel/vinculos';
import { carregarFatosDoAlvo } from '../../../shared/autorizacao/fatos';
import { decidirAcessoAoUsuario } from '../../../shared/kernel/politica-de-acesso';
import { ChavesRedis } from '../../../shared/redis/chaves';
import { REDIS } from '../../../shared/redis/redis';
import { Consentimento, permiteTratamento } from '../domain/consentimento';
import { ConsentimentoEntity } from '../infrastructure/persistencia/consentimento.entity';
import { TextoDeConsentimentoEntity } from '../infrastructure/persistencia/texto-consentimento.entity';
import { UsuarioEntity } from '../infrastructure/persistencia/usuario.entity';

const TTL_CACHE_SEGUNDOS = 60;

export interface SituacaoDeConsentimento {
  studentId: string;
  isMinor: boolean;
  purposes: {
    purpose: Finalidade;
    status: 'pending' | 'granted' | 'revoked' | 'not_required';
    textVersion: string | null;
    grantedAt: Date | null;
    revokedAt: Date | null;
  }[];
}

function paraDominio(e: ConsentimentoEntity): Consentimento {
  return new Consentimento(e.studentUserId, e.purpose, e.status, e.guardianUserId, e.textVersion, e.grantedAt, e.revokedAt, e.revokedByUserId);
}

/**
 * Consentimento bloqueante (RF-008, RNF-009) e gate reutilizável
 * `ConsentimentoVálido(usuário, finalidade)`, usado por todo caso de uso que toca dado de menor.
 */
@Injectable()
export class ServicoDeConsentimento implements GateDeConsentimento {
  constructor(
    private readonly ds: DataSource,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(RELOGIO) private readonly relogio: Relogio,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    private readonly chaves: ChavesRedis,
    private readonly auditoria: Auditoria,
  ) {}

  /** Gate. Lê do cache curto (invalidado a cada mudança) ou do banco. */
  async permite(usuarioId: string, finalidade: Finalidade): Promise<boolean> {
    const chave = this.chaves.consentimento(usuarioId);
    const cache = await this.redis.hgetall(chave);
    if (cache.menor !== undefined) {
      if (cache.menor === '0') return true;
      return cache[finalidade] === '1';
    }
    const u = await this.ds.getRepository(UsuarioEntity).findOne({ where: { id: usuarioId }, select: { id: true, isMinor: true } });
    if (!u) return false;
    const linhas = await this.ds.getRepository(ConsentimentoEntity).findBy({ studentUserId: usuarioId });
    const valor: Record<string, string> = { menor: u.isMinor ? '1' : '0' };
    for (const f of FINALIDADES) {
      valor[f] = permiteTratamento(u.isMinor, linhas.map(paraDominio).find((c) => c.finalidade === f)) ? '1' : '0';
    }
    await this.redis.multi().hset(chave, valor).expire(chave, TTL_CACHE_SEGUNDOS).exec();
    return valor[finalidade] === '1';
  }

  /** Versão do gate que lança erro (para casos de uso). */
  async exigir(usuarioId: string, finalidade: Finalidade): Promise<void> {
    if (!(await this.permite(usuarioId, finalidade))) throw new ErroConsentimentoAusente(finalidade);
  }

  async invalidarCache(usuarioId: string): Promise<void> {
    await this.redis.del(this.chaves.consentimento(usuarioId));
  }

  async situacao(ator: AtorUsuario | AtorServico, alunoId: string): Promise<SituacaoDeConsentimento> {
    if (ator.tipo === 'usuario') {
      const d = decidirAcessoAoUsuario(ator, await carregarFatosDoAlvo(this.vinculos, ator, alunoId), 'ler');
      if (d === 'inexistente') throw new ErroNaoEncontrado('Aluno');
      if (d === 'negado') throw new ErroAcessoNegado();
    }
    return this.situacaoSemChecagem(alunoId);
  }

  async situacaoSemChecagem(alunoId: string): Promise<SituacaoDeConsentimento> {
    const u = await this.ds.getRepository(UsuarioEntity).findOneBy({ id: alunoId });
    if (!u || u.status === 'pseudonymized') throw new ErroNaoEncontrado('Aluno');
    const linhas = (await this.ds.getRepository(ConsentimentoEntity).findBy({ studentUserId: alunoId })).map(paraDominio);
    return {
      studentId: alunoId,
      isMinor: u.isMinor,
      purposes: FINALIDADES.map((f) => {
        const c = linhas.find((l) => l.finalidade === f);
        return {
          purpose: f,
          status: !u.isMinor ? 'not_required' : (c?.estado ?? 'pending'),
          textVersion: c?.versaoDoTexto ?? null,
          grantedAt: c?.concedidoEm ?? null,
          revokedAt: c?.revogadoEm ?? null,
        };
      }),
    };
  }

  /** Só o responsável vinculado concede. Aceite registrado com finalidade, versão do texto e data. */
  async conceder(ator: AtorUsuario, alunoId: string, finalidades: Finalidade[], versaoDoTexto: string): Promise<SituacaoDeConsentimento> {
    await this.exigirResponsavel(ator, alunoId);
    const aluno = await this.ds.getRepository(UsuarioEntity).findOneBy({ id: alunoId });
    if (!aluno || aluno.role !== 'student' || aluno.status !== 'active') throw new ErroNaoEncontrado('Aluno');
    const textos = await this.ds.getRepository(TextoDeConsentimentoEntity).findBy({ version: versaoDoTexto });
    const faltando = finalidades.filter((f) => !textos.some((t) => t.purpose === f && t.reviewStatus !== 'retired'));
    if (faltando.length > 0) {
      throw new ErroDeValidacao('Versão do texto inexistente para a(s) finalidade(s)', faltando.map((f) => ({ campo: 'body.textVersion', mensagem: `sem texto ${versaoDoTexto} para ${f}` })));
    }
    const agora = this.relogio.agora();
    await this.ds.transaction(async (em) => {
      for (const f of finalidades) {
        const c = await this.carregar(em, alunoId, f);
        c.conceder(ator.usuarioId, versaoDoTexto, agora);
        await this.gravar(em, c, aluno.schoolId);
        await this.auditoria.registrar(
          { acao: 'consent.granted', entidade: 'consent', entidadeId: alunoId, escolaId: aluno.schoolId, dados: { purpose: f, textVersion: versaoDoTexto } },
          em,
        );
      }
      await registrarNoOutbox(em, 'ConsentimentoConcedido', alunoId, { studentId: alunoId, purposes: finalidades, textVersion: versaoDoTexto, at: agora.toISOString() });
    });
    await this.invalidarCache(alunoId);
    return this.situacaoSemChecagem(alunoId);
  }

  /** Revogação com efeito imediato: cache invalidado e evento ConsentimentoRevogado publicado. */
  async revogar(ator: AtorUsuario, alunoId: string, finalidades: Finalidade[]): Promise<SituacaoDeConsentimento> {
    await this.exigirResponsavel(ator, alunoId);
    const aluno = await this.ds.getRepository(UsuarioEntity).findOneBy({ id: alunoId });
    if (!aluno) throw new ErroNaoEncontrado('Aluno');
    const agora = this.relogio.agora();
    await this.ds.transaction(async (em) => {
      for (const f of finalidades) {
        const c = await this.carregar(em, alunoId, f);
        c.revogar(ator.usuarioId, agora);
        await this.gravar(em, c, aluno.schoolId);
        await this.auditoria.registrar(
          { acao: 'consent.revoked', entidade: 'consent', entidadeId: alunoId, escolaId: aluno.schoolId, dados: { purpose: f } },
          em,
        );
      }
      await registrarNoOutbox(em, 'ConsentimentoRevogado', alunoId, { studentId: alunoId, purposes: finalidades, at: agora.toISOString() });
    });
    await this.invalidarCache(alunoId);
    return this.situacaoSemChecagem(alunoId);
  }

  async textos(versao?: string) {
    const r = this.ds.getRepository(TextoDeConsentimentoEntity);
    const todos = await r.find({ order: { createdAt: 'DESC' } });
    const filtrados = versao ? todos.filter((t) => t.version === versao) : todos.filter((t) => t.reviewStatus !== 'retired');
    // Mais recente por finalidade.
    const porFinalidade = new Map<string, TextoDeConsentimentoEntity>();
    for (const t of filtrados) if (!porFinalidade.has(t.purpose)) porFinalidade.set(t.purpose, t);
    return [...porFinalidade.values()];
  }

  private async exigirResponsavel(ator: AtorUsuario, alunoId: string): Promise<void> {
    if (ator.papel !== 'guardian') throw new ErroAcessoNegado('Só o responsável vinculado decide sobre o consentimento');
    if (!(await this.vinculos.responsavelPeloAluno(ator.usuarioId, alunoId))) throw new ErroNaoEncontrado('Aluno');
  }

  private async carregar(em: EntityManager, alunoId: string, f: Finalidade): Promise<Consentimento> {
    const e = await em.getRepository(ConsentimentoEntity).findOne({ where: { studentUserId: alunoId, purpose: f }, lock: { mode: 'pessimistic_write' } });
    return e ? paraDominio(e) : Consentimento.pendente(alunoId, f);
  }

  private async gravar(em: EntityManager, c: Consentimento, escolaId: string | null): Promise<void> {
    await em
      .createQueryBuilder()
      .insert()
      .into(ConsentimentoEntity)
      .values({
        studentUserId: c.alunoId,
        purpose: c.finalidade,
        status: c.estado,
        guardianUserId: c.responsavelId,
        textVersion: c.versaoDoTexto,
        grantedAt: c.concedidoEm,
        revokedAt: c.revogadoEm,
        revokedByUserId: c.revogadoPor,
        schoolId: escolaId,
        updatedAt: new Date(),
      })
      .orUpdate(['status', 'guardian_user_id', 'text_version', 'granted_at', 'revoked_at', 'revoked_by_user_id', 'school_id', 'updated_at'], ['student_user_id', 'purpose'])
      .execute();
  }
}
