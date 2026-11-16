import { hash, verify } from '@node-rs/argon2';

import type { HasherDeSenha } from '../domain/portas';

/**
 * Argon2id (padrão da biblioteca) com parâmetros da recomendação OWASP:
 * 19 MiB de memória, 2 iterações, paralelismo 1.
 */
const OPCOES = { memoryCost: 19456, timeCost: 2, parallelism: 1 };

export class HasherArgon2 implements HasherDeSenha {
  gerar(senha: string): Promise<string> {
    return hash(senha, OPCOES);
  }
  async verificar(hashGuardado: string, senha: string): Promise<boolean> {
    if (!hashGuardado.startsWith('$argon2')) return false; // contas sem senha local ('!')
    try {
      return await verify(hashGuardado, senha);
    } catch {
      return false;
    }
  }
}
