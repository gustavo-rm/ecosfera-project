"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { evidence, type EvidenceRecord } from "@/core/evidence/bus";
import { getMesh, latLonToDir, nearestCell } from "@/core/mesh/geodesic";
import { exportFixture, FixtureSource, importFixture } from "@/core/source/FixtureSource";
import { SyntheticSource } from "@/core/source/SyntheticSource";
import type { StateOverrides } from "@/core/source/synthetic/engine";
import { ARCHETYPE_PRESETS, SCENARIO_IDS } from "@/core/source/synthetic/scenarios";
import { DEFAULT_PARAMS, EVENT_TYPES, PARAM_DEFS } from "@/core/state/catalogs";
import { classifyRegime, regimeMetrics } from "@/core/state/metrics";
import type { PlanetParams } from "@/core/state/types";
import { fmt, fmtAuto, t } from "@/i18n";
import { perfStats, QUALITY_ORDER } from "@/render/quality";
import { useGameStore } from "@/store/gameStore";
import { setSource, snapshots, usePlanetStore } from "@/store/planetStore";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { Button, Chip, DataTable, Empty, Select, Slider, SyntheticBadge, Tabs, Toggle } from "@/ui/kit";
import { LayersPanel } from "../hud/panels";
import { PlanetStage } from "../hud/stage";
import { useHistory } from "../session/hooks";
import { SettingsForm } from "../shell/Menu";
import { download } from "../teacher/export";

type OKey = keyof StateOverrides;
/** Live sliders by family of variable. Each one drives a row of the "state variable -> effect on the planet" table. */
const FAMILIES: { id: string; params: (keyof PlanetParams)[]; overrides: [OKey, number, number, number, boolean?][] }[] = [
  { id: "relief", params: ["relief", "tectonics", "volcanism", "landDistribution", "crust"], overrides: [] },
  { id: "water", params: [], overrides: [["waterFraction", 0, 1, 0.01], ["salinityPpt", 0, 45, 0.5], ["oceanPh", 3, 11, 0.1]] },
  { id: "atmosphere", params: [], overrides: [["pressureBar", 0, 10, 0.05], ["o2Pct", 0, 35, 0.5], ["co2Ppm", 10, 100000, 10, true], ["ch4Ppm", 0.1, 5000, 0.1, true], ["aerosols", 0, 1, 0.01], ["magneticField", 0, 1, 0.01], ["starActivity", 0, 1, 0.01]] },
  { id: "climate", params: ["axialTiltDeg", "eccentricity", "dayHours"], overrides: [["tempOffset", -60, 120, 1], ["humidityScale", 0, 2, 0.05], ["yearPhase", 0, 1, 0.01], ["surfaceHeat", 0, 1, 0.01]] },
  { id: "life", params: ["soilFertility"], overrides: [["biomassScale", 0, 2, 0.05], ["fertilityScale", 0, 2, 0.05], ["richnessScale", 0, 3, 0.1], ["organicStuck", 0, 1, 0.01], ["extinctionPulse", 0, 1, 0.01]] },
  { id: "star", params: ["starType", "orbitAU", "starAgeGyr", "moons"], overrides: [] },
];

function PerfPanel() {
  const [, tick] = useState(0);
  const quality = usePlanetStore((s) => s.quality), auto = usePlanetStore((s) => s.autoQuality);
  useEffect(() => { const id = setInterval(() => tick((x) => x + 1), 500); return () => clearInterval(id); }, []);
  const rows: [string, string][] = [["frameMs", `${fmt(perfStats.frameMs, 1)} ms`], ["fps", fmt(perfStats.fps, 0)], ["worstMs", `${fmt(perfStats.worstMs, 0)} ms`], ["drawCalls", String(perfStats.drawCalls)], ["triangles", fmt(perfStats.triangles)], ["dpr", fmt(perfStats.dpr, 2)], ["geometries", String(perfStats.geometries)], ["textures", String(perfStats.textures)], ["programs", String(perfStats.programs)], ["attributeBytes", `${fmt(perfStats.attributeBytes / 1024, 0)} KiB`], ["uploads", String(perfStats.uploadsPerSecond)], ["snapshots", String(snapshots.size)]];
  return (
    <div className="flex flex-col gap-3" data-perf>
      <dl className="ec-num grid grid-cols-2 gap-x-3 gap-y-1 text-[length:var(--ec-text-sm)]">{rows.map(([k, v]) => <div key={k} className="flex justify-between gap-2 border-b border-ec-border-subtle"><dt>{t(`lab.perf.${k}`)}</dt><dd data-perf-key={k}>{v}</dd></div>)}</dl>
      <div role="radiogroup" aria-label={t("lab.perf.quality")} className="flex gap-1">{QUALITY_ORDER.map((q) => <button key={q} type="button" role="radio" aria-checked={quality === q} className="ec-btn flex-1" onClick={() => usePlanetStore.getState().set({ quality: q, autoQuality: false })} data-quality={q}>{t(`lab.perf.q.${q}`)}</button>)}</div>
      <Toggle label={t("lab.perf.auto")} checked={auto} onChange={(v) => usePlanetStore.getState().set({ autoQuality: v })} />
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("lab.perf.note")}</p>
    </div>
  );
}

