"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BASE_LAYERS, LAYER_BY_ID, LAYERS, type LayerId } from "@/core/appearance/layers";
import { evidence } from "@/core/evidence/bus";
import { getMesh } from "@/core/mesh/geodesic";
import { INTERVENTIONS, MISSIONS, RESOURCES, type InterventionDef } from "@/game/catalog";
import { fmt, t } from "@/i18n";
import { cameraApi } from "@/render/CameraRig";
import { MAX_AP, useGameStore, type Notice } from "@/store/gameStore";
import { SPEEDS, snapshots, usePlanetStore } from "@/store/planetStore";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { Button, Chip, Meter, Panel, Ped, Select, SyntheticBadge, Trend } from "@/ui/kit";
import { useHistory, usePastFrame, yearsLabel } from "../session/hooks";
import { LayerLegend } from "./stage";

const LAYER_ICON: Record<string, string> = { temperature: "thermometer", biome: "tree", population: "footprint", water: "water", precipitation: "storm", elevation: "mountain", fertility: "seed", biomass: "leaf", richness: "dna", habitat: "eye", o2: "oxygen", co2: "wind", mineral: "mountain", nitrogen: "cycle", organicMatter: "bone", disturbance: "alert", salinity: "water", ph: "ph" };

function Segments({ value, label }: { value: number; label: string }) {
  const filled = Math.round(Math.min(1, Math.max(0, value)) * 5);
  return (
    <span role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={5} aria-valuenow={filled} aria-valuetext={t("hud.segments", { filled })} className="inline-flex gap-[2px]">
      {[0, 1, 2, 3, 4].map((i) => <span key={i} aria-hidden="true" className="inline-block h-3 w-2 rounded-[2px] border border-ec-border" style={{ background: i < filled ? "var(--ec-primary)" : "transparent" }} />)}
    </span>
  );
}
function Indicator({ icon, label, value, delta, children, word }: { icon: string; label: string; value?: string; delta: number; children?: React.ReactNode; word?: string }) {
  return (
    <li className="flex flex-none items-center gap-1.5 rounded-[var(--ec-radius-md)] border border-ec-border-subtle bg-ec-surface-2 px-2 py-1" title={label}>
      <Icon name={icon} />
      <span className="flex flex-col leading-tight">
        <span className="ec-muted text-[length:var(--ec-text-xs)]">{label}{word ? ` · ${word}` : ""}</span>
        <span className="ec-num flex items-center gap-1 font-semibold">{value}{children}<Trend delta={delta} /></span>
      </span>
    </li>
  );
}

/** Era name and the five key indicators, each with icon, value and trend arrow (GDD §13). */
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const past = usePastFrame(240);
  const dev = useSettings((s) => s.devMode);
  if (!frame) return null;
  const g = frame.globals, p = past?.globals ?? g;
  const tempWord = g.meanTempC < 0 ? t("hud.cold") : g.meanTempC > 45 ? t("hud.hot") : t("hud.mild");
  return (
    <header className="ec-panel pointer-events-auto flex flex-wrap items-center gap-2 !rounded-none !border-x-0 !border-t-0 px-3 py-1.5 lg:flex-nowrap">
      <Link href="/" className="ec-display flex items-center gap-2 font-bold tracking-wide" aria-label={t("app.home")}><Icon name="globe" style={{ color: "var(--ec-primary)" }} /><span className="hidden lg:inline">ECOSFERA</span></Link>
      <div className="flex flex-none flex-col leading-tight" data-era>
        <span className="ec-display font-semibold">{t("hud.era", { n: g.era })} · {t(`era.${g.era}.name`)}</span>
        <span className="ec-muted ec-num text-[length:var(--ec-text-xs)]">{t("hud.year", { year: fmt(g.year) })}</span>
      </div>
      <ul className="ec-scroll mx-auto flex min-w-0 max-w-full flex-1 gap-1.5 lg:justify-center" aria-label={t("hud.indicators")}>
        <Indicator icon="thermometer" label={t("hud.temperature")} value={`${fmt(Math.min(g.meanTempC, 9999), 0)} °C`} delta={(g.meanTempC - p.meanTempC) / 20} word={tempWord} />
        <Indicator icon="oxygen" label="O₂" value={`${fmt(g.o2Pct, 1)} %`} delta={(g.o2Pct - p.o2Pct) / 5} />
        <Indicator icon="ph" label="pH" value={fmt(g.oceanPh, 1)} delta={(g.oceanPh - p.oceanPh) * 2} />
        <Indicator icon="leaf" label={t("hud.biodiversity")} delta={g.biodiversity - p.biodiversity}><Segments value={g.biodiversity} label={t("hud.biodiversity")} /></Indicator>
        <Indicator icon="spark" label={t("hud.prosperity")} delta={g.prosperity - p.prosperity}><Segments value={g.prosperity} label={t("hud.prosperity")} /></Indicator>
      </ul>
      <div className="flex flex-none items-center gap-1.5">
        <Chip tone={frame.meta.mode === "fast" ? "warning" : undefined} icon={frame.meta.mode === "fast" ? "forward" : "eye"}>{t(`hud.mode.${frame.meta.mode}`)}</Chip>
        {frame.meta.synthetic && <SyntheticBadge compact />}
        {dev && <Link href="/lab" className="ec-btn" aria-label={t("nav.lab")}><Icon name="flask" /></Link>}
        <Button iconOnly icon="menu" onClick={onMenu}>{t("nav.menu")}</Button>
      </div>
    </header>
  );
}

