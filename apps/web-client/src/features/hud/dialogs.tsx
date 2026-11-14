"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { evidence } from "@/core/evidence/bus";
import { getMesh } from "@/core/mesh/geodesic";
import { EVENT_DEFS } from "@/core/state/catalogs";
import type { PlanetEvent } from "@/core/state/types";
import { INTERVENTION_BY_ID, RESOURCES, type PredictVar } from "@/game/catalog";
import { answerQuestion, QUICK_QUESTIONS, streamText, type QuestionId, type TutorAnswer } from "@/game/tutor";
import { fmt, t } from "@/i18n";
import { cameraApi } from "@/render/CameraRig";
import { useGameStore, type Direction } from "@/store/gameStore";
import { snapshots, usePlanetStore } from "@/store/planetStore";
import { Icon } from "@/ui/icons";
import { Button, Chip, DataTable, Dialog, Ped, Select, SyntheticBadge } from "@/ui/kit";
import { useHistory, usePastFrame, useReducedMotion, yearsLabel } from "../session/hooks";
import { expandParams } from "./panels";

/** Causal chain as linked steps (vulcão → aerossóis → resfriamento → ...). */
export function CausalChain({ steps }: { steps: string[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-1" aria-label={t("why.chain")} data-chain>
      {steps.map((k, i) => (
        <li key={k} className="flex items-center gap-1">
          {i > 0 && <Icon name="flat" size={16} className="ec-muted" />}
          <span className="ec-chip !min-h-[32px] !text-[length:var(--ec-text-sm)]"><Ped k={k} /></span>
        </li>
      ))}
    </ol>
  );
}

/** Intervention card: gain and cost shown BEFORE confirming, the optional prediction panel, and never a free choice. */
export function InterventionDialog({ id, onClose }: { id: string | null; onClose: () => void }) {
  const def = id ? INTERVENTION_BY_ID[id] : null;
  const frame = usePlanetStore((s) => s.frame);
  const selected = usePlanetStore((s) => s.selectedCell);
  const game = useGameStore();
  const [option, setOption] = useState<string>(() => (id ? INTERVENTION_BY_ID[id]?.options?.[0]?.id ?? "" : ""));
  const [variable, setVariable] = useState<PredictVar | "">("");
  const [direction, setDirection] = useState<Direction | "">("");
  const opened = useRef(0), consulted = useRef<string[]>([]);
  useEffect(() => {
    if (!id) return;
    opened.current = performance.now(); consulted.current = [];
    return evidence.subscribe((r) => { if (r.type === "chart_opened") consulted.current.push(r.chart); if (r.type === "layer_viewed") consulted.current.push(r.layer); });
  }, [id]);
  if (!def || !frame) return null;
  const locked = !!def.requires && !game.unlocked.includes(def.requires), early = frame.globals.era < def.minEra;
  const wait = (game.cooldowns[def.id] ?? 0) - frame.tick, affordable = game.canAfford(def.id);
  const telegraphed = frame.events.find((e) => e.phase !== "aftermath" && e.origin !== "background" && !e.suppressed);
  const needsTarget = def.needsCell && selected === null, noEvent = def.kind === "suppress" && !telegraphed;
  const can = !locked && !early && wait <= 0 && affordable && !needsTarget && !noEvent;
  const confirm = () => {
    const prediction = variable && direction ? { variable, direction } : undefined;
    evidence.emit({ type: "decision_time", interventionId: def.id, seconds: Math.round((performance.now() - opened.current) / 1000), consulted: [...new Set(consulted.current)] });
    if (game.apply(def.id, { cell: def.needsCell ? selected : null, optionId: option || undefined, prediction, eventId: telegraphed?.id })) onClose();
  };
  return (
    <Dialog open onClose={onClose} title={t(`intervention.${def.id}.name`)} footer={<><Button onClick={onClose}>{t("common.cancel")}</Button><Button variant="primary" icon="check" disabled={!can} onClick={confirm} data-confirm>{t("intervention.confirm")}</Button></>}>
      <div className="flex flex-col gap-3" data-intervention-dialog={def.id}>
        {locked && <div className="ec-card flex items-start gap-2" role="note"><Icon name="lock" /><div><p className="font-semibold">{t("intervention.lockedTitle")}</p><p>{t("intervention.lockedBody", { concept: t(`research.${def.requires}.name`) })}</p><Link className="ec-link" href="/jogo/pesquisa">{t("intervention.goResearch")}</Link></div></div>}
        {early && !locked && <p className="ec-card" role="note">{t("intervention.needsEra", { era: def.minEra })}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="ec-card"><h3 className="flex items-center gap-2"><Icon name="up" style={{ color: "var(--ec-success)" }} />{t("intervention.gain")}</h3><Ped as="p" k={`ped.intervention.${def.id}.gain`} /></div>
          <div className="ec-card"><h3 className="flex items-center gap-2"><Icon name="down" style={{ color: "var(--ec-warning)" }} />{t("intervention.sideCost")}</h3><Ped as="p" k={`ped.intervention.${def.id}.side`} /></div>
        </div>
        <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2">
          <dt className="font-semibold">{t("intervention.cost")}</dt>
          <dd className="flex flex-wrap gap-2">{Object.entries(def.cost).map(([k, v]) => { const r = RESOURCES.find((x) => x.id === k)!; const short = game.resources[r.id] < (v ?? 0); return <Chip key={k} icon={r.icon} tone={short ? "danger" : undefined}>{t(`resource.${k}`)}: <span className="ec-num">{v}</span> ({t("intervention.have", { n: fmt(game.resources[r.id]) })})</Chip>; })}</dd>
          <dt className="font-semibold">{t("intervention.cooldown")}</dt><dd>{t("intervention.cooldownYears", { years: Math.ceil(def.cooldown / 12) })}{wait > 0 && <> · <strong>{t("intervention.cooldownLeft", { years: Math.ceil(wait / 12) })}</strong></>}</dd>
          {def.synergy && <><dt className="font-semibold">{t("intervention.synergy")}</dt><dd>{def.synergy.map((s) => t(`intervention.${s}.name`)).join(", ")}</dd></>}
          {def.conflict && <><dt className="font-semibold">{t("intervention.conflict")}</dt><dd>{def.conflict.map((s) => t(`intervention.${s}.name`)).join(", ")}</dd></>}
        </dl>
        {def.options && <Select label={t(`intervention.${def.id}.option`)} value={option} onChange={setOption} options={def.options.map((o) => ({ value: o.id, label: t(o.eventType ? `event.${o.eventType}.name` : `role.${o.role}`) }))} />}
        {def.kind === "suppress" && <p className="ec-card" role="note">{telegraphed ? t("intervention.suppressTarget", { name: t(`event.${telegraphed.type}.name`) }) : t("intervention.suppressNone")}</p>}
        {def.needsCell && (
          <div className="ec-card flex flex-wrap items-center gap-2" role="note">
            <Icon name="target" />
            {selected === null ? <><span className="flex-1">{t("intervention.pickTarget")}</span><Button onClick={() => cameraApi.pickCenter()}>{t("intervention.useCenter")}</Button></>
              : <span>{t("intervention.target", { lat: fmt(getMesh(frame.level).latitude[selected], 0), lon: fmt(getMesh(frame.level).longitude[selected], 0) })}</span>}
          </div>
        )}
        {def.predict.length > 0 && (
          <fieldset className="ec-card" data-prediction>
            <legend className="flex items-center gap-2 px-1 font-semibold"><Icon name="target" />{t("predict.title")}</legend>
            <Ped as="p" k="ped.predict.intro" className="ec-muted mb-2 text-[length:var(--ec-text-sm)]" />
            <div className="grid gap-2 sm:grid-cols-2">
              <Select label={t("predict.variable")} value={variable} onChange={(v) => setVariable(v as PredictVar | "")} options={[{ value: "", label: t("predict.skip") }, ...def.predict.map((v) => ({ value: v, label: t(`predict.var.${v}`) }))]} />
              <div role="radiogroup" aria-label={t("predict.direction")}>
                <span className="ec-label">{t("predict.direction")}</span>
                <div className="flex gap-1">{(["up", "same", "down"] as const).map((d) => <button key={d} type="button" role="radio" aria-checked={direction === d} disabled={!variable} className="ec-btn flex-1" onClick={() => setDirection(d)}><Icon name={d === "same" ? "flat" : d} />{t(`predict.${d}`)}</button>)}</div>
              </div>
            </div>
          </fieldset>
        )}
        {!affordable && !locked && <p role="alert" className="flex items-center gap-2"><Icon name="alert" style={{ color: "var(--ec-danger)" }} />{t("intervention.cannotAfford")}</p>}
      </div>
    </Dialog>
  );
}

/** "Por quê?": explains an event or a collapse with a concrete datum and a causal chain, and offers a safe restart. */
export function WhyDialog({ eventId, open, onClose }: { eventId: string | null; open: boolean; onClose: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const collapsed = useGameStore((s) => s.collapsed);
  if (!open || !frame) return null;
  const ev: PlanetEvent | undefined = eventId ? frame.events.find((e) => e.id === eventId) : undefined, g = frame.globals;
  const chain = ev ? EVENT_DEFS[ev.type].chain.map((c) => `ped.chain.${c}`)
    : g.organicStuck > 0.3 ? ["ped.chain.noDecomposers", "ped.chain.matterStuck", "ped.chain.nutrientsDrop", "ped.chain.producerCollapse", "ped.chain.populationDrop"]
    : g.viability < 0.05 ? ["ped.chain.harshConditions", "ped.chain.noLiquidWater", "ped.chain.noLife"] : ["ped.chain.observe", "ped.chain.predict", "ped.chain.act", "ped.chain.compare"];
  return (
    <Dialog open onClose={onClose} title={ev ? t("why.titleEvent", { name: t(`event.${ev.type}.name`) }) : t("why.titleCollapse")} footer={<>{(collapsed || g.viability < 0.05) && <Link className="ec-btn ec-btn--primary" href="/jogo/genese">{t("why.restart")}</Link>}<Button onClick={onClose}>{t("common.close")}</Button></>}>
      <div className="flex flex-col gap-3" data-why>
        <p>{ev ? t("why.eventData", { name: t(`event.${ev.type}.name`), lat: fmt(ev.lat, 0), lon: fmt(ev.lon, 0), intensity: fmt(ev.intensity * 100, 0), scale: t(`scale.${ev.scale}`) }) : t("why.collapseData", { temp: fmt(Math.min(g.meanTempC, 9999), 0), ocean: fmt(g.oceanFraction * 100, 0), richness: frame.bio.richness })}</p>
        <CausalChain steps={chain} />
        {ev && <p className="ec-muted">{t("why.instrument", { instrument: t(`instrument.${ev.instrument}`) })}{!EVENT_DEFS[ev.type].inEngineCatalog && ` ${t("why.abstractEvent")}`}</p>}
        {!ev && <Ped as="p" k="ped.why.legit" />}
      </div>
    </Dialog>
  );
}

/** Contextual tutor that does not block the game. Text streams in; the question comes before the explanation. */
export function TutorPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const log = useGameStore((s) => s.tutorLog);
  const past = usePastFrame(600);
  const reduced = useReducedMotion();
  const [index, setIndex] = useState(-1);
  const [text, setText] = useState("");
  const [reveal, setReveal] = useState(false);
  const current = index >= 0 ? log[index] : log[log.length - 1];
  const ask = (q: QuestionId) => {
    if (!frame) return;
    const a = answerQuestion(q, frame, past), g = useGameStore.getState();
    evidence.emit({ type: "tutor_question", questionId: q });
    g.patch({ tutorLog: [...g.tutorLog.slice(-19), a], stats: { ...g.stats, tutorQuestions: g.stats.tutorQuestions + 1 } });
    setIndex(-1); setReveal(false);
  };
  useEffect(() => {
    if (!current) return;
    let alive = true;
    const p = { ...current.dataParams }; if (typeof p.name === "string" && p.name.startsWith("event.")) p.name = t(p.name);
    const full = `${t(current.dataKey, p)} ${t(current.promptKey)}`;
    void (async () => { for await (const part of streamText(full, reduced)) { if (!alive) return; setText(part); } })();
    return () => { alive = false; };
  }, [current, reduced]);
  if (!open) return null;
  const pos = index >= 0 ? index : log.length - 1;
  return (
    <aside className="ec-panel pointer-events-auto flex max-h-full w-[340px] max-w-full flex-col p-3" aria-label={t("tutor.title")} data-tutor-panel>
      <div className="mb-2 flex items-center justify-between gap-2"><h2 className="flex items-center gap-2 !text-[length:var(--ec-text-md)]"><Icon name="chat" />{t("tutor.title")}</h2><Button variant="ghost" iconOnly icon="close" onClick={onClose}>{t("common.close")}</Button></div>
      <div className="mb-2 flex flex-wrap gap-1">{QUICK_QUESTIONS.map((q) => <Button key={q} onClick={() => ask(q)} data-question={q}><Ped k={`ped.tutor.q.${q}`} /></Button>)}</div>
      <div className="ec-scroll flex-1" aria-live="polite">
        {!current ? <Ped as="p" k="ped.tutor.empty" className="ec-muted" /> : (
          <div className="flex flex-col gap-2" data-tutor-answer>
            <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("tutor.asked", { year: fmt(yearsLabel(current.tick)) })} · <Ped k={`ped.tutor.q.${current.questionId}`} /></p>
            <p className={frame && frame.meta.synthetic ? "ec-ped" : undefined} data-placeholder="pedagogical">{text}</p>
            {!reveal ? <Button icon="eye" onClick={() => setReveal(true)} data-reveal>{t("tutor.showExplanation")}</Button> : <><CausalChain steps={current.chain} /><p className="flex items-start gap-2"><Icon name="flat" /><Ped k={current.nextKey} /></p></>}
            <p><Chip icon="flask">{t(`tutor.source.${current.source}`)}</Chip></p>
          </div>
        )}
      </div>
      {log.length > 1 && (
        <div className="mt-2 flex items-center justify-between gap-2 border-t border-ec-border-subtle pt-2">
          <Button icon="up" disabled={pos <= 0} onClick={() => { setIndex(pos - 1); setReveal(true); }}>{t("tutor.previous")}</Button>
          <span className="ec-num ec-muted text-[length:var(--ec-text-xs)]">{pos + 1}/{log.length}</span>
          <Button icon="down" disabled={pos >= log.length - 1} onClick={() => { setIndex(pos + 1); setReveal(true); }}>{t("tutor.next")}</Button>
        </div>
      )}
    </aside>
  );
}

/** Regional panel: climate, resources and lineages present around a cell (opens when a region is focused). */
export function RegionDialog({ cell, onClose }: { cell: number | null; onClose: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const data = useMemo(() => {
    if (!frame || cell === null || cell >= frame.cellCount) return null;
    const mesh = getMesh(frame.level), c = mesh.centers, f = frame.fields, cos = Math.cos((12 * Math.PI) / 180);
    const acc: Record<string, number> = {}, keys = ["temperature", "precipitation", "humidity", "soilFertility", "water", "mineral", "nitrogen", "organicMatter", "biomassPhoto", "biomassHerb", "biomassCarn"] as const;
    const present = new Map<number, number>();
    let n = 0, land = 0;
    for (let i = 0; i < frame.cellCount; i++) {
      if (c[i * 3] * c[cell * 3] + c[i * 3 + 1] * c[cell * 3 + 1] + c[i * 3 + 2] * c[cell * 3 + 2] < cos) continue;
      n++; if (!f.isWater[i]) land++;
      for (const k of keys) acc[k] = (acc[k] ?? 0) + f[k][i];
      for (const d of [f.domProducer[i], f.domHerb[i], f.domCarn[i]]) if (d >= 0) present.set(d, (present.get(d) ?? 0) + 1);
    }
    for (const k of keys) acc[k] /= n;
    return { acc, n, land: land / n, species: [...present.entries()].sort((a, b) => b[1] - a[1]).map(([idx, cnt]) => ({ s: frame.bio.species.find((x) => x.index === idx)!, share: cnt / n })).filter((x) => x.s) };
  }, [frame, cell]);
  if (!data || !frame || cell === null) return null;
  const a = data.acc;
  const rows = [["layer.temperature.name", a.temperature, "°C", 0], ["layer.precipitation.name", a.precipitation, "mm/mês", 0], ["region.humidity", a.humidity * 100, "%", 0], ["layer.fertility.name", a.soilFertility, "", 2], ["layer.water.name", a.water, "", 2], ["layer.mineral.name", a.mineral, "", 2], ["layer.nitrogen.name", a.nitrogen, "", 2], ["layer.organicMatter.name", a.organicMatter, "", 2], ["layer.biomass.name", a.biomassPhoto, "", 2]] as const;
  return (
    <Dialog open onClose={onClose} title={t("region.title", { lat: fmt(getMesh(frame.level).latitude[cell], 0), lon: fmt(getMesh(frame.level).longitude[cell], 0) })}>
      <div className="flex flex-col gap-3" data-region-dialog>
        <p className="ec-muted">{t("region.summary", { cells: data.n, land: fmt(data.land * 100, 0) })}</p>
        <DataTable caption={t("region.climate")} rows={[...rows]} rowKey={(r) => r[0]} columns={[{ key: "k", header: t("compare.variable"), render: (r) => t(r[0]) }, { key: "v", header: t("region.mean"), numeric: true, render: (r) => `${fmt(Math.min(r[1], 9999), r[3])} ${r[2]}` }]} />
        <h3>{t("region.lineages")}</h3>
        {data.species.length === 0 ? <p className="ec-muted">{t("region.noLife")}</p>
          : <DataTable caption={t("region.lineages")} rows={data.species} rowKey={(r) => r.s.id} columns={[{ key: "n", header: t("codex.name"), render: (r) => <Link className="ec-link" href={`/jogo/codex?especie=${r.s.id}`}>{r.s.name}</Link> }, { key: "r", header: t("codex.role"), render: (r) => t(`role.${r.s.role}`) }, { key: "s", header: t("region.dominantIn"), numeric: true, render: (r) => `${fmt(r.share * 100, 0)}%` }]} />}
      </div>
    </Dialog>
  );
}

const REFLECTIONS = ["cause", "surprise", "next"] as const;
/** End-of-era report: causal chains of what happened, reflection questions and the evidence register (no grades). */
export function EraReportDialog({ era, onClose }: { era: number | null; onClose: () => void }) {
  const frame = usePlanetStore((s) => s.frame);
  const info = usePlanetStore((s) => s.info);
  const history = useHistory(160);
  const diary = useGameStore((s) => s.diary);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [sent, setSent] = useState<string[]>([]);
  if (era === null || !frame || !info) return null;
  const idx = info.eras.findIndex((e) => e.era === era), start = info.eras[idx]?.start ?? 0, end = info.eras[idx + 1]?.start ?? info.endTick;
  const a = snapshots.bracket(start + 1).before ?? snapshots.nearest(start), b = snapshots.nearest(end);
  const marks = (history?.marks ?? []).filter((m) => m.tick >= start && m.tick <= end && m.kind === "event");
  const ev = evidence.all().filter((r) => r.era === era);
  const counts = ev.reduce<Record<string, number>>((m, r) => { m[r.type] = (m[r.type] ?? 0) + 1; return m; }, {});
  const submit = (q: string) => { evidence.emit({ type: "reflection_answered", questionId: `era${era}.${q}`, length: (answers[q] ?? "").trim().length }); setSent([...sent, q]); const g = useGameStore.getState(); g.patch({ stats: { ...g.stats, reflections: g.stats.reflections + 1 } }); };
  return (
    <Dialog open wide onClose={onClose} title={t("report.title", { era, name: t(`era.${era}.name`) })} footer={<Button variant="primary" onClick={onClose}>{t("report.continue")}</Button>}>
      <div className="flex flex-col gap-4" data-era-report>
        <div className="flex flex-wrap items-center gap-2"><SyntheticBadge /><Chip icon="clock">{t("report.span", { y0: fmt(yearsLabel(start)), y1: fmt(yearsLabel(end)) })}</Chip></div>
        {a && b && (
          <table className="ec-table"><caption className="ec-sr-only">{t("report.numbers")}</caption>
            <thead><tr><th scope="col">{t("compare.variable")}</th><th scope="col" className="ec-num">{t("report.start")}</th><th scope="col" className="ec-num">{t("report.end")}</th></tr></thead>
            <tbody>{([[t("hud.temperature") + " (°C)", a.globals.meanTempC, b.globals.meanTempC, 0], ["O₂ (%)", a.globals.o2Pct, b.globals.o2Pct, 1], ["CO₂ (ppm)", a.globals.co2Ppm, b.globals.co2Ppm, 0], [t("compare.lineages"), a.bio.richness, b.bio.richness, 0], [t("report.levels"), a.bio.trophicLevels, b.bio.trophicLevels, 0]] as [string, number, number, number][]).map(([l, x, y, d]) => <tr key={l}><th scope="row">{l}</th><td className="ec-num">{fmt(Math.min(x, 9999), d)}</td><td className="ec-num">{fmt(Math.min(y, 9999), d)}</td></tr>)}</tbody>
          </table>
        )}
        <section><h3>{t("report.chains")}</h3>
          {marks.length === 0 ? <Ped as="p" k="ped.report.quiet" className="ec-muted" /> : <ul className="mt-2 flex flex-col gap-2">{marks.map((m, i) => { const type = m.labelKey.split(".")[1] as keyof typeof EVENT_DEFS; return <li key={i}><p className="mb-1 font-semibold">{t(m.labelKey)} · {t("hud.year", { year: fmt(yearsLabel(m.tick)) })}</p><CausalChain steps={EVENT_DEFS[type].chain.map((c) => `ped.chain.${c}`)} /></li>; })}</ul>}
        </section>
        <section><h3>{t("report.diary")}</h3><ul className="mt-1 list-disc pl-6">{diary.filter((d) => d.tick >= start && d.tick <= end).slice(-8).map((d, i) => <li key={i}><span className="ec-num ec-muted">{t("hud.year", { year: fmt(yearsLabel(d.tick)) })}</span> · {t(d.key, expandParams(d.params))}</li>)}</ul></section>
        <section><h3>{t("report.reflection")}</h3>
          <div className="mt-2 flex flex-col gap-3">{REFLECTIONS.map((q) => (
            <div key={q}><label className="ec-label" htmlFor={`rf-${q}`}><Ped k={`ped.report.q.${q}`} /></label>
              <textarea id={`rf-${q}`} className="ec-input" value={answers[q] ?? ""} onChange={(e) => setAnswers({ ...answers, [q]: e.target.value })} disabled={sent.includes(q)} />
              <div className="mt-1 flex items-center gap-2"><Button icon="check" disabled={sent.includes(q) || !(answers[q] ?? "").trim()} onClick={() => submit(q)}>{sent.includes(q) ? t("report.saved") : t("report.save")}</Button><span className="ec-muted text-[length:var(--ec-text-xs)]">{t("report.privacy")}</span></div>
            </div>))}</div>
        </section>
        <section><h3>{t("report.evidence")}</h3><p className="ec-muted text-[length:var(--ec-text-sm)]">{t("report.evidenceHint")}</p>
          {Object.keys(counts).length === 0 ? <p className="ec-muted">{t("report.noEvidence")}</p> : <ul className="mt-1 flex flex-wrap gap-2">{Object.entries(counts).map(([k, v]) => <li key={k}><Chip>{t(`evidence.${k}`)}: <span className="ec-num">{v}</span></Chip></li>)}</ul>}
        </section>
      </div>
    </Dialog>
  );
}