/** The five regime metrics of the spec §24.4, required in development mode. */
function RegimePanel() {
  const history = useHistory(240);
  const m = useMemo(() => (history ? regimeMetrics(history) : null), [history]);
  if (!m) return <Empty title={t("state.loading")} />;
  const regime = classifyRegime(m);
  const rows: [string, string, string][] = [["dominance", fmt(m.dominance, 2), "0,15–0,45"], ["populationCV", fmt(m.populationCV, 2), "0,2–0,6"], ["extinctionsPer1000", fmt(m.extinctionsPer1000, 2), t("lab.regime.lowContinuous")], ["coexisting", String(m.coexisting), t("lab.regime.many")], ["autocorrelation", fmt(m.autocorrelation, 2), t("lab.regime.slowDecay")]];
  return (
    <div className="flex flex-col gap-2" data-regime={regime}>
      <p><Chip tone={regime === "homeochaos" ? "success" : regime === "none" ? undefined : "warning"} icon={regime === "homeochaos" ? "check" : "alert"}>{t(`lab.regime.class.${regime}`)}</Chip></p>
      <DataTable caption={t("lab.tab.regime")} rows={rows} rowKey={(r) => r[0]} columns={[{ key: "m", header: t("lab.regime.metric"), render: (r) => t(`lab.regime.${r[0]}`) }, { key: "v", header: t("common.value"), numeric: true, render: (r) => r[1] }, { key: "t", header: t("lab.regime.target"), render: (r) => r[2] }]} />
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("lab.regime.note")}</p>
    </div>
  );
}

function StatePanel() {
  const frame = usePlanetStore((s) => s.frame);
  const [log, setLog] = useState<EvidenceRecord[]>(evidence.all());
  const [msg, setMsg] = useState("");
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => evidence.subscribe(() => setLog(evidence.all())), []);
  const json = useMemo(() => (frame ? JSON.stringify({ tick: frame.tick, level: frame.level, cellCount: frame.cellCount, meta: frame.meta, globals: frame.globals, params: frame.params, events: frame.events, bio: { ...frame.bio, species: `[${frame.bio.species.length}]`, cycles: `[${frame.bio.cycles.length}]` }, fields: Object.fromEntries(Object.entries(frame.fields).map(([k, v]) => [k, v ? `${v.constructor.name}(${v.length})` : null])) }, null, 1) : ""), [frame]);
  const exportNow = () => { if (!frame) return; download(`ecosfera-fixture-${frame.meta.scenarioId}-${frame.tick}.json`, exportFixture([frame], "lab export"), "application/json"); setMsg(t("lab.state.exported", { n: 1 })); };
  const exportBuffer = () => { const frames = snapshots.ticks().map((tk) => snapshots.nearest(tk)!); if (!frames.length) return; download(`ecosfera-fixture-buffer.json`, exportFixture(frames, "lab buffer"), "application/json"); setMsg(t("lab.state.exported", { n: frames.length })); };
  const importFile = async (f: File) => { try { const frames = importFixture(await f.text()); setSource(new FixtureSource(frames)); await usePlanetStore.getState().init({ scenarioId: frames[0].meta.scenarioId, level: frames[0].level }); setMsg(t("lab.state.imported", { n: frames.length })); } catch (e) { setMsg(t("lab.state.importError", { detail: e instanceof Error ? e.message : "" })); } };
  return (
    <div className="flex flex-col gap-3" data-state-panel>
      <div className="flex flex-wrap gap-2"><Button icon="download" onClick={exportNow} data-export-fixture>{t("lab.state.export")}</Button><Button icon="download" onClick={exportBuffer}>{t("lab.state.exportBuffer")}</Button><Button icon="plus" onClick={() => file.current?.click()}>{t("lab.state.import")}</Button><Button icon="reset" onClick={() => { setSource(new SyntheticSource()); void usePlanetStore.getState().init({ scenarioId: "genesis", level: 5 }); }}>{t("lab.state.backToSynthetic")}</Button>
        <input ref={file} type="file" accept="application/json" className="ec-sr-only" aria-label={t("lab.state.import")} onChange={(e) => { const f = e.target.files?.[0]; if (f) void importFile(f); }} data-import-fixture /></div>
      <p role="status">{msg}</p>
      <h3>{t("lab.state.raw")}</h3><pre className="ec-scroll ec-num max-h-[260px] rounded-[var(--ec-radius-md)] border border-ec-border-subtle bg-ec-surface-2 p-2 text-[length:var(--ec-text-xs)]" tabIndex={0} data-raw-json>{json}</pre>
      <h3>{t("lab.state.evidence", { n: log.length })}</h3>
      {log.length === 0 ? <p className="ec-muted">{t("lab.state.noEvidence")}</p> : <pre className="ec-scroll ec-num max-h-[220px] rounded-[var(--ec-radius-md)] border border-ec-border-subtle bg-ec-surface-2 p-2 text-[length:var(--ec-text-xs)]" tabIndex={0} data-evidence-log>{log.slice(-40).reverse().map((r) => JSON.stringify(r)).join("\n")}</pre>}
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("lab.state.noTransport")}</p>
    </div>
  );
}

