/** Porta de armazenamento de objetos (exportações e datasets). */
export interface ObjectStorage {
  readonly nome: string;
  gravar(bucket: string, chave: string, corpo: Buffer, tipo: string): Promise<void>;
  urlAssinada(bucket: string, chave: string, ttlSegundos: number, nomeDoArquivo: string): Promise<string>;
  remover(bucket: string, chave: string): Promise<void>;
}
export const OBJECT_STORAGE = Symbol('ObjectStorage');

/** Tipos aceitos e limite de tamanho (validação antes de gravar). */
export const TIPOS_PERMITIDOS = new Set(['application/pdf', 'text/csv', 'application/json']);
