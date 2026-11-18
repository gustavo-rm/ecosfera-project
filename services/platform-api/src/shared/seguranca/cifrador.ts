import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';

/**
 * Cifra campos sensíveis em repouso (AES-256-GCM, autenticado).
 * Formato: v1:<base64(iv[12] | tag[16] | texto cifrado)>.
 */
export class Cifrador {
  private readonly chave: Buffer;
  constructor(chaveBase64: string) {
    this.chave = Buffer.from(chaveBase64, 'base64');
    if (this.chave.length !== 32)
      throw new Error('Chave de cifra precisa de 32 bytes');
  }

  cifrar(texto: string): string {
    const iv = randomBytes(12);
    const c = createCipheriv('aes-256-gcm', this.chave, iv);
    const corpo = Buffer.concat([c.update(texto, 'utf8'), c.final()]);
    return `v1:${Buffer.concat([iv, c.getAuthTag(), corpo]).toString('base64')}`;
  }

  decifrar(valor: string): string {
    if (!valor.startsWith('v1:'))
      throw new Error('Formato de cifra desconhecido');
    const bruto = Buffer.from(valor.slice(3), 'base64');
    const d = createDecipheriv(
      'aes-256-gcm',
      this.chave,
      bruto.subarray(0, 12),
    );
    d.setAuthTag(bruto.subarray(12, 28));
    return Buffer.concat([d.update(bruto.subarray(28)), d.final()]).toString(
      'utf8',
    );
  }
}
