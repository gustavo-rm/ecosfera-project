import {
  Counter,
  Gauge,
  Histogram,
  Registry,
  collectDefaultMetrics,
} from '@prometheus-io/client';

/** Métricas Prometheus do processo. Rótulos sem PII (só rotas-modelo e códigos). */
export class Metricas {
  readonly registro = new Registry();
  readonly duracaoHttp = new Histogram({
    name: 'platform_http_request_duration_seconds',
    help: 'Duração das requisições HTTP',
    labelNames: ['method', 'route', 'status'] as const,
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
    registers: [this.registro],
  });
  readonly errosHttp = new Counter({
    name: 'platform_http_errors_total',
    help: 'Respostas de erro por tipo RFC 7807',
    labelNames: ['type', 'status'] as const,
    registers: [this.registro],
  });
  readonly conexoesWs = new Gauge({
    name: 'platform_ws_connections',
    help: 'Conexões WebSocket abertas nesta instância',
    registers: [this.registro],
  });
  readonly mensagensWsDescartadas = new Counter({
    name: 'platform_ws_messages_dropped_total',
    help: 'Deltas descartados/coalescidos por backpressure',
    registers: [this.registro],
  });
  readonly eventosConsumidos = new Counter({
    name: 'platform_events_consumed_total',
    help: 'Eventos consumidos do barramento',
    labelNames: ['type', 'outcome'] as const,
    registers: [this.registro],
  });
  readonly outboxPendente = new Gauge({
    name: 'platform_outbox_pending',
    help: 'Eventos aguardando publicação no outbox',
    registers: [this.registro],
  });
  readonly chamadasPorta = new Histogram({
    name: 'platform_port_call_duration_seconds',
    help: 'Duração das chamadas às portas externas (simulação, tutor)',
    labelNames: ['port', 'operation', 'outcome'] as const,
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [this.registro],
  });
  readonly loginsFalhos = new Counter({
    name: 'platform_auth_login_failures_total',
    help: 'Logins negados',
    registers: [this.registro],
  });

  constructor(padrao = true) {
    if (padrao)
      collectDefaultMetrics({ register: this.registro, prefix: 'platform_' });
  }
}
