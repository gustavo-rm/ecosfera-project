import { context, propagation, trace } from '@opentelemetry/api';
import { AsyncLocalStorageContextManager } from '@opentelemetry/context-async-hooks';
import {
  CompositePropagator,
  W3CBaggagePropagator,
  W3CTraceContextPropagator,
} from '@opentelemetry/core';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { IORedisInstrumentation } from '@opentelemetry/instrumentation-ioredis';
import { PgInstrumentation } from '@opentelemetry/instrumentation-pg';
import { resourceFromAttributes } from '@opentelemetry/resources';
import {
  BatchSpanProcessor,
  type SpanProcessor,
  TracerProvider,
} from '@opentelemetry/sdk-trace';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';

let provedor: TracerProvider | undefined;

/**
 * Liga o OpenTelemetry. Sempre: contexto e propagação W3C (traceparent),
 * para que o traceId atravesse platform-api → ai-sim-service.
 * Exportação OTLP só quando OTEL_EXPORTER_OTLP_ENDPOINT está definida
 * (coletor próprio da implantação; nada de SaaS de terceiros por padrão).
 * Deve rodar antes de carregar http/express/pg/ioredis.
 */
export function iniciarRastreamento(): void {
  if (provedor) return;
  const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
  const processadores: SpanProcessor[] = [];
  if (endpoint) {
    processadores.push(
      new BatchSpanProcessor({
        exporter: new OTLPTraceExporter({
          url: `${endpoint.replace(/\/$/, '')}/v1/traces`,
        }),
      }),
    );
  }
  context.setGlobalContextManager(
    new AsyncLocalStorageContextManager().enable(),
  );
  propagation.setGlobalPropagator(
    new CompositePropagator({
      propagators: [
        new W3CTraceContextPropagator(),
        new W3CBaggagePropagator(),
      ],
    }),
  );
  provedor = new TracerProvider({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME ?? 'platform-api',
    }),
    spanProcessors: processadores,
  });
  trace.setGlobalTracerProvider(provedor);
  registerInstrumentations({
    instrumentations: [
      new HttpInstrumentation({
        ignoreIncomingRequestHook: (req) =>
          /\/(health|ready|metrics)$/.test(req.url ?? ''),
      }),
      new ExpressInstrumentation(),
      new PgInstrumentation({ enhancedDatabaseReporting: false }),
      new IORedisInstrumentation(),
    ],
  });
}

export async function encerrarRastreamento(): Promise<void> {
  await provedor?.shutdown().catch(() => undefined);
}
