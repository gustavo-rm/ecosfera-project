"use client";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { evidence } from "@/core/evidence/bus";
import { ARCHETYPE_PRESETS, SCENARIOS } from "@/core/source/synthetic/scenarios";
import { DEFAULT_PARAMS, DIMENSIONS, PARAM_DEFS, STAR_TABLE, type ParamDef, type ParamDimension } from "@/core/state/catalogs";
import type { PlanetParams } from "@/core/state/types";
import { PLAYER_LEVELS } from "@/game/catalog";
import { fmt, fmtAuto, t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { Icon } from "@/ui/icons";
import { Button, Chip, Ped, Select, Slider, Tabs, Toggle } from "@/ui/kit";
import { PlanetStage } from "../hud/stage";
import { StudentSession } from "../session/StudentSession";
import { StudentShell } from "../shell/Menu";

const DIM_ICON: Record<ParamDimension, string> = { astronomical: "sun", physical: "bolt", geological: "mountain", atmospheric: "wind", hydrological: "water", biological: "leaf" };
const FUTURE_TICK = 12900, START_TICK = 150;
/** PLACEHOLDER rules for the habitable zone (simplified estimate, to be reviewed by the domain authority). */
export const habitableZone = (p: PlanetParams) => { const L = STAR_TABLE[p.starType].luminosity; return { inner: Math.sqrt(L / 1.1), outer: Math.sqrt(L / 0.53) }; };
export const gravityOf = (p: PlanetParams) => p.massEarths / (p.radiusEarths * p.radiusEarths);

/** Orbit diagram with the habitable band. Position, label and text carry the meaning; color is a redundancy. */
function OrbitDiagram({ p }: { p: PlanetParams }) {
  const hz = habitableZone(p), max = Math.max(hz.outer * 1.5, p.orbitAU * 1.25), s = 92 / max, e = p.eccentricity, b = Math.sqrt(1 - e * e);
  const state = p.orbitAU < hz.inner ? "hot" : p.orbitAU > hz.outer ? "cold" : "inside";
  return (
    <figure data-hz={state}>
      <svg viewBox="-100 -100 200 200" className="mx-auto block w-full max-w-[220px]" role="img" aria-label={`${t("genesis.hz.title")}: ${t(`genesis.hz.${state}`)}. ${t("genesis.hz.caption")}`}>
        <circle r={(hz.inner + hz.outer) / 2 * s} fill="none" stroke="var(--ec-success)" strokeOpacity={0.35} strokeWidth={(hz.outer - hz.inner) * s} />
        <circle r={hz.inner * s} fill="none" stroke="var(--ec-success)" strokeDasharray="3 3" /><circle r={hz.outer * s} fill="none" stroke="var(--ec-success)" strokeDasharray="3 3" />
        <ellipse cx={-p.orbitAU * e * s} rx={p.orbitAU * s} ry={p.orbitAU * b * s} fill="none" stroke="var(--ec-text)" strokeWidth={1.5} />
        <circle r={5 + STAR_TABLE[p.starType].size * 3} fill={`rgb(${STAR_TABLE[p.starType].color.map((c) => Math.round(c * 255)).join(",")})`} />
        <circle cx={p.orbitAU * (1 - e) * s} r={5} fill="var(--ec-info)" stroke="var(--ec-text)" strokeWidth={1.5} />
      </svg>
      <figcaption className="mt-1 flex flex-col items-center gap-1 text-center text-[length:var(--ec-text-sm)]">
        <Chip tone={state === "inside" ? "success" : "warning"} icon={state === "inside" ? "check" : state === "hot" ? "fire" : "glaciation"}>{t(`genesis.hz.${state}`)}</Chip>
        <span className="ec-muted text-[length:var(--ec-text-xs)]">{t("genesis.hz.caption")}</span>
      </figcaption>
    </figure>
  );
}

function Lever({ def, p, onChange }: { def: ParamDef; p: PlanetParams; onChange: (k: keyof PlanetParams, v: PlanetParams[keyof PlanetParams]) => void }) {
  const label = t(`param.${def.key}.name`), v = p[def.key];
  if (def.kind === "toggle") return <Toggle label={label} icon="seed" checked={v as boolean} onChange={(x) => onChange(def.key, x)} />;
  if (def.kind === "select") return <Select label={label} value={String(v)} onChange={(x) => onChange(def.key, x as never)} options={def.options!.map((o) => ({ value: o, label: t(`option.${o}`) }))} />;
  return <Slider label={label} value={v as number} min={def.min} max={def.max} step={def.step} log={def.log} onChange={(x) => onChange(def.key, (def.step >= 1 ? Math.round(x) : x) as never)} format={(x) => `${def.log ? fmtAuto(x) : fmt(x, def.step >= 1 ? 0 : def.step >= 0.1 ? 1 : 2)}${def.unit ? " " + def.unit : ""}`} />;
}

/** Gênese: the planet changes live while the student moves the levers. The preview is the heart of the screen. */
export function GenesisScreen() {
  const router = useRouter();
  const level = useGameStore((s) => s.playerLevel);
  const hydrated = useGameStore((s) => s.hydrated);
  const frame = usePlanetStore((s) => s.frame);
  const [p, setP] = useState<PlanetParams>({ ...DEFAULT_PARAMS });
  const [dim, setDim] = useState<ParamDimension>("astronomical");
  const [future, setFuture] = useState(true);
  const [all, setAll] = useState(false);
  const changes = useRef<Record<string, number>>({}), timer = useRef<ReturnType<typeof setTimeout> | null>(null), ready = useRef(false);
  useEffect(() => {
    if (!hydrated) return;
    const st = usePlanetStore.getState();
    st.set({ layer: null, selectedCell: null });
    void st.init({ scenarioId: "genesis", level: 4, params: p, startTick: FUTURE_TICK }).then(() => { ready.current = true; });
    return () => { for (const [param, n] of Object.entries(changes.current)) evidence.emit({ type: "param_explored", param, changes: n }); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated]);
  const push = (next: PlanetParams) => {
    setP(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => { if (ready.current) usePlanetStore.getState().command({ type: "setParams", params: next }); }, 90);
  };
  const change = (k: keyof PlanetParams, v: PlanetParams[keyof PlanetParams]) => { changes.current[k] = (changes.current[k] ?? 0) + 1; push({ ...p, [k]: v }); };
  const g = frame?.globals, gravity = gravityOf(p);
  const warnings = useMemo(() => {
    const w: string[] = [];
    if (!g) return w;
    if (g.meanTempC > 70 && g.surfaceHeat < 0.3) w.push("boil"); if (g.iceFraction > 0.75) w.push("freeze"); if (p.pressureBar < 0.05) w.push("noAir"); if (p.waterFraction < 0.08) w.push("noWater");
    if (p.magneticField < 0.25 && p.starActivity > 0.4) w.push("noMagnet"); if (gravity > 1.8) w.push("heavy"); if (!p.lifeSeed) w.push("noSeed"); if (p.eccentricity > 0.35) w.push("eccentric"); if (p.axialTiltDeg > 45) w.push("tilt");
    return w;
  }, [g, p, gravity]);
  const start = async (scenarioId: string, params: Partial<PlanetParams>) => { await useGameStore.getState().start(scenarioId, params, params.seed); router.push("/jogo"); };
  const defs = PARAM_DEFS.filter((d) => d.dimension === dim);
  return (
    <StudentShell titleKey="genesis.title" wide>
      <StudentSession autoStart={false} passive />
      <Ped as="p" k="ped.genesis.intro" className="ec-muted mb-3" />
      <div className="grid gap-3 lg:grid-cols-[320px_minmax(0,1fr)_300px]" data-screen="genesis">
        <section className="ec-card flex flex-col gap-3" aria-labelledby="alavancas">
          <h2 id="alavancas">{t("genesis.levers")}</h2>
          <Tabs label={t("genesis.levers")} value={dim} onChange={(v) => setDim(v as ParamDimension)} tabs={DIMENSIONS.map((d) => ({ id: d, label: t(`dimension.${d}`), icon: DIM_ICON[d] }))} className="[&_.ec-btn]:px-2 [&_.ec-btn]:text-[length:var(--ec-text-xs)]" />
          <div role="tabpanel" aria-label={t(`dimension.${dim}`)} className="flex flex-col gap-3">
            {defs.map((d) => (d.minLevel <= level || all ? <Lever key={d.key} def={d} p={p} onChange={change} /> : <p key={d.key} className="ec-muted flex items-center gap-2 text-[length:var(--ec-text-sm)]"><Icon name="lock" size={16} />{t(`param.${d.key}.name`)} · {t("genesis.locked", { level: t(`level.${PLAYER_LEVELS[d.minLevel]}`) })}</p>))}
            {dim === "physical" && <><p className="ec-num">{t("genesis.derived.gravity")}: {fmt(gravity, 2)} g</p><Ped as="p" k="ped.genesis.coupling.gravity" className="ec-muted text-[length:var(--ec-text-sm)]" /><Ped as="p" k="ped.genesis.coupling.magnet" className="ec-muted text-[length:var(--ec-text-sm)]" /></>}
            {dim === "astronomical" && <Ped as="p" k="ped.genesis.coupling.tilt" className="ec-muted text-[length:var(--ec-text-sm)]" />}
          </div>
          <Button variant="ghost" icon={all ? "minus" : "plus"} aria-pressed={all} onClick={() => setAll(!all)}>{all ? t("genesis.lessLevers") : t("genesis.moreLevers")}</Button>
          <Slider label={t("genesis.seed")} value={p.seed} min={1} max={99} step={1} onChange={(v) => change("seed", Math.round(v))} />
          <Button icon="reset" onClick={() => push({ ...DEFAULT_PARAMS })}>{t("genesis.reset")}</Button>
        </section>
        <section className="flex flex-col gap-2" aria-label={t("genesis.preview")}>
          <div className="relative h-[46vh] min-h-[300px] overflow-hidden rounded-[var(--ec-radius-lg)] border border-ec-border-subtle bg-[#04060d] lg:h-[calc(100dvh-300px)]"><PlanetStage /></div>
          <div className="flex flex-wrap items-center gap-2">
            <div role="group" aria-label={t("genesis.preview")} className="flex gap-1">
              <Button aria-pressed={future} onClick={() => { setFuture(true); usePlanetStore.getState().seek(FUTURE_TICK); }}>{t("genesis.preview.future")}</Button>
              <Button aria-pressed={!future} onClick={() => { setFuture(false); usePlanetStore.getState().seek(START_TICK); }}>{t("genesis.preview.start")}</Button>
            </div>
            {g && <Chip icon="globe">{t(`archetype.${g.archetype}`)}</Chip>}
            <Button variant="primary" large icon="play" className="ml-auto" onClick={() => void start("genesis", p)} data-start>{t("genesis.start")}</Button>
          </div>
        </section>
        <div className="flex flex-col gap-3">
          <section className="ec-card" aria-labelledby="hz"><h2 id="hz" className="mb-2">{t("genesis.hz.title")}</h2><OrbitDiagram p={p} /></section>
          <section className="ec-card" aria-labelledby="alertas" aria-live="polite">
            <h2 id="alertas" className="mb-2">{t("genesis.warnings")}</h2>
            {warnings.length === 0 ? <p className="flex items-start gap-2"><Icon name="check" style={{ color: "var(--ec-success)" }} />{t("genesis.noWarnings")}</p>
              : <ul className="flex flex-col gap-2" data-warnings>{warnings.map((w) => <li key={w} className="flex items-start gap-2"><Icon name="alert" style={{ color: "var(--ec-warning)" }} /><Ped k={`ped.genesis.warn.${w}`} /></li>)}</ul>}
            {g && <dl className="ec-num mt-3 grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]"><dt>{t("genesis.derived.temp")}</dt><dd>{fmt(Math.min(g.meanTempC, 9999), 0)} °C</dd><dt>{t("genesis.derived.ocean")}</dt><dd>{fmt(g.oceanFraction * 100, 0)} %</dd><dt>{t("genesis.derived.flux")}</dt><dd>{fmt(g.starFlux * 1361, 0)} W/m²</dd></dl>}
          </section>
          <section className="ec-card" aria-labelledby="partida">
            <h2 id="partida" className="mb-2">{t("genesis.presets")}</h2>
            <div className="flex flex-wrap gap-1">{(["terra", "ocean", "desert", "snowball", "greenhouse", "airless"] as const).map((k) => <Button key={k} onClick={() => push({ ...DEFAULT_PARAMS, ...ARCHETYPE_PRESETS[k].params })} data-preset={k}>{t(`genesis.preset.${k}`)}</Button>)}</div>
            <h3 className="mb-1 mt-3">{t("genesis.scenarios")}</h3>
            <ul className="flex flex-col gap-2">{Object.keys(SCENARIOS).map((id) => <li key={id}><button type="button" className="ec-btn h-auto w-full flex-col !items-start py-2 text-left" onClick={() => void start(id, {})} data-scenario={id}><span>{t(`genesis.scenario.${id}`)}</span><Ped k={`ped.genesis.scenario.${id}`} className="ec-muted text-[length:var(--ec-text-xs)] font-normal" /></button></li>)}</ul>
          </section>
        </div>
      </div>
    </StudentShell>
  );
}
