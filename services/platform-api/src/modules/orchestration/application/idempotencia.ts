import { Inject, Injectable } from '@nestjs/common';
import type { Redis } from 'ioredis';
import { DataSource } from 'typeorm';

import { ErroDeConflito } from '../../../shared/kernel/erros';
import { ChavesRedis } from '../../../shared/redis/chaves';
import { REDIS } from '../../../shared/redis/redis';
import { RegistroDeIdempotenciaEntity } from '../infrastructure/persistencia/planeta.entity';

/**
 * Executa um efeito no máximo uma vez por (escopo, chave). Reenvio devolve a resposta guardada.
 * Pedido concorrente com a mesma chave recebe 409 enquanto o primeiro não termina.
 */
@Injectable()
export class ServicoDeIdempotencia {
  constructor(
    private readonly ds: DataSource,
    @Inject(REDIS) private readonly redis: Redis,
    private readonly chaves: ChavesRedis,
  ) {}

  async executar<T>(escopo: string, chave: string, usuarioId: string, fn: () => Promise<T>): Promise<{ resultado: T; repetido: boolean }> {
    const repo = this.ds.getRepository(RegistroDeIdempotenciaEntity);
    const existente = await repo.findOneBy({ scope: escopo, key: chave });
    if (existente) {
      if (existente.userId !== usuarioId) throw new ErroDeConflito('Chave de idempotência já usada por outro usuário');
      return { resultado: existente.response as T, repetido: true };
    }
    const trava = this.chaves.idempotenciaEmAndamento(escopo, chave);
    if ((await this.redis.set(trava, usuarioId, 'EX', 30, 'NX')) !== 'OK') {
      throw new ErroDeConflito('Pedido com esta chave de idempotência ainda em processamento');
    }
    try {
      const resultado = await fn();
      await repo.createQueryBuilder().insert().values({ scope: escopo, key: chave, userId: usuarioId, statusCode: 200, response: resultado as object }).orIgnore().execute();
      return { resultado, repetido: false };
    } finally {
      await this.redis.del(trava);
    }
  }
}
