import { randomUUID } from 'node:crypto';

/** Porta de geração de IDs (UUID v4 — mesmo tipo da baseline). */
export interface GeradorDeIds {
  novo(): string;
}
export const GERADOR_DE_IDS = Symbol('GeradorDeIds');
export class GeradorDeUuid implements GeradorDeIds {
  novo(): string {
    return randomUUID();
  }
}
export class GeradorSequencial implements GeradorDeIds {
  private n = 0;
  novo(): string {
    this.n += 1;
    return `00000000-0000-4000-8000-${this.n.toString(16).padStart(12, '0')}`;
  }
}
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function ehUuid(v: unknown): v is string {
  return typeof v === 'string' && UUID_RE.test(v);
}
