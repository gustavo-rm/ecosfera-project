import type { IncomingMessage, Server } from 'node:http';
import type { Duplex } from 'node:stream';

import { Inject, Injectable, type OnApplicationShutdown } from '@nestjs/common';
import type { Redis } from 'ioredis';
import type { Logger } from 'pino';
import { WebSocket, WebSocketServer } from 'ws';

import { RegistroDeRegrasDePosse } from '../../../shared/autorizacao/registro-de-posse';
import {
  GATE_DE_CONSENTIMENTO,
  type GateDeConsentimento,
  VERIFICADOR_DE_CREDENCIAIS,
  type VerificadorDeCredenciais,
} from '../../../shared/autorizacao/portas';
import {
  CONFIGURACAO,
  type Configuracao,
} from '../../../shared/config/configuracao';
import { PREFIXO_API } from '../../../shared/http/contrato';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { ErroDeAplicacao } from '../../../shared/kernel/erros';
import { novoTraceId } from '../../../shared/observabilidade/contexto';
import { LOGGER } from '../../../shared/observabilidade/logger';
import { Metricas } from '../../../shared/observabilidade/metricas';
import { ChavesRedis } from '../../../shared/redis/chaves';
import { REDIS, REDIS_ASSINANTE } from '../../../shared/redis/redis';
import type { MensagemDoStream } from '../domain/portas';
import {
  ARMAZEM_DE_SESSOES,
  type ArmazemDeSessoes,
} from '../../identity/domain/portas';
import { PlanetaMetaEntity } from './persistencia/planeta.entity';
import { DataSource } from 'typeorm';

const CAMINHO = new RegExp(
  `^/${PREFIXO_API.replace(/\//g, '\\/')}/planets/([0-9a-f-]{36})/stream$`,
  'i',
);
const PAPEIS = new Set(['student', 'teacher', 'coordinator', 'admin']);

interface Conexao {
  ws: WebSocket;
  ator: AtorUsuario;
  planetaId: string;
  donoId: string;
  vivo: boolean;
  deltaPendente?: string;
}

/**
 * WebSocket /planets/{id}/stream (RT-005). Mensagens tipadas {type, payload, tickId}.
 * Sem estado compartilhado em memória: o fan-out é por Redis pub/sub; cada réplica só guarda
 * as próprias conexões abertas.
 */
@Injectable()
export class GatewayDeTempoReal implements OnApplicationShutdown {
  private readonly wss: WebSocketServer;
  private readonly porPlaneta = new Map<string, Set<Conexao>>();
  private batimento?: NodeJS.Timeout;
  intervaloDeBatimentoMs = 30_000;

  constructor(
    @Inject(VERIFICADOR_DE_CREDENCIAIS)
    private readonly credenciais: VerificadorDeCredenciais,
    @Inject(GATE_DE_CONSENTIMENTO) private readonly gate: GateDeConsentimento,
    @Inject(ARMAZEM_DE_SESSOES) private readonly sessoes: ArmazemDeSessoes,
    @Inject(REDIS) private readonly redis: Redis,
    @Inject(REDIS_ASSINANTE) private readonly assinante: Redis,
    @Inject(CONFIGURACAO) private readonly config: Configuracao,
    @Inject(LOGGER) private readonly logger: Logger,
    private readonly posse: RegistroDeRegrasDePosse,
    private readonly chaves: ChavesRedis,
    private readonly metricas: Metricas,
    private readonly ds: DataSource,
  ) {
    this.wss = new WebSocketServer({
      noServer: true,
      maxPayload: 16 * 1024,
      perMessageDeflate: false,
      handleProtocols: (protocolos) =>
        protocolos.has('ecosfera.v1') ? 'ecosfera.v1' : false,
    });
  }

