import { context, propagation } from '@opentelemetry/api';

import {
  ErroDeDependencia,
  ErroDeValidacao,
  ErroNaoEncontrado,
  ErroPontosDeAcaoInsuficientes,
} from '../../../shared/kernel/erros';
import type { Metricas } from '../../../shared/observabilidade/metricas';

export interface OpcoesDoCliente {
  baseUrl: string;
  timeoutMs: number;
  repeticoes: number;
  nomeDaDependencia: string;
  /** Credencial de serviço do platform-api junto ao ai-sim-service (contrato a definir; P4). */
  token?: () => Promise<string>;
}

/**
 * Cliente HTTP do ai-sim-service. Timeout por chamada, repetição limitada SÓ para
 * operações idempotentes (GET, ou POST com Idempotency-Key), propagação W3C do traço
 * e tradução de falhas em erros tratados (503/504) — nunca 500 genérico.
 */
export class ClienteHttpDoServico {
  constructor(
    private readonly o: OpcoesDoCliente,
    private readonly metricas: Metricas,
  ) {}

  private cabecalhos(extra: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = { accept: 'application/json', ...extra };
    propagation.inject(context.active(), h);
    return h;
  }

  async requisitar<T>(metodo: 'GET' | 'POST', caminho: string, corpo?: unknown, opcoes: { idempotente?: boolean; operacao: string } = { operacao: caminho }): Promise<T> {
    const idempotente = opcoes.idempotente ?? metodo === 'GET';
    const tentativas = idempotente ? this.o.repeticoes + 1 : 1;
    let ultimo: unknown;
    for (let i = 0; i < tentativas; i++) {
      const fim = this.metricas.chamadasPorta.startTimer({ port: this.o.nomeDaDependencia, operation: opcoes.operacao });
      try {
        const res = await this.fetch(metodo, caminho, corpo);
        fim({ outcome: String(res.status) });
        if (res.status >= 500) {
          ultimo = new ErroDeDependencia(this.o.nomeDaDependencia);
          continue;
        }
        return (await this.traduzir(res)) as T;
      } catch (e) {
        const porTempo = (e as Error).name === 'TimeoutError' || (e as Error).name === 'AbortError';
        fim({ outcome: porTempo ? 'timeout' : 'error' });
        if (e instanceof ErroDeValidacao || e instanceof ErroNaoEncontrado || e instanceof ErroPontosDeAcaoInsuficientes) throw e;
        ultimo = e instanceof ErroDeDependencia ? e : new ErroDeDependencia(this.o.nomeDaDependencia, porTempo);
      }
      if (i + 1 < tentativas) await new Promise((r) => setTimeout(r, 100 * 2 ** i));
    }
    throw ultimo instanceof Error ? ultimo : new ErroDeDependencia(this.o.nomeDaDependencia);
  }

  async fetch(metodo: string, caminho: string, corpo?: unknown, accept = 'application/json'): Promise<Response> {
    const auth: Record<string, string> = this.o.token ? { authorization: `Bearer ${await this.o.token()}` } : {};
    return fetch(`${this.o.baseUrl.replace(/\/$/, '')}${caminho}`, {
      method: metodo,
      headers: this.cabecalhos({ ...auth, accept, ...(corpo !== undefined ? { 'content-type': 'application/json' } : {}) }),
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
      signal: AbortSignal.timeout(this.o.timeoutMs),
    });
  }

  private async traduzir(res: Response): Promise<unknown> {
    const texto = await res.text();
    let corpo: Record<string, unknown> = {};
    try {
      corpo = texto ? (JSON.parse(texto) as Record<string, unknown>) : {};
    } catch {
      throw new ErroDeDependencia(this.o.nomeDaDependencia);
    }
    if (res.ok) return corpo;
    if (res.status === 404) throw new ErroNaoEncontrado('Recurso no serviço de simulação');
    if (res.status === 422 || res.status === 400) throw new ErroDeValidacao(String(corpo.detail ?? 'Parâmetros recusados pelo serviço de simulação'));
    if (res.status === 409 && String(corpo.type ?? '').includes('action-points')) {
      const ap = corpo.actionPoints as { remaining?: number; required?: number } | undefined;
      throw new ErroPontosDeAcaoInsuficientes(ap?.remaining ?? 0, ap?.required ?? 0);
    }
    throw new ErroDeDependencia(this.o.nomeDaDependencia);
  }
}
