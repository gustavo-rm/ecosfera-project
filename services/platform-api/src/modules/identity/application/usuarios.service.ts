import { Inject, Injectable } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import { carregarFatosDoAlvo } from '../../../shared/autorizacao/fatos';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroAcessoNegado, ErroDeConflito, ErroDeValidacao, ErroNaoEncontrado } from '../../../shared/kernel/erros';
import { PAPEIS_ATRIBUIVEIS_PELA_ESCOLA, type Papel } from '../../../shared/kernel/papeis';
import { decidirAcessoAoUsuario, type Intencao } from '../../../shared/kernel/politica-de-acesso';
import { VINCULOS_ESCOLARES, type VinculosEscolares } from '../../../shared/kernel/vinculos';
import { problemasDaSenha } from '../domain/politica-de-senha';
import {
  ARMAZEM_DE_SESSOES,
  type ArmazemDeSessoes,
  HASHER_DE_SENHA,
  type HasherDeSenha,
  REPOSITORIO_DE_USUARIOS,
  type RepositorioDeUsuarios,
} from '../domain/portas';
import { mesclarPreferencias, type MudancaDePreferencias, normalizarEmail, PREFERENCIAS_PADRAO, type Usuario } from '../domain/usuario';
import { VinculoResponsavelEntity } from '../infrastructure/persistencia/vinculo-responsavel.entity';
import { ServicoDeAutenticacao } from './autenticacao.service';

export interface DadosDeNovoUsuario {
  name: string;
  email: string;
  role: Papel;
  schoolId?: string | null;
  isMinor?: boolean;
  password?: string;
}

@Injectable()
export class ServicoDeUsuarios {
  constructor(
    @Inject(REPOSITORIO_DE_USUARIOS) private readonly usuarios: RepositorioDeUsuarios,
    @Inject(HASHER_DE_SENHA) private readonly hasher: HasherDeSenha,
    @Inject(ARMAZEM_DE_SESSOES) private readonly sessoes: ArmazemDeSessoes,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    private readonly auth: ServicoDeAutenticacao,
    private readonly auditoria: Auditoria,
    private readonly ds: DataSource,
  ) {}

  /** Defesa em profundidade: a mesma política do guard, com fatos carregados aqui. */
  async exigirAcesso(ator: AtorUsuario, alvoId: string, intencao: Intencao): Promise<void> {
    const d = decidirAcessoAoUsuario(ator, await carregarFatosDoAlvo(this.vinculos, ator, alvoId), intencao);
    if (d === 'inexistente') throw new ErroNaoEncontrado('Usuário');
    if (d === 'negado') throw new ErroAcessoNegado();
  }

  /** RF-002: quem cria quem. */
  private escolaEPapelPermitidos(ator: AtorUsuario | null, d: DadosDeNovoUsuario): string | null {
    if (ator === null || ator.papel === 'platform_admin') {
      const semEscola = d.role === 'platform_admin' || d.role === 'researcher' || d.role === 'guardian';
      if (!semEscola && !d.schoolId) throw new ErroDeValidacao('schoolId é obrigatório para este papel', [{ campo: 'body.schoolId', mensagem: 'obrigatório' }]);
      return d.schoolId ?? null;
    }
    if (ator.papel === 'admin') {
      if (!PAPEIS_ATRIBUIVEIS_PELA_ESCOLA.includes(d.role)) throw new ErroAcessoNegado('Admin da escola não pode criar este papel');
      if (d.schoolId && d.schoolId !== ator.escolaId) throw new ErroAcessoNegado('Só é possível criar usuários na sua escola');
      return ator.escolaId;
    }
    if (ator.papel === 'teacher') {
      if (d.role !== 'student') throw new ErroAcessoNegado('Professor só cria contas de aluno');
      if (d.schoolId && d.schoolId !== ator.escolaId) throw new ErroAcessoNegado('Só é possível criar usuários na sua escola');
      return ator.escolaId;
    }
    throw new ErroAcessoNegado();
  }

  async criar(ator: AtorUsuario | null, d: DadosDeNovoUsuario): Promise<Usuario> {
    const escolaId = this.escolaEPapelPermitidos(ator, d);
    const email = normalizarEmail(d.email);
    if (await this.usuarios.porEmail(email)) throw new ErroDeConflito('Já existe uma conta com este e-mail');
    let senhaHash = '!';
    if (d.password) {
      const problemas = problemasDaSenha(d.password, email);
      if (problemas.length > 0) {
        throw new ErroDeValidacao('A senha não atende à política', problemas.map((m) => ({ campo: 'body.password', mensagem: m })));
      }
      senhaHash = await this.hasher.gerar(d.password);
    }
    const menor = d.role === 'student' ? (d.isMinor ?? true) : false;
    let u: Usuario;
    try {
      u = await this.usuarios.inserir({
        escolaId,
        nome: d.name.trim(),
        email,
        papel: d.role,
        menor,
        situacao: 'active',
        preferencias: PREFERENCIAS_PADRAO,
        senhaHash,
      });
    } catch (e) {
      if ((e as { code?: string }).code === '23505') throw new ErroDeConflito('Já existe uma conta com este e-mail');
      throw e;
    }
    await this.auditoria.registrar({
      acao: 'user.created',
      entidade: 'user',
      entidadeId: u.id,
      escolaId,
      dados: { role: u.papel, isMinor: u.menor, activation: d.password ? 'password' : 'link' },
    });
    if (!d.password) await this.auth.enviarLinkDeRedefinicao(u, 'activation');
    return u;
  }

