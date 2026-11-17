"use client";
import { BEHAVIOR_WEIGHTS, GENE_BY_ID } from "@/core/state/catalogs";
import type { SpeciesRecord } from "@/core/state/types";
import { fmt, t } from "@/i18n";

const num = (s: SpeciesRecord, k: string) => s.phenotype[k] as number;

/**
 * Tolerance as a curve (optimum and breadth), not a hard limit. The area under the curve is kept constant, so a
 * wider range means a lower peak: the specialist versus generalist trade-off (briefing §4, TOL).
 */
export function ToleranceCurve({ s, opt, breadth, unit }: { s: SpeciesRecord; opt: string; breadth: string; unit: string }) {
  const o = GENE_BY_ID[opt], b = GENE_BY_ID[breadth], mu = num(s, opt), sigma = Math.max(num(s, breadth), (b.min ?? 0.1)), lo = o.min ?? 0, hi = o.max ?? 1;
  const W = 240, H = 90, peak = Math.min(1, (b.min ?? 1) * 3.2 / sigma + 0.18);
  const pts = Array.from({ length: 61 }, (_, i) => { const x = lo + ((hi - lo) * i) / 60; return `${(i / 60) * W},${H - 8 - peak * (H - 22) * Math.exp(-0.5 * ((x - mu) / sigma) ** 2)}`; }).join(" ");
  const summary = t("codex.curveSummary", { label: o.labelPt, opt: `${fmt(mu, 1)} ${unit}`, breadth: `${fmt(sigma, 1)} ${unit}` });
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={summary}>
        <polyline points={`0,${H - 8} ${pts} ${W},${H - 8}`} fill="var(--ec-primary)" fillOpacity={0.2} stroke="var(--ec-primary)" strokeWidth={2} />
        <line x1={0} y1={H - 8} x2={W} y2={H - 8} stroke="var(--ec-border)" />
        <line x1={((mu - lo) / (hi - lo)) * W} y1={H - 8} x2={((mu - lo) / (hi - lo)) * W} y2={10} stroke="var(--ec-text)" strokeDasharray="3 3" />
        <text x={2} y={H} fontSize={9} fill="var(--ec-text-muted)">{fmt(lo)} {unit}</text><text x={W - 2} y={H} fontSize={9} textAnchor="end" fill="var(--ec-text-muted)">{fmt(hi)} {unit}</text>
      </svg>
      <figcaption className="text-[length:var(--ec-text-sm)]"><strong>{o.labelPt}</strong> · <span className="ec-num">{fmt(mu, 1)} {unit}</span> · {b.labelPt}: <span className="ec-num">±{fmt(sigma, 1)} {unit}</span></figcaption>
    </figure>
  );
}

/** Radar of the behavior weights: the "genetic personality" of the lineage. */
export function BehaviorRadar({ s }: { s: SpeciesRecord }) {
  const n = BEHAVIOR_WEIGHTS.length, R = 78, vals = BEHAVIOR_WEIGHTS.map((k) => num(s, k));
  const pt = (i: number, r: number) => { const a = (i / n) * 2 * Math.PI - Math.PI / 2; return [Math.cos(a) * r, Math.sin(a) * r]; };
  const top = BEHAVIOR_WEIGHTS.map((k, i) => ({ k, v: vals[i] })).sort((a, b) => b.v - a.v).slice(0, 3).map((x) => `${GENE_BY_ID[x.k].labelPt} (${fmt(x.v, 2)})`).join(", ");
  return (
    <figure>
      <svg viewBox="-150 -105 300 210" className="w-full max-w-[360px]" role="img" aria-label={t("codex.radarSummary", { top })}>
        {[0.25, 0.5, 0.75, 1].map((f) => <polygon key={f} points={BEHAVIOR_WEIGHTS.map((_, i) => pt(i, R * f).join(",")).join(" ")} fill="none" stroke="var(--ec-chart-grid)" />)}
        {BEHAVIOR_WEIGHTS.map((k, i) => { const [x, y] = pt(i, R), [lx, ly] = pt(i, R + 12); return <g key={k}><line x1={0} y1={0} x2={x} y2={y} stroke="var(--ec-chart-grid)" /><text x={lx} y={ly + 3} fontSize={8.5} textAnchor={lx > 5 ? "start" : lx < -5 ? "end" : "middle"} fill="var(--ec-text)">{GENE_BY_ID[k].labelPt.replace("Prioridade de ", "").replace("Tendência a ", "")}</text></g>; })}
        <polygon points={vals.map((v, i) => pt(i, R * v).join(",")).join(" ")} fill="var(--ec-accent)" fillOpacity={0.3} stroke="var(--ec-accent)" strokeWidth={2} />
        {vals.map((v, i) => { const [x, y] = pt(i, R * v); return <circle key={i} cx={x} cy={y} r={3} fill="var(--ec-accent)" />; })}
      </svg>
      <figcaption className="text-[length:var(--ec-text-sm)]">{t("codex.radarSummary", { top })}</figcaption>
    </figure>
  );
}

const GLYPHS = ["M-6 0a6 6 0 1 0 12 0a6 6 0 1 0-12 0", "M0-7L7 6H-7z", "M-6-6H6V6H-6z", "M0-7L7 0L0 7L-7 0z", "M-6-6L6 6M6-6L-6 6", "M0-7L2 -2L7-2L3 2L5 7L0 4L-5 7L-3 2L-7-2L-2-2z", "M-6 0H6M0-6V6", "M-7 0L-3.500-6H3.500L7 0L3.500 6H-3.500z"];
const GLYPH_NAMES = ["círculo", "triângulo", "quadrado", "losango", "xis", "estrela", "cruz", "hexágono"];
/** A marker (tag) as six glyphs from an alphabet of eight. Shapes, not colors, tell them apart. */
export function TagGlyphs({ symbols, label }: { symbols: number[]; label: string }) {
  return (
    <span className="inline-flex items-center gap-2"><span className="min-w-[150px] text-[length:var(--ec-text-sm)]">{label}</span>
      <svg viewBox="0 0 120 20" width={132} height={22} role="img" aria-label={`${label}: ${symbols.map((x) => GLYPH_NAMES[x % 8]).join(", ")}`}>
        {symbols.map((x, i) => <path key={i} d={GLYPHS[x % 8]} transform={`translate(${10 + i * 20},10)`} fill="none" stroke="var(--ec-text)" strokeWidth={1.6} />)}
      </svg>
    </span>
  );
}
