import type { Logger } from 'pino';

import type { ContextoDaChamada, TutorGateway } from '../domain/portas';

const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** FAKE do TutorGateway: respostas fixas, marcadas como [SIMULADO]. Proibido em produção. */
export class TutorFalso implements TutorGateway {
  readonly nome = 'FAKE:TutorGateway';
  constructor(
    private readonly logger: Logger,
    private readonly atrasoMs = 40,
  ) {}

  async *explicar(p: { planetId: string; contextRef: string; question?: string }, _ctx: ContextoDaChamada): AsyncIterable<string> {
    this.logger.debug({ fake: this.nome }, '[FAKE] explicação simulada');
    const partes = [
      '[SIMULADO] ',
      'Quando o CO₂ aumenta, ',
      'a atmosfera retém mais calor ',
      '(efeito estufa), ',
      `e a temperatura do planeta sobe. Contexto: ${p.contextRef}.`,
    ];
    for (const parte of partes) {
      await espera(this.atrasoMs);
      yield parte;
    }
  }

  dica(p: { planetId: string; missionId: string }) {
    return Promise.resolve({ hint: `[SIMULADO] Observe a série de temperatura antes de intervir (missão ${p.missionId.slice(0, 8)}).`, level: 1 });
  }

  conselheiro(p: { role: string; query: string }) {
    return Promise.resolve({ advice: `[SIMULADO] Como ${p.role}, eu compararia ganhos e custos antes de decidir.` });
  }

  adaptacao() {
    return Promise.resolve({ difficulty: 'standard', unlocks: ['[SIMULADO] trade-offs-basicos'] });
  }
}