  async perfil(ator: AtorUsuario, id: string): Promise<Usuario> {
    await this.exigirAcesso(ator, id, 'ler');
    const u = await this.usuarios.porId(id);
    if (!u || u.situacao === 'pseudonymized') throw new ErroNaoEncontrado('Usuário');
    if (ator.usuarioId !== id && u.menor) {
      // Acesso de outra pessoa a dado de menor: auditado (RF-068).
      await this.auditoria.registrar({ acao: 'minor_data.accessed', entidade: 'user', entidadeId: id, escolaId: u.escolaId, dados: { scope: 'profile' } });
    }
    return u;
  }

  async listar(ator: AtorUsuario, papel: Papel | undefined, pagina: number, tamanho: number) {
    if (!ator.escolaId || !['admin', 'coordinator'].includes(ator.papel)) throw new ErroAcessoNegado();
    return this.usuarios.listarDaEscola(ator.escolaId, papel, pagina, tamanho);
  }

  async atualizarPreferencias(ator: AtorUsuario, id: string, mudanca: MudancaDePreferencias): Promise<Usuario> {
    if (ator.usuarioId !== id) throw new ErroNaoEncontrado('Usuário');
    const u = await this.usuarios.porId(id);
    if (!u) throw new ErroNaoEncontrado('Usuário');
    u.preferencias = mesclarPreferencias(u.preferencias, mudanca);
    await this.usuarios.salvar(u);
    return u;
  }

  async alterarPapel(ator: AtorUsuario, id: string, papel: Papel): Promise<Usuario> {
    await this.exigirAcesso(ator, id, 'gerir');
    if (ator.papel !== 'platform_admin' && !PAPEIS_ATRIBUIVEIS_PELA_ESCOLA.includes(papel)) {
      throw new ErroAcessoNegado('Papel não atribuível pela escola');
    }
    if (ator.usuarioId === id) throw new ErroAcessoNegado('Não é possível alterar o próprio papel');
    const u = await this.usuarios.porId(id);
    if (!u) throw new ErroNaoEncontrado('Usuário');
    const anterior = u.papel;
    u.alterarPapel(papel);
    await this.usuarios.salvar(u);
    const revogadas = await this.sessoes.revogarTodasDoUsuario(id);
    await this.auditoria.registrar({
      acao: 'user.role_changed',
      entidade: 'user',
      entidadeId: id,
      escolaId: u.escolaId,
      dados: { from: anterior, to: papel, sessionsRevoked: revogadas },
    });
    return u;
  }

  /** RNF-012: correção de dados pelo admin da escola. */
  async corrigir(ator: AtorUsuario, id: string, d: { name?: string; email?: string }): Promise<Usuario> {
    await this.exigirAcesso(ator, id, 'gerir');
    const u = await this.usuarios.porId(id);
    if (!u || u.situacao === 'pseudonymized') throw new ErroNaoEncontrado('Usuário');
    const campos: string[] = [];
    if (d.name !== undefined) {
      u.nome = d.name.trim();
      campos.push('name');
    }
    if (d.email !== undefined) {
      const novo = normalizarEmail(d.email);
      const outro = await this.usuarios.porEmail(novo);
      if (outro && outro.id !== id) throw new ErroDeConflito('Já existe uma conta com este e-mail');
      u.email = novo;
      campos.push('email');
    }
    await this.usuarios.salvar(u);
    await this.auditoria.registrar({ acao: 'user.rectified', entidade: 'user', entidadeId: id, escolaId: u.escolaId, dados: { fields: campos } });
    return u;
  }

  /** RF-007: vínculo responsável ↔ aluno. */
  async vincularResponsavel(ator: AtorUsuario, alunoId: string, responsavelId: string): Promise<void> {
    await this.exigirAcesso(ator, alunoId, 'gerir');
    const [aluno, resp] = await Promise.all([this.usuarios.porId(alunoId), this.usuarios.porId(responsavelId)]);
    if (!aluno || aluno.papel !== 'student') throw new ErroNaoEncontrado('Aluno');
    if (!resp || resp.papel !== 'guardian' || resp.situacao !== 'active') throw new ErroNaoEncontrado('Responsável');
    if (resp.escolaId !== null && resp.escolaId !== aluno.escolaId) throw new ErroNaoEncontrado('Responsável');
    try {
      await this.ds.getRepository(VinculoResponsavelEntity).insert({ guardianUserId: responsavelId, studentUserId: alunoId });
    } catch (e) {
      if ((e as { code?: string }).code === '23505') throw new ErroDeConflito('Responsável já vinculado a este aluno');
      throw e;
    }
    await this.auditoria.registrar({
      acao: 'guardian.linked',
      entidade: 'user',
      entidadeId: alunoId,
      escolaId: aluno.escolaId,
      dados: { guardianUserId: responsavelId },
    });
  }

  async alunosDoResponsavel(ator: AtorUsuario): Promise<Usuario[]> {
    if (ator.papel !== 'guardian') throw new ErroAcessoNegado();
    const vinculos = await this.ds.getRepository(VinculoResponsavelEntity).findBy({ guardianUserId: ator.usuarioId });
    const alunos = await Promise.all(vinculos.map((v) => this.usuarios.porId(v.studentUserId)));
    return alunos.filter((a): a is Usuario => !!a && a.situacao !== 'pseudonymized');
  }
}
