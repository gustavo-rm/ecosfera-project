import { Body, Controller, Param, Res } from '@nestjs/common';
import type { Response } from 'express';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { Endpoint } from '../../../shared/http/contrato';
import { UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroDeAplicacao } from '../../../shared/kernel/erros';
import { ServicoDeTutor } from '../application/tutor.service';
import { ContratosIA as C, type EsquemaConselheiro, type EsquemaDica, type EsquemaExplicar } from './contratos';

@Controller()
export class IaController {
  constructor(private readonly tutor: ServicoDeTutor) {}

  /** SSE sem buffer (RNF-003): cada trecho é escrito assim que chega. */
  @Endpoint(C.explicar)
  @Autorizacao({ papeis: ['student'], posse: { regra: 'planeta:agir', parametro: 'planetId', origem: 'body' }, consentimento: 'platform_use' })
  async explicar(@UsuarioAtual() a: AtorUsuario, @Body() b: z.infer<typeof EsquemaExplicar>, @Res() res: Response) {
    const fluxo = this.tutor.explicar(a, b)[Symbol.asyncIterator]();
    // Primeiro trecho antes dos cabeçalhos: falha de autorização/dependência ainda vira RFC 7807.
    const primeiro = await fluxo.next();
    res.status(200);
    res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
    res.flushHeaders();
    const escrever = (texto: string) => res.write(`data: ${JSON.stringify({ text: texto })}\n\n`);
    try {
      if (!primeiro.done) escrever(primeiro.value);
      for (let r = await fluxo.next(); !r.done; r = await fluxo.next()) {
        if (res.writableEnded || res.destroyed) break;
        escrever(r.value);
      }
      res.write('event: end\ndata: {}\n\n');
    } catch (e) {
      const tipo = e instanceof ErroDeAplicacao ? e.tipo : 'internal';
      res.write(`event: error\ndata: ${JSON.stringify({ type: `/errors/${tipo}`, detail: 'O tutor interrompeu a resposta' })}\n\n`);
    }
    res.end();
  }

  @Endpoint(C.dica)
  @Autorizacao({ papeis: ['student'], posse: { regra: 'planeta:agir', parametro: 'planetId', origem: 'body' }, consentimento: 'platform_use' })
  dica(@UsuarioAtual() a: AtorUsuario, @Body() b: z.infer<typeof EsquemaDica>) {
    return this.tutor.dica(a, b);
  }

  @Endpoint(C.conselheiro)
  @Autorizacao({ papeis: ['student'], consentimento: 'platform_use' })
  conselheiro(@UsuarioAtual() a: AtorUsuario, @Body() b: z.infer<typeof EsquemaConselheiro>) {
    return this.tutor.conselheiro(a, b);
  }

  @Endpoint(C.adaptacao)
  @Autorizacao({ papeis: ['teacher', 'coordinator', 'admin'], posse: { regra: 'usuario:pedagogico', parametro: 'studentId' } })
  adaptacao(@UsuarioAtual() a: AtorUsuario, @Param('studentId') id: string) {
    return this.tutor.adaptacao(a, id);
  }
}
