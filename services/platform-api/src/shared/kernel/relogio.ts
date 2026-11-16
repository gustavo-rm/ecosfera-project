/** Porta de tempo, controlável em testes. */
export interface Relogio {
  agora(): Date;
}
export const RELOGIO = Symbol('Relogio');
export class RelogioDoSistema implements Relogio {
  agora(): Date {
    return new Date();
  }
}
export class RelogioControlado implements Relogio {
  constructor(private atual: Date = new Date('2026-01-01T12:00:00Z')) {}
  agora(): Date {
    return new Date(this.atual.getTime());
  }
  avancar(ms: number): void {
    this.atual = new Date(this.atual.getTime() + ms);
  }
}
