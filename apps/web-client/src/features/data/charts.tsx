"use client";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SERIES_COLORS, SERIES_COLORS_DARK } from "@/core/appearance/palettes";
import type { BiosphereFrame, SeriesHistory, SpeciesRecord } from "@/core/state/types";
import { fmt, t } from "@/i18n";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { ChartFrame, Chip, DataTable, Empty, Ped, Toggle } from "@/ui/kit";

export const useSeriesColors = () => (useSettings((s) => s.theme) === "dark" ? SERIES_COLORS_DARK : SERIES_COLORS);
const AXIS = { tick: { fontSize: 11, fill: "var(--ec-text-muted)" }, stroke: "var(--ec-border-subtle)" };
const TIP = { contentStyle: { background: "var(--ec-surface)", border: "1px solid var(--ec-border)", borderRadius: 8, color: "var(--ec-text)" }, labelStyle: { color: "var(--ec-text)" }, itemStyle: { color: "var(--ec-text)" } };
type Key = "o2" | "co2" | "temp" | "biomass" | "richness" | "shannon" | "geneticDistance" | "strategies" | "webComplexity";
const year = (tick: number) => Math.floor(tick / 12);

function rows(h: SeriesHistory, key: Key) { return h.ticks.map((tk, i) => ({ year: year(tk), v: h[key][i] })); }
export function describeSeries(h: SeriesHistory, key: Key): string {
  const v = h[key], n = v.length;
  let min = Infinity, max = -Infinity, iMin = 0, iMax = 0;
  v.forEach((x, i) => { if (x < min) { min = x; iMin = i; } if (x > max) { max = x; iMax = i; } });
  return t("data.series.summary", { name: t(`series.${key}`), y0: fmt(year(h.ticks[0])), y1: fmt(year(h.ticks[n - 1])), from: fmt(v[0], 1), to: fmt(v[n - 1], 1), min: fmt(min, 1), yMin: fmt(year(h.ticks[iMin])), max: fmt(max, 1), yMax: fmt(year(h.ticks[iMax])) });
}
/** Marks over time: eras as dashed lines with a label, events and extinctions as solid lines of another weight. */
function marks(h: SeriesHistory, labels: boolean) {
  return h.marks.filter((m) => m.kind !== "speciation" && m.kind !== "intervention").map((m, i) => (
    <ReferenceLine key={i} x={year(m.tick)} stroke={m.kind === "era" ? "var(--ec-text-muted)" : m.kind === "event" ? "var(--ec-warning)" : "var(--ec-danger)"} strokeDasharray={m.kind === "era" ? "4 4" : m.kind === "extinction" ? "1 3" : undefined} strokeWidth={m.kind === "event" ? 1.5 : 1}
      label={labels && m.kind !== "extinction" ? { value: m.kind === "era" ? t(m.labelKey).split(" ")[0] : "▲", position: "top", fontSize: 9, fill: "var(--ec-text-muted)" } : undefined} />
  ));
}
function SmallSeries({ h, k, color }: { h: SeriesHistory; k: Key; color: string }) {
  const data = useMemo(() => rows(h, k), [h, k]);
  return (
    <ChartFrame title={t(`series.${k}`)} summary={describeSeries(h, k)} table={<DataTable caption={t(`series.${k}`)} rows={data.filter((_, i) => i % Math.ceil(data.length / 24) === 0)} rowKey={(r) => String(r.year)} columns={[{ key: "y", header: t("common.year"), numeric: true, render: (r) => fmt(r.year) }, { key: "v", header: t(`series.${k}`), numeric: true, render: (r) => fmt(r.v, 2) }]} />}>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={data} margin={{ top: 14, right: 10, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="var(--ec-chart-grid)" strokeOpacity={0.4} vertical={false} />
          <XAxis dataKey="year" type="number" domain={["dataMin", "dataMax"]} {...AXIS} tickFormatter={(v) => fmt(v)} /><YAxis {...AXIS} domain={["auto", "auto"]} width={52} tickFormatter={(v) => fmt(v, Math.abs(v) < 10 ? 1 : 0)} />
          <Tooltip {...TIP} labelFormatter={(y) => t("hud.year", { year: fmt(Number(y)) })} formatter={(v) => [fmt(Number(v), 2), t(`series.${k}`)]} />
          {marks(h, true)}
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Time series as small multiples: one measure, one axis per chart (never two y-scales in one plot). */
export function SeriesPanel({ h, species }: { h: SeriesHistory; species: SpeciesRecord[] }) {
  const colors = useSeriesColors();
  const [log, setLog] = useState(false);
  const top = useMemo(() => Object.entries(h.populations).map(([id, v]) => ({ id, peak: Math.max(...v) })).filter((x) => x.peak > 0).sort((a, b) => b.peak - a.peak).slice(0, 6).map((x) => x.id), [h]);
  const name = (id: string) => species.find((s) => s.id === id)?.name ?? id;
  const pop = useMemo(() => h.ticks.map((tk, i) => { const r: Record<string, number> = { year: year(tk) }; for (const id of top) r[id] = log ? Math.max(0.1, h.populations[id][i]) : h.populations[id][i]; return r; }), [h, top, log]);
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-wrap gap-3 text-[length:var(--ec-text-sm)]" aria-label={t("data.series.marks")}>
        <li className="flex items-center gap-1"><svg width="22" height="10" aria-hidden="true"><line x1="0" y1="5" x2="22" y2="5" stroke="var(--ec-text-muted)" strokeDasharray="4 4" /></svg>{t("data.mark.era")}</li>
        <li className="flex items-center gap-1"><svg width="22" height="10" aria-hidden="true"><line x1="0" y1="5" x2="22" y2="5" stroke="var(--ec-warning)" strokeWidth="2" /></svg>▲ {t("data.mark.event")}</li>
        <li className="flex items-center gap-1"><svg width="22" height="10" aria-hidden="true"><line x1="0" y1="5" x2="22" y2="5" stroke="var(--ec-danger)" strokeDasharray="1 3" /></svg>{t("data.mark.extinction")}</li>
      </ul>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{(["o2", "co2", "temp", "biomass", "richness", "shannon"] as Key[]).map((k) => <SmallSeries key={k} h={h} k={k} color={colors[0]} />)}</div>
      {top.length === 0 ? <Empty icon="dna" title={t("data.noLife")} /> : (
        <ChartFrame title={t("data.series.population")} summary={t("data.series.populationSummary", { n: top.length, list: top.map(name).join(", ") })} actions={<div className="w-[220px]"><Toggle label={t("data.series.log")} checked={log} onChange={setLog} /></div>}
          table={<DataTable caption={t("data.series.population")} rows={pop.filter((_, i) => i % Math.ceil(pop.length / 20) === 0)} rowKey={(r) => String(r.year)} columns={[{ key: "y", header: t("common.year"), numeric: true, render: (r) => fmt(r.year) }, ...top.map((id) => ({ key: id, header: name(id), numeric: true, render: (r: Record<string, number>) => fmt(r[id], 0) }))]} />}>
          <ul className="mb-1 flex flex-wrap gap-x-4 gap-y-1 text-[length:var(--ec-text-sm)]" aria-label={t("legend.title")}>{top.map((id, i) => <li key={id} className="flex items-center gap-1.5"><svg width="26" height="10" aria-hidden="true"><line x1="0" y1="5" x2="26" y2="5" stroke={colors[i]} strokeWidth="3" strokeDasharray={["", "6 3", "2 2", "8 2 2 2", "1 3", "10 4"][i]} /></svg>{name(id)}</li>)}</ul>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={pop} margin={{ top: 14, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--ec-chart-grid)" strokeOpacity={0.4} vertical={false} />
              <XAxis dataKey="year" type="number" domain={["dataMin", "dataMax"]} {...AXIS} tickFormatter={(v) => fmt(v)} /><YAxis {...AXIS} scale={log ? "log" : "auto"} domain={log ? [0.1, "auto"] : [0, "auto"]} width={52} tickFormatter={(v) => fmt(v)} label={{ value: t("data.series.popUnit"), angle: -90, position: "insideLeft", fontSize: 10, fill: "var(--ec-text-muted)" }} />
              <Tooltip {...TIP} labelFormatter={(y) => t("hud.year", { year: fmt(Number(y)) })} formatter={(v, id) => [fmt(Number(v), 0), name(String(id))]} />
              {marks(h, false)}
              {top.map((id, i) => <Line key={id} type="monotone" dataKey={id} stroke={colors[i]} strokeWidth={2} strokeDasharray={["", "6 3", "2 2", "8 2 2 2", "1 3", "10 4"][i]} dot={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      )}
    </div>
  );
}

/** Energy pyramid: why the food chain has few levels (about a tenth of the energy passes to the next one). */
export function PyramidPanel({ bio }: { bio: BiosphereFrame }) {
  const colors = useSeriesColors();
  if (bio.pyramid.length === 0 || bio.richness === 0) return <Empty icon="pyramid" title={t("data.noLife")} hint={t("data.noLifeHint")} />;
  const max = Math.max(...bio.pyramid), levels = bio.pyramid.map((v, i) => ({ level: i, v, ratio: i > 0 && bio.pyramid[i - 1] > 0 ? v / bio.pyramid[i - 1] : null }));
  const summary = t("data.pyramid.summary", { levels: levels.length, list: levels.map((l) => `${t(`data.pyramid.level.${Math.min(l.level, 3)}`)}: ${fmt(l.v, 1)}`).join("; ") });
  return (
    <ChartFrame title={t("data.pyramid.title")} summary={summary} table={<DataTable caption={t("data.pyramid.title")} rows={levels} rowKey={(r) => String(r.level)} columns={[{ key: "l", header: t("codex.trophicLevel"), render: (r) => t(`data.pyramid.level.${Math.min(r.level, 3)}`) }, { key: "v", header: t("data.pyramid.energy"), numeric: true, render: (r) => fmt(r.v, 1) }, { key: "r", header: t("data.pyramid.share"), numeric: true, render: (r) => (r.ratio === null ? "—" : `${fmt(r.ratio * 100, 0)}%`) }]} />}>
      <ol className="mx-auto flex max-w-2xl flex-col-reverse gap-[2px]" data-pyramid>
        {levels.map((l) => (
          <li key={l.level} className="flex items-center gap-3">
            <span className="w-[130px] text-right text-[length:var(--ec-text-sm)]">{t(`data.pyramid.level.${Math.min(l.level, 3)}`)}</span>
            <span className="flex flex-1 justify-center"><span className="block h-9 rounded-[4px]" style={{ width: `${Math.max(0.6, (l.v / max) * 100)}%`, background: colors[0] }} title={fmt(l.v, 1)} /></span>
            <span className="ec-num w-[110px] text-[length:var(--ec-text-sm)]">{fmt(l.v, 1)}{l.ratio !== null && <span className="ec-muted"> ({fmt(l.ratio * 100, 0)}%)</span>}</span>
          </li>
        ))}
      </ol>
      <p className="ec-muted mt-2 text-center text-[length:var(--ec-text-xs)]">{t("data.pyramid.unit")}</p>
      <Ped as="p" k="ped.data.pyramid" className="mt-2" />
    </ChartFrame>
  );
}

/** Structure and diversity: flat totals do not mean that evolution stopped (principle 4). */
export function StructurePanel({ h, bio, species }: { h: SeriesHistory; bio: BiosphereFrame; species: SpeciesRecord[] }) {
  const colors = useSeriesColors();
  const rates = useMemo(() => h.ticks.map((tk, i) => ({ year: year(tk), orig: h.originations[i], ext: h.extinctions[i] })), [h]);
  const name = (id: string) => species.find((s) => s.id === id)?.name ?? id;
  return (
    <div className="flex flex-col gap-3">
      <div className="ec-card flex items-start gap-2" role="note"><Icon name="info" style={{ color: "var(--ec-info)" }} /><Ped k="ped.data.flat" /></div>
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" aria-label={t("data.structure.now")}>
        {([["data.structure.shannon", fmt(bio.shannon, 2)], ["data.structure.evenness", fmt(bio.evenness, 2)], ["series.geneticDistance", fmt(bio.geneticDistance, 2)], ["series.strategies", String(bio.metabolicStrategies)], ["report.levels", String(bio.trophicLevels)], ["data.structure.connectance", fmt(bio.connectance, 2)], ["data.structure.intransitive", `${fmt(bio.intransitiveShare * 100, 0)}%`], ["compare.lineages", String(bio.richness)]] as [string, string][]).map(([k, v]) => <li key={k} className="ec-card !p-3"><p className="ec-muted text-[length:var(--ec-text-xs)]">{t(k)}</p><p className="ec-num text-[length:var(--ec-text-xl)] font-semibold">{v}</p></li>)}
      </ul>
      <div className="grid gap-3 md:grid-cols-2">{(["biomass", "geneticDistance", "strategies", "webComplexity"] as Key[]).map((k) => <SmallSeries key={k} h={h} k={k} color={colors[0]} />)}</div>
      <ChartFrame title={t("data.structure.rates")} summary={t("data.structure.ratesSummary", { orig: fmt(bio.originationRate), ext: fmt(bio.extinctionRate), mass: bio.massExtinction ? t("data.structure.massYes") : t("data.structure.massNo") })}
        table={<DataTable caption={t("data.structure.rates")} rows={rates.filter((_, i) => i % Math.ceil(rates.length / 20) === 0)} rowKey={(r) => String(r.year)} columns={[{ key: "y", header: t("common.year"), numeric: true, render: (r) => fmt(r.year) }, { key: "o", header: t("series.originations"), numeric: true, render: (r) => fmt(r.orig) }, { key: "e", header: t("series.extinctions"), numeric: true, render: (r) => fmt(r.ext) }]} />}>
        <ul className="mb-1 flex gap-4 text-[length:var(--ec-text-sm)]" aria-label={t("legend.title")}><li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-3 w-3 rounded-sm" style={{ background: colors[2] }} />{t("series.originations")}</li><li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-3 w-3 rounded-sm" style={{ background: colors[1], backgroundImage: "repeating-linear-gradient(45deg, transparent 0 3px, var(--ec-surface) 3px 5px)" }} />{t("series.extinctions")}</li></ul>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={rates.filter((_, i) => i % Math.ceil(rates.length / 40) === 0)} margin={{ top: 10, right: 10, bottom: 0, left: -18 }} barGap={2}>
            <CartesianGrid stroke="var(--ec-chart-grid)" strokeOpacity={0.4} vertical={false} /><XAxis dataKey="year" {...AXIS} tickFormatter={(v) => fmt(v)} /><YAxis {...AXIS} allowDecimals={false} />
            <Tooltip {...TIP} cursor={{ fill: "var(--ec-surface-3)", opacity: 0.4 }} labelFormatter={(y) => t("hud.year", { year: fmt(Number(y)) })} formatter={(v, k) => [fmt(Number(v)), t(k === "orig" ? "series.originations" : "series.extinctions")]} />
            <Bar dataKey="orig" fill={colors[2]} radius={[4, 4, 0, 0]} isAnimationActive={false} /><Bar dataKey="ext" fill={colors[1]} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
      <section className="ec-card" aria-labelledby="sinais"><h3 id="sinais" className="mb-2">{t("data.structure.flags")}</h3>
        {bio.flags.length === 0 ? <p className="ec-muted">{t("data.structure.noFlags")}</p> : <ul className="flex flex-col gap-2" data-flags>{bio.flags.map((f, i) => <li key={i} className="flex flex-wrap items-center gap-2"><Chip tone={f.type === "bottleneck" ? "warning" : "info"} icon={f.type === "bottleneck" ? "down" : "flag"}>{t(`data.flag.${f.type}`)}</Chip><span>{name(f.lineageId)} · {t("hud.year", { year: fmt(year(f.tick)) })}</span><Ped k={`ped.data.flag.${f.type}`} className="ec-muted text-[length:var(--ec-text-sm)]" /></li>)}</ul>}
      </section>
    </div>
  );
}
