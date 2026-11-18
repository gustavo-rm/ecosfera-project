import type { RegimeMetrics, SeriesHistory } from "./types";

/**
 * The five regime metrics (spec §24.4), computed from the observed series over a window of ticks.
 * The interface only observes: these numbers never go back to the organisms' rules.
 */
export function regimeMetrics(h: SeriesHistory, windowTicks = 2000): RegimeMetrics {
  const n = h.ticks.length;
  if (n < 3) return { dominance: 0, populationCV: 0, extinctionsPer1000: 0, coexisting: 0, autocorrelation: 0 };
  const end = h.ticks[n - 1], startIdx = Math.max(0, h.ticks.findIndex((x) => x >= end - windowTicks));
  const ids = Object.keys(h.populations);
  let total = 0, top = 0, coexisting = 0;
  for (const id of ids) { const v = h.populations[id][n - 1]; total += v; if (v > top) top = v; }
  for (const id of ids) if (h.populations[id][n - 1] > total * 0.005) coexisting++;
  // Mean coefficient of variation and lag-1 autocorrelation of the lineages alive in the whole window.
  let cvSum = 0, acSum = 0, count = 0;
  for (const id of ids) {
    const s = h.populations[id].slice(startIdx);
    if (s.length < 4 || s.some((v) => v <= 0)) continue;
    const mean = s.reduce((a, b) => a + b, 0) / s.length;
    let varSum = 0, cov = 0;
    for (let i = 0; i < s.length; i++) { varSum += (s[i] - mean) ** 2; if (i > 0) cov += (s[i] - mean) * (s[i - 1] - mean); }
    if (varSum === 0) continue;
    cvSum += Math.sqrt(varSum / s.length) / mean; acSum += cov / varSum; count++;
  }
  const span = Math.max(1, end - h.ticks[startIdx]);
  const ext = h.marks.filter((m) => m.kind === "extinction" && m.tick >= end - windowTicks && m.tick <= end).length;
  return { dominance: total ? top / total : 0, populationCV: count ? cvSum / count : 0, extinctionsPer1000: (ext * 1000) / span, coexisting, autocorrelation: count ? acSum / count : 0 };
}
export type Regime = "frozen" | "homeochaos" | "destructive" | "none";
/** Reference bands of the briefing §6. PLACEHOLDER thresholds for the development panel. */
export function classifyRegime(m: RegimeMetrics): Regime {
  if (m.coexisting === 0) return "none";
  if (m.dominance > 0.8 || m.populationCV < 0.05) return "frozen";
  if (m.populationCV > 1 || m.extinctionsPer1000 > 4) return "destructive";
  return "homeochaos";
}