  anexar(servidor: Server): void {
    servidor.on(
      'upgrade',
      (req: IncomingMessage, socket: Duplex, head: Buffer) => {
        const url = new URL(req.url ?? '/', 'http://localhost');
        const m = CAMINHO.exec(url.pathname);
        if (!m) return; // outro uso de upgrade: não é conosco
        void this.aoPedirUpgrade(req, socket, head, m[1].toLowerCase(), url);
      },
    );
    this.assinante.on('message', (canal: string, msg: string) =>
      this.aoReceber(canal, msg),
    );
    void this.assinante.subscribe(this.chaves.canalDeRevogacao());
    this.batimento = setInterval(
      () => void this.bater(),
      this.intervaloDeBatimentoMs,
    );
    this.batimento.unref();
  }

  totalDeConexoes(): number {
    let n = 0;
    for (const s of this.porPlaneta.values()) n += s.size;
    return n;
  }

  private recusar(
    socket: Duplex,
    status: number,
    tipo: string,
    detalhe: string,
  ): void {
    const corpo = JSON.stringify({
      type: `/errors/${tipo}`,
      title: 'Conexão recusada',
      status,
      detail: detalhe,
      instance: 'websocket',
      traceId: novoTraceId(),
    });
    const texto =
      { 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found' }[status] ??
      'Bad Request';
    socket.write(
      `HTTP/1.1 ${status} ${texto}\r\nContent-Type: application/problem+json\r\nContent-Length: ${Buffer.byteLength(corpo)}\r\nConnection: close\r\n\r\n${corpo}`,
    );
    socket.destroy();
  }

  private tokenDoPedido(req: IncomingMessage): string | undefined {
    const auth = req.headers.authorization;
    if (auth?.toLowerCase().startsWith('bearer ')) return auth.slice(7).trim();
    const protocolos = String(req.headers['sec-websocket-protocol'] ?? '')
      .split(',')
      .map((p) => p.trim());
    return protocolos
      .find((p) => p.startsWith('bearer.'))
      ?.slice('bearer.'.length);
  }

  private async aoPedirUpgrade(
    req: IncomingMessage,
    socket: Duplex,
    head: Buffer,
    planetaId: string,
    url: URL,
  ): Promise<void> {
    try {
      const token = this.tokenDoPedido(req);
      if (!token)
        return this.recusar(
          socket,
          401,
          'unauthenticated',
          'Token ausente no handshake',
        );
      const ator = await this.credenciais.verificarAcesso(token);
      if (!PAPEIS.has(ator.papel))
        return this.recusar(
          socket,
          403,
          'forbidden',
          'Papel sem acesso ao stream',
        );
      const regra = this.posse.obter('planeta:ler')!;
      const d = await regra(ator, planetaId);
      if (d === 'inexistente')
        return this.recusar(socket, 404, 'not-found', 'Planeta não encontrado');
      if (d === 'negado')
        return this.recusar(
          socket,
          403,
          'forbidden',
          'Sem acesso a este planeta',
        );
      const meta = await this.ds.getRepository(PlanetaMetaEntity).findOne({
        where: { id: planetaId },
        select: { id: true, ownerUserId: true },
      });
      if (
        !meta ||
        !(await this.gate.permite(meta.ownerUserId, 'platform_use'))
      ) {
        return this.recusar(
          socket,
          403,
          'consent-required',
          'Consentimento do responsável necessário',
        );
      }
      this.wss.handleUpgrade(
        req,
        socket,
        head,
        (ws) =>
          void this.aoConectar(ws, ator, planetaId, meta.ownerUserId, url),
      );
    } catch (e) {
      if (e instanceof ErroDeAplicacao && e.tipo === 'unauthenticated')
        return this.recusar(socket, 401, 'unauthenticated', e.message);
      this.logger.error(
        { err: (e as Error).message },
        'falha no handshake do WebSocket',
      );
      this.recusar(socket, 400, 'bad-request', 'Falha no handshake');
    }
  }

  private async aoConectar(
    ws: WebSocket,
    ator: AtorUsuario,
    planetaId: string,
    donoId: string,
    url: URL,
  ): Promise<void> {
    const c: Conexao = { ws, ator, planetaId, donoId, vivo: true };
    let grupo = this.porPlaneta.get(planetaId);
    if (!grupo) {
      grupo = new Set();
      this.porPlaneta.set(planetaId, grupo);
      await this.assinante.subscribe(this.chaves.canalDoPlaneta(planetaId));
    }
    grupo.add(c);
    this.metricas.conexoesWs.inc();
    ws.on('pong', () => (c.vivo = true));
    ws.on('message', () => undefined); // o canal é só servidor → cliente
    ws.on('close', () => void this.remover(c));
    ws.on('error', () => ws.terminate());
    this.enviar(
      c,
      JSON.stringify({
        type: 'event',
        payload: { kind: 'connected', planetId: planetaId },
        tickId: 0,
      } satisfies MensagemDoStream),
    );
    // Reconexão: reenvia o que o cliente perdeu desde lastTickId.
    const ultimo = Number(url.searchParams.get('lastTickId') ?? NaN);
    if (Number.isFinite(ultimo)) {
      const guardadas = (
        await this.redis.lrange(this.chaves.replayDoPlaneta(planetaId), 0, -1)
      ).reverse();
      for (const g of guardadas) {
        const m = JSON.parse(g) as MensagemDoStream;
        if (m.tickId > ultimo) this.enviar(c, g);
      }
    }
  }

  private async remover(c: Conexao): Promise<void> {
    const grupo = this.porPlaneta.get(c.planetaId);
    if (!grupo?.delete(c)) return;
    this.metricas.conexoesWs.dec();
    if (grupo.size === 0) {
      this.porPlaneta.delete(c.planetaId);
      await this.assinante.unsubscribe(this.chaves.canalDoPlaneta(c.planetaId));
    }
  }

  private aoReceber(canal: string, msg: string): void {
    if (canal === this.chaves.canalDeRevogacao()) {
      const { studentId } = JSON.parse(msg) as { studentId: string };
      for (const grupo of this.porPlaneta.values()) {
        for (const c of grupo)
          if (c.donoId === studentId) c.ws.close(4403, 'consent revoked');
      }
      return;
    }
    const m = /:planet:([0-9a-f-]{36}):stream$/.exec(canal);
    const grupo = m ? this.porPlaneta.get(m[1]) : undefined;
    if (!grupo) return;
    const tipo = (JSON.parse(msg) as MensagemDoStream).type;
    for (const c of grupo) this.enviar(c, msg, tipo === 'delta');
  }

  /**
   * Backpressure: acima do limite, deltas são coalescidos (fica só o mais recente);
   * muito acima, a conexão é fechada com 1013 (tente de novo) para não estourar memória.
   */
  private enviar(c: Conexao, dados: string, ehDelta = false): void {
    if (c.ws.readyState !== WebSocket.OPEN) return;
    const limite = this.config.WS_MAX_BUFFERED_BYTES;
    if (c.ws.bufferedAmount > limite * 4) {
      c.ws.close(1013, 'backpressure');
      return;
    }
    if (ehDelta && c.ws.bufferedAmount > limite) {
      if (c.deltaPendente) this.metricas.mensagensWsDescartadas.inc();
      c.deltaPendente = dados;
      return;
    }
    c.ws.send(dados, () => {
      if (c.deltaPendente && c.ws.bufferedAmount <= limite) {
        const p = c.deltaPendente;
        c.deltaPendente = undefined;
        this.enviar(c, p, true);
      }
    });
  }

  /** Batimento: derruba conexões mortas e as que perderam sessão ou consentimento. */
  async bater(): Promise<void> {
    for (const grupo of this.porPlaneta.values()) {
      for (const c of grupo) {
        if (!c.vivo) {
          c.ws.terminate();
          continue;
        }
        c.vivo = false;
        c.ws.ping();
        if (!(await this.sessoes.existe(c.ator.sessaoId)))
          c.ws.close(4401, 'session revoked');
        else if (!(await this.gate.permite(c.donoId, 'platform_use')))
          c.ws.close(4403, 'consent revoked');
      }
    }
  }

  onApplicationShutdown(): void {
    if (this.batimento) clearInterval(this.batimento);
    for (const grupo of this.porPlaneta.values())
      for (const c of grupo) c.ws.close(1001, 'server shutdown');
    this.wss.close();
  }
}
