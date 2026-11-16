import { Injectable } from '@nestjs/common';

import type { RegraDePosse } from './portas';

/** Cada contexto registra suas regras de posse aqui (no onModuleInit). */
@Injectable()
export class RegistroDeRegrasDePosse {
  private readonly regras = new Map<string, RegraDePosse>();

  registrar(nome: string, regra: RegraDePosse): void {
    if (this.regras.has(nome))
      throw new Error(`Regra de posse duplicada: ${nome}`);
    this.regras.set(nome, regra);
  }

  obter(nome: string): RegraDePosse | undefined {
    return this.regras.get(nome);
  }

  nomes(): string[] {
    return [...this.regras.keys()].sort();
  }
}