function CostChips({ def }: { def: InterventionDef }) {
  const res = useGameStore((s) => s.resources);
  return (
    <span className="flex flex-wrap gap-1">
      {Object.entries(def.cost).map(([k, v]) => { const r = RESOURCES.find((x) => x.id === k)!; const short = res[r.id] < (v ?? 0); return <span key={k} className={`ec-chip ${short ? "ec-chip--danger" : ""}`} title={t(`resource.${k}`)}><Icon name={r.icon} size={12} /><span className="ec-num">{v}</span><span className="ec-sr-only">{t(`resource.${k}`)}{short ? `, ${t("intervention.short")}` : ""}</span></span>; })}
    </span>
  );
}

/** Actions on the left, with the action points that remain. Locked actions name the concept that is missing. */
export function ActionsPanel({ onPick }: { onPick: (id: string) => void }) {
  const res = useGameStore((s) => s.resources);
  const unlocked = useGameStore((s) => s.unlocked);
  const cooldowns = useGameStore((s) => s.cooldowns);
  const tick = usePlanetStore((s) => s.frame?.tick ?? 0);
  const era = usePlanetStore((s) => s.frame?.globals.era ?? 1);
  return (
    <Panel as="aside" title={t("hud.actions", { left: res.actionPoints, max: MAX_AP })} icon="bolt" className="pointer-events-auto flex max-h-full flex-col">
      <ul className="mb-2 grid grid-cols-3 gap-1 text-[length:var(--ec-text-xs)]" aria-label={t("hud.resources")}>
        {RESOURCES.filter((r) => r.id !== "actionPoints" && r.id !== "influence").map((r) => <li key={r.id} className="flex items-center gap-1" title={t(`resource.${r.id}`)}><Icon name={r.icon} size={14} /><span className="ec-num">{fmt(res[r.id])}</span><span className="ec-sr-only">{t(`resource.${r.id}`)}</span></li>)}
      </ul>
      <ul className="ec-scroll -mr-1 flex flex-col gap-1 pr-1">
        {INTERVENTIONS.map((def) => {
          const locked = def.requires && !unlocked.includes(def.requires), early = era < def.minEra, wait = (cooldowns[def.id] ?? 0) - tick;
          return (
            <li key={def.id}>
              <button type="button" className="ec-btn h-auto w-full !justify-start gap-2 py-1.5 text-left" onClick={() => onPick(def.id)} data-intervention={def.id}>
                <Icon name={locked || early ? "lock" : def.icon} />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span>{t(`intervention.${def.id}.name`)}</span>
                  {locked ? <span className="ec-muted text-[length:var(--ec-text-xs)] font-normal">{t("intervention.needsConcept", { concept: t(`research.${def.requires}.name`) })}</span>
                    : early ? <span className="ec-muted text-[length:var(--ec-text-xs)] font-normal">{t("intervention.needsEra", { era: def.minEra })}</span>
                    : wait > 0 ? <span className="ec-muted text-[length:var(--ec-text-xs)] font-normal">{t("intervention.cooldownLeft", { years: Math.ceil(wait / 12) })}</span>
                    : <CostChips def={def} />}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

/** Data layers on the right (RF-054). Layers that need research show which concept reveals them. */
export function LayersPanel() {
  const layer = usePlanetStore((s) => s.layer);
  const exaggeration = usePlanetStore((s) => s.exaggeration);
  const showClouds = usePlanetStore((s) => s.showClouds);
  const unlocked = useGameStore((s) => s.unlocked);
  const revealAll = useGameStore((s) => s.revealAll);
  const [more, setMore] = useState(false);
  const pick = (id: LayerId | null) => {
    usePlanetStore.getState().setLayer(id);
    if (id) { evidence.emit({ type: "layer_viewed", layer: id }); const g = useGameStore.getState(); if (!g.stats.layersViewed.includes(id)) g.patch({ stats: { ...g.stats, layersViewed: [...g.stats.layersViewed, id] } }); }
  };
  const list = more ? LAYERS : LAYERS.filter((l) => BASE_LAYERS.includes(l.id) || l.id === layer);
  return (
    <Panel as="aside" title={t("hud.layers")} icon="layers" className="pointer-events-auto flex max-h-full flex-col">
      <ul className="ec-scroll -mr-1 flex flex-col gap-1 pr-1">
        <li><button type="button" className="ec-btn w-full !justify-start" aria-pressed={layer === null} onClick={() => pick(null)}><Icon name="globe" />{t("layer.natural")}</button></li>
        {list.map((l) => {
          const locked = !!l.requires && !unlocked.includes(l.requires) && !revealAll;
          return (
            <li key={l.id}>
              <button type="button" className="ec-btn h-auto w-full !justify-start py-1 text-left" aria-pressed={layer === l.id} aria-disabled={locked} onClick={() => !locked && pick(l.id)} data-layer={l.id}>
                <Icon name={locked ? "lock" : LAYER_ICON[l.id]} />
                <span className="flex flex-col"><span>{t(`layer.${l.id}.name`)}</span>{locked && <span className="ec-muted text-[length:var(--ec-text-xs)] font-normal">{t("layer.needs", { concept: t(`research.${l.requires}.name`) })}</span>}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <Button variant="ghost" icon={more ? "minus" : "plus"} onClick={() => setMore(!more)} aria-expanded={more}>{more ? t("hud.fewerLayers") : t("hud.moreLayers")}</Button>
      <div className="mt-2 border-t border-ec-border-subtle pt-2"><LayerLegend /></div>
      <div className="mt-2 border-t border-ec-border-subtle pt-2">
        <label className="ec-label" htmlFor="exag">{t("hud.exaggeration")} <span className="ec-num">×{fmt((exaggeration * 6371) / 8, 0)}</span></label>
        <input id="exag" type="range" className="ec-range" min={0.005} max={0.16} step={0.005} value={exaggeration} onChange={(e) => usePlanetStore.getState().set({ exaggeration: Number(e.target.value) })} />
        <button type="button" role="switch" aria-checked={showClouds} className="ec-btn w-full !justify-between" onClick={() => usePlanetStore.getState().set({ showClouds: !showClouds })}><span className="flex items-center gap-2"><Icon name="storm" />{t("hud.clouds")}</span><span className="ec-chip" aria-hidden="true">{showClouds ? t("common.on") : t("common.off")}</span></button>
      </div>
    </Panel>
  );
}

/** Time control: the student sees eras and years, never ticks. Dragging the timeline shows the planet in the past (RF-059). */
export function TimeBar({ onTutor, onMissions }: { onTutor: () => void; onMissions: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const info = usePlanetStore((s) => s.info);
  const playing = usePlanetStore((s) => s.playing);
  const speed = usePlanetStore((s) => s.speed);
  const compareTick = usePlanetStore((s) => s.compareTick);
  const history = useHistory(120);
  const maxTick = usePlanetStore((s) => s.maxTick);
  const missionsDone = useGameStore((s) => s.missionsDone);
  const stats = useGameStore((s) => s.stats);
  const current = useMemo(() => {
    if (!frame) return null;
    const open = MISSIONS.filter((x) => !missionsDone.includes(x.id));
    const m = open.filter((x) => x.era === frame.globals.era)[0] ?? open.filter((x) => x.era < frame.globals.era).pop() ?? open[0];
    return m ? { id: m.id, progress: m.progress(frame, stats) } : null;
  }, [frame, missionsDone, stats]);
  if (!frame || !info) return null;
  const st = usePlanetStore.getState(), g = frame.globals, end = Math.max(maxTick, info.startTick + 1), span = end - info.startTick;
  const marks = (history?.marks ?? []).filter((m) => m.tick <= end && m.kind !== "speciation");
  const seek = (v: number) => { if (playing) st.setClock(false); evidence.emit({ type: "timeline_scrubbed", fromTick: frame.tick, toTick: v }); st.seek(v); };
  return (
    <footer className="ec-panel pointer-events-auto flex flex-wrap items-center gap-x-3 gap-y-1 !rounded-none !border-x-0 !border-b-0 px-3 py-2">
      <div className="flex items-center gap-1" role="group" aria-label={t("time.controls")}>
        <Button large iconOnly variant="primary" icon={playing ? "pause" : "play"} onClick={() => st.setClock(!playing)} data-play>{playing ? t("time.pause") : t("time.play")}</Button>
        <Select label={t("time.speed")} hideLabel value={String(speed)} onChange={(v) => st.setClock(playing, Number(v))} options={SPEEDS.map((s) => ({ value: String(s.ticksPerSecond), label: t(`time.speed.${s.id}`) }))} />
        <Button icon="skip" onClick={() => st.runToEraEnd()} disabled={frame.tick >= g.eraEndTick} title={t("time.toEraEndHint")}><span className="hidden xl:inline">{t("time.toEraEnd")}</span></Button>
      </div>
      <div className="relative min-w-[180px] flex-1">
        <div className="relative h-4" aria-hidden="true">
          {marks.map((m, i) => (
            <span key={i} title={`${t(m.labelKey, m.labelParams)} · ${t("hud.year", { year: yearsLabel(m.tick) })}`} className="absolute top-0 -translate-x-1/2" style={{ left: `${((m.tick - info.startTick) / span) * 100}%`, color: m.kind === "extinction" ? "var(--ec-danger)" : m.kind === "event" ? "var(--ec-warning)" : m.kind === "intervention" ? "var(--ec-info)" : "var(--ec-text-muted)" }}>
              <Icon size={12} name={m.kind === "era" ? "flag" : m.kind === "event" ? "alert" : m.kind === "extinction" ? "close" : "bolt"} />
            </span>
          ))}
        </div>
        <label htmlFor="timeline" className="ec-sr-only">{t("time.timeline")}</label>
        <input id="timeline" type="range" className="ec-range !h-7" min={info.startTick} max={end} step={12} value={Math.min(frame.tick, end)} onChange={(e) => seek(Number(e.target.value))}
          aria-valuetext={t("time.position", { era: t(`era.${g.era}.name`), year: fmt(g.year) })} data-timeline />
        <ul className="ec-sr-only">{marks.map((m, i) => <li key={i}>{t(m.labelKey, m.labelParams)}, {t("hud.year", { year: yearsLabel(m.tick) })}</li>)}</ul>
      </div>
      <Button icon="compare" aria-pressed={compareTick !== null} onClick={() => st.set({ compareTick: compareTick === null ? frame.tick : null })} title={t("time.compareHint")}><span className="hidden xl:inline">{t("time.compare")}</span></Button>
      {current && (
        <button type="button" className="ec-btn h-auto max-w-[240px] flex-col !items-stretch gap-1 py-1 text-left" onClick={onMissions} data-mission>
          <span className="flex items-center gap-2"><Icon name="target" size={16} /><span className="truncate">{t(`mission.${current.id}.name`)}</span></span>
          <Meter value={current.progress} label={t("mission.progress")} />
        </button>
      )}
      <Button variant="primary" icon="chat" onClick={onTutor} data-tutor>{t("tutor.open")}</Button>
    </footer>
  );
}

/** Before/after comparison tied to the timeline: pin a moment, move in time, read the differences. */
export function ComparePanel() {
  const compareTick = usePlanetStore((s) => s.compareTick);
  const frame = usePlanetStore((s) => s.frame);
  const version = usePlanetStore((s) => s.bufferVersion);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const pinned = useMemo(() => (compareTick === null ? null : snapshots.nearest(compareTick)), [compareTick, version]);
  if (compareTick === null || !frame || !pinned) return null;
  const a = pinned.globals, b = frame.globals;
  const rows: [string, number, number, number][] = [[t("hud.temperature") + " (°C)", a.meanTempC, b.meanTempC, 1], ["O₂ (%)", a.o2Pct, b.o2Pct, 1], ["CO₂ (ppm)", a.co2Ppm, b.co2Ppm, 0], [t("compare.ice") + " (%)", a.iceFraction * 100, b.iceFraction * 100, 0], [t("compare.ocean") + " (%)", a.oceanFraction * 100, b.oceanFraction * 100, 0], [t("compare.lineages"), pinned.bio.richness, frame.bio.richness, 0]];
  return (
    <Panel title={t("compare.title")} icon="compare" className="pointer-events-auto w-[300px] max-w-full" headingLevel={3}>
      <table className="ec-table">
        <thead><tr><th scope="col">{t("compare.variable")}</th><th scope="col" className="ec-num">{t("compare.before", { year: fmt(a.year) })}</th><th scope="col" className="ec-num">{t("compare.after", { year: fmt(b.year) })}</th></tr></thead>
        <tbody>{rows.map(([label, x, y, d]) => <tr key={label}><th scope="row">{label}</th><td className="ec-num">{fmt(Math.min(x, 9999), d)}</td><td className="ec-num">{fmt(Math.min(y, 9999), d)} <Trend delta={(y - x) / Math.max(1, Math.abs(x))} threshold={0.01} /></td></tr>)}</tbody>
      </table>
      <div className="mt-2 flex gap-2">
        <Button icon="eye" onClick={() => { const st = usePlanetStore.getState(); st.setClock(false); const back = frame.tick; st.seek(pinned.tick); st.set({ compareTick: back }); }}>{t("compare.swap")}</Button>
      </div>
    </Panel>
  );
}

/** Short, actionable notifications ("Alga floresceu! Investigar"). They never block the game. */
export function Notices({ onAction }: { onAction: (n: Notice) => void }) {
  const notices = useGameStore((s) => s.notices);
  return (
    <ul className="pointer-events-auto flex w-[min(440px,100%)] flex-col gap-1" aria-label={t("notice.region")} data-notices>
      {notices.slice(-3).map((n) => (
        <li key={n.id} className="ec-panel flex items-center gap-2 px-3 py-1.5">
          <Icon name={n.icon} style={{ color: `var(--ec-${n.tone})` }} />
          <span className="flex-1 text-[length:var(--ec-text-sm)]">{t(n.key, expandParams(n.params))}</span>
          {n.action && <Button onClick={() => onAction(n)}>{t(`notice.action.${n.action.type}`)}</Button>}
          <Button variant="ghost" iconOnly icon="close" onClick={() => useGameStore.getState().dismiss(n.id)}>{t("common.dismiss")}</Button>
        </li>
      ))}
    </ul>
  );
}
/** Notice params carry ids; names are resolved here so that text stays in the message files. */
export function expandParams(p?: Record<string, string | number>): Record<string, string | number> | undefined {
  if (!p) return p;
  const out = { ...p };
  if (typeof p.name === "string" && ["fire", "drought", "storm", "glaciation", "volcanism", "impact", "eutrophication", "pandemic", "invasive"].includes(p.name)) out.name = t(`event.${p.name}.name`);
  if (typeof p.instrument === "string") out.instrument = t(`instrument.${p.instrument}`);
  if (typeof p.variable === "string") out.variable = t(`predict.var.${p.variable}`);
  if (typeof p.era === "number") out.eraName = t(`era.${p.era}.name`);
  if (typeof p.id === "string") out.title = t(p.id.includes(".") ? p.id : `mission.${p.id}.name`);
  return out;
}

/** Collapsible chart of one series (O₂ along the eras, by default). Opening it before acting is recorded as evidence. */
export function MiniChart() {
  const [open, setOpen] = useState(false);
  const [series, setSeries] = useState<"o2" | "co2" | "temp" | "biomass" | "richness">("o2");
  const history = useHistory(120);
  const toggle = () => {
    if (!open) { const g = useGameStore.getState(), tick = usePlanetStore.getState().frame?.tick ?? 0; evidence.emit({ type: "chart_opened", chart: `mini:${series}`, ticksSinceLastAction: tick - g.lastActionTick }); g.patch({ stats: { ...g.stats, chartsOpened: g.stats.chartsOpened + 1 } }); }
    setOpen(!open);
  };
  const data = useMemo(() => (history ? history.ticks.map((tk, i) => ({ year: Math.floor(tk / 12), v: history[series][i] })) : []), [history, series]);
  const last = data[data.length - 1], first = data[0];
  return (
    <Panel className="pointer-events-auto w-[300px] max-w-full" headingLevel={3}>
      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" icon="chart" aria-expanded={open} onClick={toggle} data-minichart>{t("hud.chart", { series: t(`series.${series}`) })}</Button>
        {open && <Select label={t("hud.chartSeries")} hideLabel value={series} onChange={setSeries} options={(["o2", "co2", "temp", "biomass", "richness"] as const).map((s) => ({ value: s, label: t(`series.${s}`) }))} />}
      </div>
      {open && (data.length < 2 ? <p className="ec-muted p-2 text-[length:var(--ec-text-sm)]">{t("chart.noData")}</p> : (
        <div role="img" aria-label={t("chart.summaryRange", { series: t(`series.${series}`), from: fmt(first.v, 1), to: fmt(last.v, 1), y0: fmt(first.year), y1: fmt(last.year) })}>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
              <XAxis dataKey="year" tick={{ fontSize: 10, fill: "var(--ec-text-muted)" }} stroke="var(--ec-border)" />
              <YAxis tick={{ fontSize: 10, fill: "var(--ec-text-muted)" }} stroke="var(--ec-border)" domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ background: "var(--ec-surface)", border: "1px solid var(--ec-border)", color: "var(--ec-text)" }} labelFormatter={(y) => t("hud.year", { year: y })} formatter={(v) => [fmt(Number(v), 1), t(`series.${series}`)]} />
              <Line type="monotone" dataKey="v" stroke="var(--ec-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
    </Panel>
  );
}

/** Probe: values of the cell under the cursor or the selected cell (RF-054), with focus and regional panel. */
export function RegionProbe({ onRegion }: { onRegion: (cell: number) => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const selected = usePlanetStore((s) => s.selectedCell);
  const hovered = usePlanetStore((s) => s.hoveredCell);
  const layer = usePlanetStore((s) => s.layer);
  const cell = selected ?? hovered;
  if (!frame || cell === null || cell >= frame.cellCount) return null;
  const mesh = getMesh(frame.level), f = frame.fields, def = layer ? LAYER_BY_ID[layer] : null;
  return (
    <Panel title={selected !== null ? t("probe.selected") : t("probe.hover")} icon="search" className="pointer-events-auto w-[260px] max-w-full" headingLevel={3}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[length:var(--ec-text-sm)]" data-probe>
        <dt className="ec-muted">{t("probe.position")}</dt><dd className="ec-num">{fmt(mesh.latitude[cell], 0)}°, {fmt(mesh.longitude[cell], 0)}°</dd>
        <dt className="ec-muted">{t("layer.biome.name")}</dt><dd>{t(`biome.${f.biome[cell]}`)}</dd>
        <dt className="ec-muted">{t("layer.temperature.name")}</dt><dd className="ec-num">{fmt(Math.min(f.temperature[cell], 9999), 0)} °C</dd>
        <dt className="ec-muted">{t("layer.elevation.name")}</dt><dd className="ec-num">{fmt(f.elevation[cell] - (frame.globals.seaLevelM < -9e4 ? 0 : frame.globals.seaLevelM), 0)} m</dd>
        {def && def.kind !== "categorical" && <><dt className="ec-muted">{t(`layer.${def.id}.name`)}</dt><dd className="ec-num font-semibold">{fmt(def.value(f, cell, frame), def.max <= 3 ? 2 : 0)} {def.unit}</dd></>}
      </dl>
      {selected !== null && (
        <div className="mt-2 flex flex-wrap gap-1">
          <Button icon="eye" onClick={() => usePlanetStore.getState().focusOn(selected)}>{t("probe.focus")}</Button>
          <Button icon="table" onClick={() => onRegion(selected)} data-region>{t("probe.region")}</Button>
          <Button variant="ghost" iconOnly icon="close" onClick={() => usePlanetStore.getState().selectCell(null)}>{t("probe.clear")}</Button>
        </div>
      )}
    </Panel>
  );
}

/** Camera buttons for touch and for people who prefer buttons to gestures. */
export function CameraButtons() {
  const autoRotate = usePlanetStore((s) => s.autoRotate);
  return (
    <div className="pointer-events-auto flex flex-col gap-1" role="group" aria-label={t("camera.controls")}>
      <Button iconOnly icon="plus" onClick={() => cameraApi.zoom(0.8)}>{t("camera.zoomIn")}</Button>
      <Button iconOnly icon="minus" onClick={() => cameraApi.zoom(1.25)}>{t("camera.zoomOut")}</Button>
      <Button iconOnly icon="reset" onClick={() => cameraApi.reset()}>{t("camera.reset")}</Button>
      <Button iconOnly icon="cycle" aria-pressed={autoRotate} onClick={() => usePlanetStore.getState().set({ autoRotate: !autoRotate })}>{t("camera.autoRotate")}</Button>
    </div>
  );
}

const STEPS = ["rotate", "play", "layer", "select", "scan", "tutor"] as const;
/** First use: learning by doing, one hint at a time, each one completed by the action itself. */
export function Onboarding() {
  const step = useGameStore((s) => s.onboarding);
  const playing = usePlanetStore((s) => s.playing);
  const layer = usePlanetStore((s) => s.layer);
  const selected = usePlanetStore((s) => s.selectedCell);
  const scans = useGameStore((s) => s.stats.scans);
  const questions = useGameStore((s) => s.stats.tutorQuestions);
  const tick = usePlanetStore((s) => s.frame?.tick ?? 0);
  const [moved, setMoved] = useState(false);
  useEffect(() => { const h = () => setMoved(true); window.addEventListener("pointerup", h); window.addEventListener("keyup", h); return () => { window.removeEventListener("pointerup", h); window.removeEventListener("keyup", h); }; }, []);
  const done = [moved && step === 0, playing || tick > 24, layer !== null, selected !== null, scans > 0, questions > 0];
  useEffect(() => { if (step >= 0 && step < STEPS.length && done[step]) useGameStore.getState().patch({ onboarding: step + 1 >= STEPS.length ? -1 : step + 1 }); });
  if (step < 0 || step >= STEPS.length) return null;
  return (
    <div className="ec-panel pointer-events-auto flex max-w-[460px] items-center gap-3 px-3 py-2" role="status" data-onboarding={STEPS[step]}>
      <Icon name="info" style={{ color: "var(--ec-info)" }} />
      <div className="flex-1"><p className="ec-muted text-[length:var(--ec-text-xs)]">{t("onboarding.step", { n: step + 1, total: STEPS.length })}</p><Ped as="p" k={`ped.onboarding.${STEPS[step]}`} /></div>
      <Button variant="ghost" onClick={() => useGameStore.getState().patch({ onboarding: -1 })}>{t("onboarding.skip")}</Button>
    </div>
  );
}
