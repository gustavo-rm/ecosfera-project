import { createHash } from 'node:crypto';

import type { Redis } from 'ioredis';

import type { ChavesRedis } from '../../../shared/redis/chaves';
import type { ArmazemDeSessoes, ResultadoDaRotacao } from '../domain/portas';

const h = (s: string) => createHash('sha256').update(s).digest('hex');
const usados = (chaveSessao: string) => `${chaveSessao}:used`;

/**
 * Rotação atômica: o refresh atual vira "usado"; reapresentar um usado revoga a família (sessão inteira).
 */
const ROTACIONAR = `
if redis.call('EXISTS', KEYS[1]) == 0 then return {'invalido', ''} end
local atual = redis.call('HGET', KEYS[1], 'cur')
local uid = redis.call('HGET', KEYS[1], 'uid')
if atual == ARGV[1] then
  redis.call('SADD', KEYS[2], atual)
  redis.call('HSET', KEYS[1], 'cur', ARGV[2])
  redis.call('EXPIRE', KEYS[1], ARGV[3])
  redis.call('EXPIRE', KEYS[2], ARGV[3])
  return {'ok', uid}
end
if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 1 then
  redis.call('DEL', KEYS[1], KEYS[2])
  return {'reuso', uid}
end
return {'invalido', ''}
`;

export class SessoesRedis implements ArmazemDeSessoes {
  constructor(
    private readonly redis: Redis,
    private readonly chaves: ChavesRedis,
  ) {}

  async criar(
    sessaoId: string,
    usuarioId: string,
    segredo: string,
    ttl: number,
  ): Promise<void> {
    const k = this.chaves.sessao(sessaoId);
    await this.redis
      .multi()
      .hset(k, {
        uid: usuarioId,
        cur: h(segredo),
        criada: Date.now().toString(),
      })
      .expire(k, ttl)
      .sadd(this.chaves.sessoesDoUsuario(usuarioId), sessaoId)
      .expire(this.chaves.sessoesDoUsuario(usuarioId), ttl)
      .exec();
  }

  async rotacionar(
    sessaoId: string,
    apresentado: string,
    novo: string,
    ttl: number,
  ): Promise<ResultadoDaRotacao> {
    const k = this.chaves.sessao(sessaoId);
    const [tipo, uid] = (await this.redis.eval(
      ROTACIONAR,
      2,
      k,
      usados(k),
      h(apresentado),
      h(novo),
      ttl,
    )) as [string, string];
    if (tipo === 'ok') return { tipo: 'ok', novoSegredo: novo, usuarioId: uid };
    if (tipo === 'reuso') {
      await this.redis.srem(this.chaves.sessoesDoUsuario(uid), sessaoId);
      return { tipo: 'reuso', usuarioId: uid };
    }
    return { tipo: 'invalido' };
  }

  async existe(sessaoId: string): Promise<boolean> {
    return (await this.redis.exists(this.chaves.sessao(sessaoId))) === 1;
  }

  async revogar(sessaoId: string): Promise<void> {
    const k = this.chaves.sessao(sessaoId);
    const uid = await this.redis.hget(k, 'uid');
    await this.redis.del(k, usados(k));
    if (uid) await this.redis.srem(this.chaves.sessoesDoUsuario(uid), sessaoId);
  }

  async revogarTodasDoUsuario(usuarioId: string): Promise<number> {
    const conjunto = this.chaves.sessoesDoUsuario(usuarioId);
    const ids = await this.redis.smembers(conjunto);
    if (ids.length > 0) {
      const chaves = ids.flatMap((id) => [
        this.chaves.sessao(id),
        usados(this.chaves.sessao(id)),
      ]);
      await this.redis.del(...chaves);
    }
    await this.redis.del(conjunto);
    return ids.length;
  }
}