/** Lab console (behind the development flag): how the planet is validated while there is no backend. */
export function LabConsole() {
  const dev = useSettings((s) => s.devMode), hydrated = useSettings((s) => s.hydrated);
  const frame = usePlanetStore((s) => s.frame), info = usePlanetStore((s) => s.info), playing = usePlanetStore((s) => s.playing);
  const selected = usePlanetStore((s) => s.selectedCell);
  const revealAll = useGameStore((s) => s.revealAll);
  const [tab, setTab] = useState(() => (typeof window === "undefined" ? "scenario" : new URLSearchParams(window.location.search).get("aba") ?? "scenario")), [family, setFamily] = useState("atmosphere");
  const seq = useRef(0);
  const [scenario, setScenario] = useState("genesis"), [seed, setSeed] = useState(7), [level, setLevel] = useState(5);
  const [params, setParams] = useState<PlanetParams>({ ...DEFAULT_PARAMS }), [ov, setOv] = useState<StateOverrides>({}), [telegraph, setTelegraph] = useState(false);
  const boot = (scenarioId: string, s: number, lv: number, p: Partial<PlanetParams> = {}, tick?: number) => { setOv({}); setParams({ ...DEFAULT_PARAMS, ...p, seed: s }); return usePlanetStore.getState().init({ scenarioId, level: lv, seed: s, params: p, startTick: tick }); };
  useEffect(() => {
    if (!hydrated || !dev) return;
    const q = new URLSearchParams(window.location.search);
    usePlanetStore.getState().set({ autoRotate: false, layer: null, still: q.get("still") === "1" });
    void usePlanetStore.getState().init({ scenarioId: q.get("cenario") ?? "genesis", level: 5, seed: 7, startTick: Number(q.get("tick") ?? 12900) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, dev]);
  if (!hydrated) return null;
  if (!dev) return <main id="conteudo" className="mx-auto flex max-w-xl flex-col items-center gap-3 p-8 text-center" data-screen="lab-off"><Icon name="lock" size={36} /><h1>{t("lab.offTitle")}</h1><p>{t("lab.offBody")}</p><Link className="ec-btn ec-btn--primary" href="/">{t("app.home")}</Link></main>;
  const setOverride = (k: OKey, v: number | undefined) => { const next = { ...ov, [k]: v }; if (v === undefined) delete next[k]; setOv(next); usePlanetStore.getState().command({ type: "setOverrides", overrides: next }); };
  const setParam = (k: keyof PlanetParams, v: PlanetParams[keyof PlanetParams]) => { const next = { ...params, [k]: v }; setParams(next); usePlanetStore.getState().command({ type: "setParams", params: { [k]: v } }); };
  const fire = (type: (typeof EVENT_TYPES)[number]) => { const st = usePlanetStore.getState(), mesh = getMesh(frame?.level ?? 5), d = latLonToDir(15, 30), cell = selected ?? nearestCell(mesh, d[0], d[1], d[2]); st.command({ type: "intervene", id: `lab-${type}-${++seq.current}`, kind: "event", eventType: type, cell, noTelegraph: !telegraph }); st.focusOn(cell); if (!playing) st.setClock(true, 12); };
  const fam = FAMILIES.find((f) => f.id === family)!;
  return (
    <div className="grid h-dvh grid-rows-[auto_minmax(0,1fr)] lg:grid-cols-[430px_minmax(0,1fr)] lg:grid-rows-1" data-screen="lab">
      <aside className="ec-scroll flex flex-col gap-3 border-r border-ec-border-subtle bg-ec-surface p-3 max-lg:max-h-[50dvh]" aria-label={t("lab.title")}>
        <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="!text-[length:var(--ec-text-xl)]">{t("lab.title")}</h1><Link href="/" className="ec-btn"><Icon name="home" />{t("app.home")}</Link></div>
        <p className="flex flex-wrap items-center gap-2"><SyntheticBadge />{frame && <Chip icon="clock">{t("lab.tick", { tick: frame.tick, year: fmt(frame.globals.year), era: frame.globals.era })}</Chip>}</p>
        <Tabs label={t("lab.title")} value={tab} onChange={setTab} tabs={["scenario", "variables", "events", "perf", "regime", "state", "a11y"].map((id) => ({ id, label: t(`lab.tab.${id}`) }))} className="[&_.ec-btn]:px-2 [&_.ec-btn]:text-[length:var(--ec-text-xs)]" />
        <div role="tabpanel" aria-label={t(`lab.tab.${tab}`)} className="flex flex-col gap-3" data-tab={tab}>
          {tab === "scenario" && <>
            <Select label={t("lab.scenario")} value={scenario} onChange={(v) => { setScenario(v); void boot(v, seed, level); }} options={SCENARIO_IDS.map((s) => ({ value: s, label: t(`genesis.scenario.${s}`) }))} />
            <Slider label={t("genesis.seed")} value={seed} min={1} max={99} step={1} onChange={(v) => { const s = Math.round(v); setSeed(s); void boot(scenario, s, level, {}, frame?.tick); }} />
            <div role="radiogroup" aria-label={t("lab.level")}><span className="ec-label">{t("lab.level")}</span><div className="flex gap-1">{[3, 4, 5].map((lv) => <button key={lv} type="button" role="radio" aria-checked={level === lv} className="ec-btn flex-1" onClick={() => { setLevel(lv); void boot(scenario, seed, lv, {}, frame?.tick); }} data-level={lv}>{lv} · {fmt(10 * 4 ** lv + 2)}</button>)}</div></div>
            {frame && info && <div><label className="ec-label" htmlFor="labtime">{t("lab.time")}</label><input id="labtime" type="range" className="ec-range" min={info.startTick} max={info.endTick} step={12} value={frame.tick} onChange={(e) => usePlanetStore.getState().seek(Number(e.target.value))} data-lab-time />
              <div className="flex gap-1"><Button icon={playing ? "pause" : "play"} onClick={() => usePlanetStore.getState().setClock(!playing, 12)}>{playing ? t("time.pause") : t("time.play")}</Button><Button icon="forward" onClick={() => usePlanetStore.getState().setClock(true, 120)}>{t("time.speed.decade")}</Button><Button icon="skip" onClick={() => usePlanetStore.getState().runToEraEnd()}>{t("time.toEraEnd")}</Button></div></div>}
            <div><span className="ec-label">{t("lab.archetypes")}</span><div className="flex flex-wrap gap-1">{Object.entries(ARCHETYPE_PRESETS).map(([k, p]) => <Button key={k} onClick={() => { setScenario(p.scenarioId); void boot(p.scenarioId, p.params.seed ?? 7, level, p.params, p.tick); }} data-archetype={k}>{t(`lab.archetype.${k}`)}</Button>)}</div></div>
          </>}
          {tab === "variables" && <>
            <Tabs label={t("lab.families")} value={family} onChange={setFamily} tabs={FAMILIES.map((f) => ({ id: f.id, label: t(`lab.family.${f.id}`) }))} className="[&_.ec-btn]:px-2 [&_.ec-btn]:text-[length:var(--ec-text-xs)]" />
            {fam.params.map((k) => { const def = PARAM_DEFS.find((d) => d.key === k)!; return def.kind === "select" ? <Select key={k} label={t(`param.${k}.name`)} value={String(params[k])} onChange={(v) => setParam(k, v as never)} options={def.options!.map((o) => ({ value: o, label: t(`option.${o}`) }))} /> : <Slider key={k} label={t(`param.${k}.name`)} value={params[k] as number} min={def.min} max={def.max} step={def.step} log={def.log} onChange={(v) => setParam(k, (def.step >= 1 ? Math.round(v) : v) as never)} format={(v) => `${fmtAuto(v)} ${def.unit}`} />; })}
            {fam.overrides.map(([k, min, max, step, log]) => { const g = frame?.globals as unknown as Record<string, number> | undefined; const cur = ov[k] ?? (g && typeof g[k] === "number" ? g[k] : k === "waterFraction" ? params.waterFraction : k === "humidityScale" || k === "biomassScale" || k === "fertilityScale" || k === "richnessScale" ? 1 : 0);
              return <div key={k} className="flex items-end gap-1" data-override={k}><div className="flex-1"><Slider label={t(`lab.override.${k}`)} value={Math.min(max, Math.max(min, cur))} min={min} max={max} step={step} log={log} onChange={(v) => setOverride(k, v)} format={(v) => fmtAuto(v)} /></div><Button iconOnly icon="reset" disabled={ov[k] === undefined} onClick={() => setOverride(k, undefined)}>{t("lab.resetOverride", { name: t(`lab.override.${k}`) })}</Button></div>; })}
            <Slider label={t("hud.exaggeration")} value={usePlanetStore.getState().exaggeration} min={0.005} max={0.16} step={0.005} onChange={(v) => usePlanetStore.getState().set({ exaggeration: v })} format={(v) => `×${fmt((v * 6371) / 8, 0)}`} />
            <Button icon="reset" onClick={() => { setOv({}); usePlanetStore.getState().command({ type: "setOverrides", overrides: {} }); }}>{t("lab.resetAll")}</Button>
          </>}
          {tab === "events" && <>
            <Toggle label={t("lab.telegraph")} checked={telegraph} onChange={setTelegraph} />
            <p className="ec-muted text-[length:var(--ec-text-sm)]">{selected === null ? t("lab.eventWhereDefault") : t("lab.eventWhereSelected")}</p>
            <div className="grid grid-cols-2 gap-1">{EVENT_TYPES.map((e) => <Button key={e} icon={e} onClick={() => fire(e)} data-fire={e}>{t(`event.${e}.name`).split(" (")[0]}</Button>)}</div>
            {frame && <DataTable caption={t("lab.activeEvents")} rows={frame.events} rowKey={(e) => e.id} columns={[{ key: "t", header: t("lab.activeEvents"), render: (e) => t(`event.${e.type}.name`).split(" (")[0] }, { key: "p", header: t("lab.phase"), render: (e) => t(`lab.phase.${e.phase}`) }, { key: "i", header: "%", numeric: true, render: (e) => fmt(e.intensity * 100, 0) }, { key: "o", header: t("lab.origin"), render: (e) => t(`lab.origin.${e.origin}`) }]} />}
          </>}
          {tab === "perf" && <PerfPanel />}
          {tab === "regime" && <RegimePanel />}
          {tab === "state" && <StatePanel />}
          {tab === "a11y" && <><SettingsForm /><Toggle label={t("lab.revealAll")} checked={revealAll} onChange={(v) => useGameStore.getState().patch({ revealAll: v })} /><Toggle label={t("lab.still")} checked={usePlanetStore.getState().still} onChange={(v) => usePlanetStore.getState().set({ still: v })} /></>}
        </div>
      </aside>
      <main id="conteudo" className="relative min-h-[320px] bg-[#04060d]">
        <PlanetStage />
        <div className="pointer-events-none absolute right-2 top-2 flex max-h-[calc(100%-16px)] w-[236px]"><LayersPanel /></div>
      </main>
    </div>
  );
}
