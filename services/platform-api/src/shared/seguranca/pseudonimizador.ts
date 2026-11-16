import { createHmac, randomBytes } from 'node:crypto';

/** Pseudônimos por HMAC-SHA256. Com chave fixa: estáveis (auditoria). Com sal descartável: não ligáveis (pesquisa). */
export class Pseudonimizador {
  constructor(private readonly chave: string) {}

  estavel(valor: string, contexto = 'geral'): string {
    return createHmac('sha256', this.chave).update(`${contexto}:${valor}`).digest('hex').slice(0, 32);
  }

  /** Cria um pseudonimizador de uso único (sal aleatório, descartado após o uso). */
  static descartavel(): (valor: string) => string {
    const sal = randomBytes(32);
    return (valor: string) => createHmac('sha256', sal).update(valor).digest('hex').slice(0, 16);
  }
}

/** Hash de segredos curtos para guardar em Redis (tokens de refresh e de redefinição). */
export function hashDeToken(token: string): string {
  return createHmac('sha256', 'ecosfera-token-hash').update(token).digest('hex');
}
