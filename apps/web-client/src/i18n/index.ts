/**
 * Minimal i18n (RNF-026): every user-facing string lives in src/i18n/messages. pt-BR is the base locale.
 * A library is not needed yet (one locale, no plural rules beyond simple cases); see docs/frontend/DECISOES.md.
 */
import { ptBR } from "./messages/pt-BR";

export type Locale = "pt-BR";
type Tree = { [k: string]: string | Tree };
const flat: Record<Locale, Record<string, string>> = { "pt-BR": flatten(ptBR as Tree) };
function flatten(tree: Tree, prefix = "", out: Record<string, string> = {}): Record<string, string> {
  for (const [k, v] of Object.entries(tree)) { if (typeof v === "string") out[k === "_" ? prefix.slice(0, -1) : prefix + k] = v; else flatten(v, prefix + k + ".", out); }
  return out;
}
let locale: Locale = "pt-BR";
export const setLocale = (l: Locale) => { locale = l; };
export const hasKey = (key: string) => key in flat[locale];
export const allKeys = () => Object.keys(flat["pt-BR"]);

/** Translate. `{name}` placeholders are replaced by params. Missing keys are visible on purpose: ⟦key⟧. */
export function t(key: string, params?: Record<string, string | number>): string {
  const s = flat[locale][key];
  if (s === undefined) return `⟦${key}⟧`;
  return params ? s.replace(/\{(\w+)\}/g, (_, k) => (params[k] !== undefined ? String(params[k]) : `{${k}}`)) : s;
}
const nf = new Map<string, Intl.NumberFormat>();
/** Number in pt-BR format. */
export function fmt(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return "—";
  let f = nf.get(String(digits));
  if (!f) { f = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }); nf.set(String(digits), f); }
  return f.format(value);
}
/** Compact number with at most three significant digits, for values that span many orders of magnitude. */
export function fmtAuto(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const a = Math.abs(value);
  if (a !== 0 && (a < 0.01 || a >= 1e6)) return value.toExponential(1).replace(".", ",").replace("e", "·10^").replace("+", "");
  return fmt(value, a >= 100 ? 0 : a >= 10 ? 1 : 2);
}
