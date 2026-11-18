import type { Papel } from '../../../shared/kernel/papeis';
import type { Usuario } from './usuario';

export interface RepositorioDeUsuarios {
  porId(id: string): Promise<Usuario | null>;
  porEmail(email: string): Promise<Usuario | null>;
  salvar(u: Usuario): Promise<void>;
  inserir(
    u: Omit<
      Usuario,
      'id' | 'podeAutenticar' | 'alterarPapel' | 'pseudonimizar'
    >,
  ): Promise<Usuario>;
  listarDaEscola(
    escolaId: string,
    papel: Papel | undefined,
    pagina: number,
    tamanho: number,
  ): Promise<{ itens: Usuario[]; total: number }>;
}
export const REPOSITORIO_DE_USUARIOS = Symbol('RepositorioDeUsuarios');

export interface HasherDeSenha {
  gerar(senha: string): Promise<string>;
  verificar(hash: string, senha: string): Promise<boolean>;
}
export const HASHER_DE_SENHA = Symbol('HasherDeSenha');

export interface MensagemDeEmail {
  para: string;
  assunto: string;
  texto: string;
  /** Marca o conteúdo sensível (tokens) para nunca ir a log em produção. */
  sensivel: boolean;
}
export interface Mailer {
  enviar(m: MensagemDeEmail): Promise<void>;
}
export const MAILER = Symbol('Mailer');

export interface DadosDaSessao {
  usuarioId: string;
  criadaEm: number;
}
export type ResultadoDaRotacao =
  | { tipo: 'ok'; novoSegredo: string; usuarioId: string }
  | { tipo: 'reuso'; usuarioId: string }
  | { tipo: 'invalido' };

/** Sessões e famílias de refresh token (Redis). */
export interface ArmazemDeSessoes {
  criar(
    sessaoId: string,
    usuarioId: string,
    segredo: string,
    ttlSegundos: number,
  ): Promise<void>;
  rotacionar(
    sessaoId: string,
    segredoApresentado: string,
    novoSegredo: string,
    ttlSegundos: number,
  ): Promise<ResultadoDaRotacao>;
  existe(sessaoId: string): Promise<boolean>;
  revogar(sessaoId: string): Promise<void>;
  revogarTodasDoUsuario(usuarioId: string): Promise<number>;
}
export const ARMAZEM_DE_SESSOES = Symbol('ArmazemDeSessoes');
