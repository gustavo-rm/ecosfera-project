import { randomBytes, randomUUID } from 'node:crypto';

import { Inject, Injectable } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { Auditoria } from '../../../shared/auditoria/auditoria';
import {
  CONFIGURACAO,
  type Configuracao,
} from '../../../shared/config/configuracao';
import { registrarNoOutbox } from '../../../shared/eventos/eventos';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import {
  ErroAcessoNegado,
  ErroConsentimentoAusente,
  ErroDeAplicacao,
  ErroNaoEncontrado,
} from '../../../shared/kernel/erros';
import {
  VINCULOS_ESCOLARES,
  type VinculosEscolares,
} from '../../../shared/kernel/vinculos';
import { ServicoDeEducacao } from '../../education/application/educacao.service';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import {
  decidirAcessoAoPlaneta,
  type FatosDoPlaneta,
  type PlanetaMeta,
} from '../domain/planeta';
import {
  type ContextoDaChamada,
  type Intervencao,
  SIMULATION_GATEWAY,
  type SimulationGateway,
} from '../domain/portas';
import { PlanetaMetaEntity } from '../infrastructure/persistencia/planeta.entity';

const paraMeta = (e: PlanetaMetaEntity): PlanetaMeta => ({
  id: e.id,
  donoId: e.ownerUserId,
  escolaId: e.schoolId,
  missaoId: e.missionId,
  eraAtual: e.currentEra,
  seed: e.seed ?? '',
  situacao: e.status,
});

@Injectable()
export class ServicoDePlanetas {
  constructor(
    private readonly ds: DataSource,
    @Inject(SIMULATION_GATEWAY) private readonly sim: SimulationGateway,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    private readonly consentimento: ServicoDeConsentimento,
    private readonly educacao: ServicoDeEducacao,
    private readonly auditoria: Auditoria,
  ) {}

  async fatos(ator: AtorUsuario, planetaId: string): Promise<FatosDoPlaneta> {
    const e = await this.ds.getRepository(PlanetaMetaEntity).findOne({
      where: { id: planetaId },
      select: { id: true, ownerUserId: true, schoolId: true },
    });
    if (!e)
      return {
        existe: false,
        donoId: null,
        escolaId: null,
        professorDoDono: false,
      };
    const prof =
      ator.papel === 'teacher'
        ? await this.vinculos.professorLecionaParaAluno(
            ator.usuarioId,
            e.ownerUserId,
          )
        : false;
    return {
      existe: true,
      donoId: e.ownerUserId,
      escolaId: e.schoolId,
      professorDoDono: prof,
    };
  }

  /** Defesa em profundidade: posse + consentimento do DONO (o dado é dele, mesmo quando quem lê é o professor). */
  async exigir(
    ator: AtorUsuario,
    planetaId: string,
    intencao: 'ler' | 'agir',
  ): Promise<PlanetaMeta> {
    const d = decidirAcessoAoPlaneta(
      ator,
      await this.fatos(ator, planetaId),
      intencao,
    );
    if (d === 'inexistente') throw new ErroNaoEncontrado('Planeta');
    if (d === 'negado') throw new ErroAcessoNegado();
    const e = (await this.ds
      .getRepository(PlanetaMetaEntity)
      .findOneBy({ id: planetaId }))!;
    if (!(await this.consentimento.permite(e.ownerUserId, 'platform_use')))
      throw new ErroConsentimentoAusente('platform_use');
    if (ator.usuarioId !== e.ownerUserId) {
      await this.auditoria.registrar({
        acao: 'minor_data.accessed',
        entidade: 'planet',
        entidadeId: planetaId,
        escolaId: e.schoolId,
        dados: { scope: 'planet', ownerId: e.ownerUserId },
      });
    }
    return paraMeta(e);
  }

  ctx(dono: { donoId: string; escolaId: string | null }): ContextoDaChamada {
    // traceparent é propagado pelo cliente HTTP (OpenTelemetry), não por aqui.
    return { alunoId: dono.donoId, escolaId: dono.escolaId };
  }

  async criar(
    ator: AtorUsuario,
    d: { params: Record<string, unknown>; seed?: string; missionId?: string },
  ) {
    if (ator.papel !== 'student')
      throw new ErroAcessoNegado('Só alunos criam planetas');
    // Sem consentimento, sem coleta: o guard já barrou; o caso de uso confere de novo.
    if (!(await this.consentimento.permite(ator.usuarioId, 'platform_use')))
      throw new ErroConsentimentoAusente('platform_use');
    if (d.missionId) await this.educacao.exigirMissao(ator, d.missionId, 'ler');
    const id = randomUUID();
    const seed = d.seed ?? randomBytes(8).toString('hex');
    const ctx = { alunoId: ator.usuarioId, escolaId: ator.escolaId };
    await this.sim.validar(id, d.params, ctx);
    const estado = await this.sim.criarPlaneta(id, seed, d.params, ctx);
    await this.ds.transaction(async (em) => {
      await em.insert(PlanetaMetaEntity, {
        id,
        ownerUserId: ator.usuarioId,
        schoolId: ator.escolaId,
        missionId: d.missionId ?? null,
        seed,
        currentEra: estado.era,
      });
      await registrarNoOutbox(em, 'PlanetaCriado', id, {
        planetId: id,
        studentId: ator.usuarioId,
        schoolId: ator.escolaId,
        missionId: d.missionId ?? null,
        seed,
      });
    });
    return { planetId: id, seed, state: estado };
  }

