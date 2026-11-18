import { Redis } from 'ioredis';

export const REDIS = Symbol('Redis');
/** Conexão dedicada a SUBSCRIBE (pub/sub do WebSocket). */
export const REDIS_ASSINANTE = Symbol('RedisAssinante');
/** Conexão dedicada a leituras bloqueantes (XREADGROUP). */
export const REDIS_BLOQUEANTE = Symbol('RedisBloqueante');

export function criarRedis(url: string, nome: string): Redis {
  return new Redis(url, {
    connectionName: `platform-api:${nome}`,
    maxRetriesPerRequest: 3,
    enableReadyCheck: true,
    lazyConnect: false,
  });
}
