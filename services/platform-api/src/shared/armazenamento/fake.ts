import { createHmac, timingSafeEqual } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, normalize } from 'node:path';

import type { ObjectStorage } from './portas';

/**
 * FAKE do ObjectStorage: arquivos em disco local e URL assinada por HMAC servida pelo próprio
 * platform-api (rota interna /files). Expira como a do S3. Proibido em produção.
 */
export class ArmazenamentoFalso implements ObjectStorage {
  readonly nome = 'FAKE:ObjectStorage';
  constructor(
    private readonly dir: string,
    private readonly segredo: string,
    private readonly baseUrl: string,
    private readonly agora: () => number = () => Date.now(),
  ) {}

  private caminho(bucket: string, chave: string): string {
    const p = normalize(join(this.dir, bucket, chave));
    if (!p.startsWith(normalize(this.dir))) throw new Error('chave inválida');
    return p;
  }

  async gravar(bucket: string, chave: string, corpo: Buffer, tipo: string): Promise<void> {
    const p = this.caminho(bucket, chave);
    await mkdir(dirname(p), { recursive: true });
    await writeFile(p, corpo);
    await writeFile(`${p}.tipo`, tipo);
  }

  private assinatura(bucket: string, chave: string, exp: number, nome: string): string {
    return createHmac('sha256', this.segredo).update(`${bucket}\n${chave}\n${exp}\n${nome}`).digest('base64url');
  }

  urlAssinada(bucket: string, chave: string, ttl: number, nome: string): Promise<string> {
    const exp = Math.floor(this.agora() / 1000) + ttl;
    const q = new URLSearchParams({ b: bucket, k: chave, exp: String(exp), n: nome, sig: this.assinatura(bucket, chave, exp, nome) });
    return Promise.resolve(`${this.baseUrl.replace(/\/$/, '')}/platform/api/v1/files?${q.toString()}`);
  }

  /** Valida a URL e devolve o arquivo; null se inválida ou expirada. */
  async abrir(q: Record<string, string | undefined>): Promise<{ corpo: Buffer; tipo: string; nome: string } | null> {
    const { b, k, exp, n, sig } = q;
    if (!b || !k || !exp || !n || !sig) return null;
    const esperado = Buffer.from(this.assinatura(b, k, Number(exp), n));
    const recebido = Buffer.from(sig);
    if (esperado.length !== recebido.length || !timingSafeEqual(esperado, recebido)) return null;
    if (Number(exp) < Math.floor(this.agora() / 1000)) return null;
    try {
      const p = this.caminho(b, k);
      return { corpo: await readFile(p), tipo: await readFile(`${p}.tipo`, 'utf8'), nome: n };
    } catch {
      return null;
    }
  }

  async remover(bucket: string, chave: string): Promise<void> {
    const p = this.caminho(bucket, chave);
    await rm(p, { force: true });
    await rm(`${p}.tipo`, { force: true });
  }
}
