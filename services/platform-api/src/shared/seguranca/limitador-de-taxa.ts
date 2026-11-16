import type { Redis } from 'ioredis';

import type { ChavesRedis } from '../redis/chaves';

export interface ResultadoDoLimite {
  permitido: boolean;
  usados: number;
  tentarEmSegundos: number;
}

/**
 * Limite por janela fixa no Redis (INCR + EXPIRE atômicos via Lua).
 * Compartilhado entre réplicas: nada em memória do processo.
 */
const SCRIPT = `
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {n, ttl}
`;

export class LimitadorDeTaxa {
  constructor(
    private readonly redis: Redis,
    private readonly chaves: ChavesRedis,
  ) {}

  async consumir(nome: string, chave: string, limite: number, janelaSegundos: number): Promise<ResultadoDoLimite> {
    const [usados, ttl] = (await this.redis.eval(SCRIPT, 1, this.chaves.limite(nome, chave), janelaSegundos)) as [
      number,
      number,
    ];
    return { permitido: usados <= limite, usados, tentarEmSegundos: Math.max(ttl, 1) };
  }

  async zerar(nome: string, chave: string): Promise<void> {
    await this.redis.del(this.chaves.limite(nome, chave));
  }
}
