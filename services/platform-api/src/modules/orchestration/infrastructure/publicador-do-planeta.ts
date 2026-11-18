import type { Redis } from 'ioredis';

import type { ChavesRedis } from '../../../shared/redis/chaves';
import type { MensagemDoStream, PublicadorDoPlaneta } from '../domain/portas';

/** PUBLISH no canal do planeta + lista curta de replay para reconexão. */
export class PublicadorRedisDoPlaneta implements PublicadorDoPlaneta {
  constructor(
    private readonly redis: Redis,
    private readonly chaves: ChavesRedis,
    private readonly tamanhoReplay: number,
  ) {}
  async publicar(planetaId: string, m: MensagemDoStream): Promise<void> {
    const json = JSON.stringify(m);
    const replay = this.chaves.replayDoPlaneta(planetaId);
    const p = this.redis
      .multi()
      .publish(this.chaves.canalDoPlaneta(planetaId), json);
    if (this.tamanhoReplay > 0)
      p.lpush(replay, json)
        .ltrim(replay, 0, this.tamanhoReplay - 1)
        .expire(replay, 3600);
    await p.exec();
  }
}
