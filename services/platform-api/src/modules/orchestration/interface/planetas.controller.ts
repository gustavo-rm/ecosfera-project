import { Body, Controller, Headers, Param, Res } from '@nestjs/common';
import type { Response } from 'express';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { Endpoint } from '../../../shared/http/contrato';
import { Consulta, UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ServicoDeIdempotencia } from '../application/idempotencia';
import { ServicoDePlanetas } from '../application/planetas.service';
import {
  ContratosPlanetas as C,
  type EsquemaIntervencao,
  type EsquemaNovoPlaneta,
  type EsquemaResposta,
  type EsquemaSync,
  type EsquemaTick,
  type EsquemaValidar,
} from './contratos';

const LEITORES = ['student', 'teacher', 'coordinator', 'admin'] as const;
const ler = {
  papeis: LEITORES,
  posse: { regra: 'planeta:ler' },
  consentimento: 'platform_use' as const,
};
const agir = {
  papeis: ['student'] as const,
  posse: { regra: 'planeta:agir' },
  consentimento: 'platform_use' as const,
};

@Controller()
export class PlanetasController {
  constructor(
    private readonly planetas: ServicoDePlanetas,
    private readonly idem: ServicoDeIdempotencia,
  ) {}

  @Endpoint(C.criar)
  @Autorizacao({ papeis: ['student'], consentimento: 'platform_use' })
  criar(
    @UsuarioAtual() a: AtorUsuario,
    @Body() b: z.infer<typeof EsquemaNovoPlaneta>,
  ) {
    return this.planetas.criar(a, b);
  }

  @Endpoint(C.obter)
  @Autorizacao(ler)
  obter(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.planetas.estado(a, id);
  }

  @Endpoint(C.validar)
  @Autorizacao(agir)
  validar(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Body() b: z.infer<typeof EsquemaValidar>,
  ) {
    return this.planetas.validar(a, id, b.params);
  }

  @Endpoint(C.tick)
  @Autorizacao(agir)
  async tick(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Body() b: z.infer<typeof EsquemaTick>,
    @Res({ passthrough: true }) res: Response,
  ) {
    const r = await this.planetas.avancar(a, id, b.steps, b.speed);
    if (r.tipo === 'assincrono') {
      res.status(202);
      return { jobId: r.jobId };
    }
    return { delta: r.delta, era: r.era, tickId: r.tickId };
  }

  @Endpoint(C.intervir)
  @Autorizacao(agir)
  async intervir(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Body() b: z.infer<typeof EsquemaIntervencao>,
    @Headers('idempotency-key') chave?: string,
  ) {
    if (!chave) return this.planetas.intervir(a, id, b);
    return (
      await this.idem.executar(
        `intervention:${id}`,
        chave.slice(0, 100),
        a.usuarioId,
        () => this.planetas.intervir(a, id, b),
      )
    ).resultado;
  }

  @Endpoint(C.linha)
  @Autorizacao(ler)
  linha(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.planetas.linhaDoTempo(a, id);
  }

  @Endpoint(C.checkpoint)
  @Autorizacao(agir)
  checkpoint(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.planetas.checkpoint(a, id);
  }

  @Endpoint(C.series)
  @Autorizacao(ler)
  series(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Consulta() q: { metric: string },
  ) {
    return this.planetas.series(a, id, q.metric);
  }

  @Endpoint(C.eventos)
  @Autorizacao(ler)
  eventos(@UsuarioAtual() a: AtorUsuario, @Param('id') id: string) {
    return this.planetas.eventos(a, id);
  }

  @Endpoint(C.responder)
  @Autorizacao(agir)
  responder(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Body() b: z.infer<typeof EsquemaResposta>,
  ) {
    return this.planetas.responderEvento(a, id, b.eventId, b.choice);
  }

  @Endpoint(C.sync)
  @Autorizacao(agir)
  sync(
    @UsuarioAtual() a: AtorUsuario,
    @Param('id') id: string,
    @Body() b: z.infer<typeof EsquemaSync>,
  ) {
    return this.planetas.sincronizar(a, id, b.actions, (escopo, chave, fn) =>
      this.idem.executar(escopo, chave, a.usuarioId, fn),
    );
  }
}