  async estado(ator: AtorUsuario, id: string) {
    const m = await this.exigir(ator, id, 'ler');
    const e = await this.sim.estado(id, this.ctx(m));
    if (e.era !== m.eraAtual)
      await this.ds
        .getRepository(PlanetaMetaEntity)
        .update({ id }, { currentEra: e.era, updatedAt: new Date() });
    return { planetId: id, ownerId: m.donoId, missionId: m.missaoId, ...e };
  }

  async validar(
    ator: AtorUsuario,
    id: string,
    params: Record<string, unknown>,
  ) {
    const m = await this.exigir(ator, id, 'agir');
    return this.sim.validar(id, params, this.ctx(m));
  }

  async avancar(
    ator: AtorUsuario,
    id: string,
    passos: number,
    velocidade: number,
  ) {
    const m = await this.exigir(ator, id, 'agir');
    const assincrono = passos > this.config.TICK_SYNC_MAX_STEPS;
    return this.sim.avancar(id, passos, velocidade, assincrono, this.ctx(m));
  }

  async intervir(ator: AtorUsuario, id: string, i: Intervencao) {
    const m = await this.exigir(ator, id, 'agir');
    const r = await this.sim.intervir(id, i, this.ctx(m));
    await this.ds.transaction((em) =>
      registrarNoOutbox(em, 'IntervencaoAplicada', id, {
        planetId: id,
        studentId: m.donoId,
        action: i.action,
        target: i.target,
        cost: i.cost,
        tickId: r.tickId,
      }),
    );
    return r;
  }

  async linhaDoTempo(ator: AtorUsuario, id: string) {
    const m = await this.exigir(ator, id, 'ler');
    return this.sim.linhaDoTempo(id, this.ctx(m));
  }

  async checkpoint(ator: AtorUsuario, id: string) {
    const m = await this.exigir(ator, id, 'agir');
    return this.sim.salvarCheckpoint(id, this.ctx(m));
  }

  async series(ator: AtorUsuario, id: string, metrica: string) {
    const m = await this.exigir(ator, id, 'ler');
    return this.sim.series(id, metrica, this.ctx(m));
  }

  async eventos(ator: AtorUsuario, id: string) {
    const m = await this.exigir(ator, id, 'ler');
    return this.sim.eventos(id, this.ctx(m));
  }

  async responderEvento(
    ator: AtorUsuario,
    id: string,
    eventId: string,
    escolha: string,
  ) {
    const m = await this.exigir(ator, id, 'agir');
    return this.sim.responderEvento(id, eventId, escolha, this.ctx(m));
  }

  /**
   * Ponto de entrada da sincronização offline (RNF-021). Cada ação tem chave de idempotência;
   * reenvio não duplica efeito. A reconciliação last-write-wins é do serviço de simulação.
   */
  async sincronizar(
    ator: AtorUsuario,
    id: string,
    acoes: {
      idempotencyKey: string;
      type: 'intervention' | 'checkpoint' | 'tick';
      payload: Record<string, unknown>;
      /** Marcado pela borda quando o payload não passa no mesmo schema da rota equivalente. */
      invalida?: boolean;
      clientTimestamp: string;
    }[],
    executarUmaVez: <T>(
      escopo: string,
      chave: string,
      fn: () => Promise<T>,
    ) => Promise<{ resultado: T; repetido: boolean }>,
  ) {
    await this.exigir(ator, id, 'agir');
    const resultados: {
      idempotencyKey: string;
      status: 'applied' | 'duplicate' | 'rejected';
      result?: unknown;
      error?: string;
    }[] = [];
    const ordenadas = [...acoes].sort((a, b) =>
      a.clientTimestamp.localeCompare(b.clientTimestamp),
    );
    for (const a of ordenadas) {
      if (a.invalida) {
        resultados.push({
          idempotencyKey: a.idempotencyKey,
          status: 'rejected',
          error: '/errors/validation',
        });
        continue;
      }
      try {
        const r = await executarUmaVez(
          `sync:${id}`,
          a.idempotencyKey,
          async () => {
            if (a.type === 'intervention')
              return this.intervir(
                ator,
                id,
                a.payload as unknown as Intervencao,
              );
            if (a.type === 'checkpoint') return this.checkpoint(ator, id);
            return this.avancar(
              ator,
              id,
              Math.min(
                Number(a.payload.steps ?? 1),
                this.config.TICK_SYNC_MAX_STEPS,
              ),
              Number(a.payload.speed ?? 1),
            );
          },
        );
        resultados.push({
          idempotencyKey: a.idempotencyKey,
          status: r.repetido ? 'duplicate' : 'applied',
          result: r.resultado,
        });
      } catch (e) {
        resultados.push({
          idempotencyKey: a.idempotencyKey,
          status: 'rejected',
          // Só o tipo do erro: mensagens internas não vão ao cliente.
          error:
            e instanceof ErroDeAplicacao
              ? `/errors/${e.tipo}`
              : '/errors/internal',
        });
      }
    }
    return { results: resultados };
  }
}
