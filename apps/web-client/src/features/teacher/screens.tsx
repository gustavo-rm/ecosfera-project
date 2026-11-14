"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";
import { samplePalette, toHex } from "@/core/appearance/palettes";
import { SyntheticEngine } from "@/core/source/synthetic/engine";
import { SCENARIO_IDS } from "@/core/source/synthetic/scenarios";
import { INTERVENTIONS } from "@/game/catalog";
import { fmt, t } from "@/i18n";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { announce, Button, Chip, DataTable, Empty, Meter, Select, Slider, SyntheticBadge } from "@/ui/kit";
import { AppShell, RoleGate, TEACHER_NAV } from "../shell/Menu";
import { alerts, bnccCoverage, BNCC_SKILLS, CLASSES, classHistory, classMeans, COMPETENCIES, meanScore, STUDENTS, studentsOf, useTeacher, visible, type Challenge, type Competency, type Recommendation, type Track } from "./data";
import { buildPdf, download, toCsv } from "./export";
import { MiniGlobe } from "./MiniGlobe";

const pct = (v: number) => `${fmt(v * 100, 0)}%`;
const comp = (k: Competency) => t(`teacher.competency.${k}`);
const allClasses = () => [...CLASSES, ...useTeacher.getState().extraClasses];

function Shell({ titleKey, children, coordinator }: { titleKey: string; children: ReactNode; coordinator?: boolean }) {
  return <AppShell title={t(titleKey)} nav={coordinator ? [{ href: "/coordenacao", icon: "table", key: "nav.coordination" }, ...TEACHER_NAV.slice(0, 3)] : TEACHER_NAV} navLabel={t("nav.teacher")} wide><RoleGate allow={coordinator ? ["coordinator"] : ["teacher", "coordinator"]}><p className="mb-3 flex flex-wrap items-center gap-2"><SyntheticBadge /><span className="ec-muted text-[length:var(--ec-text-sm)]">{t("teacher.fictitious")}</span></p>{children}</RoleGate></AppShell>;
}
function ClassPicker() {
  const classId = useTeacher((s) => s.classId), extra = useTeacher((s) => s.extraClasses);
  return <div className="w-[260px] max-w-full"><Select label={t("teacher.class")} value={classId} onChange={(v) => useTeacher.getState().set({ classId: v })} options={[...CLASSES, ...extra].map((c) => ({ value: c.id, label: `${c.name} · ${t(`teacher.track.${c.track}`)}` }))} /></div>;
}
/** Small line of weekly evolution with a text summary. */
function Spark({ values, label }: { values: number[]; label: string }) {
  const W = 220, H = 56, pts = values.map((v, i) => `${(i / (values.length - 1)) * W},${H - 6 - v * (H - 12)}`).join(" ");
  const delta = values[values.length - 1] - values[0];
  return <figure><svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[260px]" role="img" aria-label={t("teacher.sparkAlt", { label, from: pct(values[0]), to: pct(values[values.length - 1]) })}><polyline points={pts} fill="none" stroke="var(--ec-primary)" strokeWidth={2.5} /><circle cx={W} cy={H - 6 - values[values.length - 1] * (H - 12)} r={4} fill="var(--ec-primary)" /></svg><figcaption className="text-[length:var(--ec-text-sm)]">{label}: <strong className="ec-num">{delta >= 0 ? "+" : ""}{fmt(delta * 100, 0)} {t("teacher.points")}</strong> {t("teacher.inWeeks", { n: values.length })}</figcaption></figure>;
}
/** AI recommendations: the AI informs, the teacher decides. Every item can be edited, accepted or dismissed. */
function Recommendations({ list }: { list: Recommendation[] }) {
  const [editing, setEditing] = useState<string | null>(null), [draft, setDraft] = useState("");
  const text = (r: Recommendation) => r.text || t(r.studentId ? "teacher.rec.student" : "teacher.rec.class", { topic: t(`teacher.topic.${r.topic}`), name: STUDENTS.find((s) => s.id === r.studentId)?.nickname ?? "" });
  const open = list.filter((r) => r.status !== "dismissed");
  if (open.length === 0) return <p className="ec-muted">{t("teacher.rec.none")}</p>;
  return (
    <ul className="flex flex-col gap-2" data-recommendations>{open.map((r) => (
      <li key={r.id} className="ec-card !p-3">
        {editing === r.id ? (<><label className="ec-label" htmlFor={`rec-${r.id}`}>{t("teacher.rec.editLabel")}</label><textarea id={`rec-${r.id}`} className="ec-input" value={draft} onChange={(e) => setDraft(e.target.value)} /><div className="mt-2 flex gap-2"><Button variant="primary" icon="check" onClick={() => { useTeacher.getState().updateRec(r.id, { text: draft, status: "edited" }); setEditing(null); announce(t("teacher.rec.saved")); }}>{t("common.save")}</Button><Button onClick={() => setEditing(null)}>{t("common.cancel")}</Button></div></>) : (
          <><p className="flex items-start gap-2"><Icon name="spark" style={{ color: "var(--ec-accent)" }} /><span>{text(r)}</span></p>
            <div className="mt-2 flex flex-wrap items-center gap-2"><Chip tone={r.status === "accepted" ? "success" : r.status === "edited" ? "info" : undefined}>{t(`teacher.rec.status.${r.status}`)}</Chip>
              <Button icon="check" onClick={() => useTeacher.getState().updateRec(r.id, { status: "accepted" })}>{t("teacher.rec.accept")}</Button>
              <Button icon="edit" onClick={() => { setEditing(r.id); setDraft(text(r)); }} data-edit-rec>{t("common.edit")}</Button>
              <Button icon="trash" onClick={() => useTeacher.getState().updateRec(r.id, { status: "dismissed" })} data-dismiss-rec>{t("teacher.rec.dismiss")}</Button></div></>)}
      </li>))}</ul>
  );
}

/** Class view: competency × student heat map, difficulty alerts with student and topic, recent evolution (RF-063, RF-077). */
export function ClassScreen() {
  const classId = useTeacher((s) => s.classId), threshold = useTeacher((s) => s.threshold), recs = useTeacher((s) => s.recommendations);
  const palette = useSettings((s) => s.palette);
  const students = studentsOf(classId), shown = students.filter(visible), means = classMeans(classId), al = alerts(classId, threshold), hist = classHistory(classId);
  const overall = COMPETENCIES.reduce((a, k) => a + means[k], 0) / COMPETENCIES.length;
  const ramp = palette === "gray" ? "gray" : palette === "cividis" ? "cividis" : "viridis";
  return (
    <Shell titleKey="teacher.classTitle">
      <div className="mb-3 flex flex-wrap items-end gap-3" data-screen="teacher-class"><ClassPicker /><div className="w-[260px] max-w-full"><Slider label={t("teacher.threshold")} value={threshold} min={0.2} max={0.7} step={0.05} onChange={(v) => useTeacher.getState().set({ threshold: v })} format={pct} hint={t("teacher.thresholdHint")} /></div></div>
      {students.length === 0 ? <Empty icon="users" title={t("teacher.emptyClass")} hint={t("teacher.emptyClassHint")} /> : (
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex flex-col gap-3">
            <ul className="grid gap-2 sm:grid-cols-4" aria-label={t("teacher.summary")}>
              <li className="ec-card !p-3"><p className="ec-muted text-[length:var(--ec-text-xs)]">{t("teacher.progress")}</p><p className="ec-num text-[length:var(--ec-text-2xl)] font-semibold">{pct(overall)}</p></li>
              {(["scientific", "systemic", "decision"] as Competency[]).map((k) => <li key={k} className="ec-card !p-3"><p className="ec-muted text-[length:var(--ec-text-xs)]">{comp(k)}</p><p className="ec-num text-[length:var(--ec-text-xl)] font-semibold">{pct(means[k])}</p><Meter value={means[k]} label={comp(k)} /></li>)}
            </ul>
            <section className="ec-card" aria-labelledby="heat"><h2 id="heat" className="mb-1">{t("teacher.heatmap")}</h2><p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("teacher.heatmapHint", { hidden: students.length - shown.length })}</p>
              <div className="ec-scroll" tabIndex={0} role="region" aria-label={t("teacher.heatmap")}>
                <table className="ec-table" data-heatmap><thead><tr><th scope="col">{t("teacher.student")}</th>{COMPETENCIES.map((k) => <th key={k} scope="col" className="!whitespace-normal text-[length:var(--ec-text-xs)]">{comp(k)}</th>)}</tr></thead>
                  <tbody>{shown.map((s) => <tr key={s.id}><th scope="row" className="whitespace-nowrap"><Link className="ec-link" href={`/professor/aluno?id=${s.id}`}>{s.nickname}</Link> <span className="ec-muted ec-num text-[length:var(--ec-text-xs)]">{s.code}</span></th>
                    {COMPETENCIES.map((k) => { const v = s.scores[k], low = v < threshold, c = samplePalette(ramp, 0.15 + v * 0.8); return <td key={k} className="ec-num !p-1 text-center"><span className="block rounded-[4px] px-1 py-1.5 font-semibold" style={{ background: toHex(c), color: v > 0.55 ? "#0b0b0b" : "#ffffff", outline: low ? "2px dashed var(--ec-text)" : undefined, outlineOffset: -2 }}>{fmt(v * 100, 0)}{low && <span aria-hidden="true"> ▼</span>}<span className="ec-sr-only">{low ? `, ${t("teacher.below")}` : ""}</span></span></td>; })}</tr>)}</tbody></table>
              </div>
              <p className="ec-muted mt-2 text-[length:var(--ec-text-xs)]">{t("teacher.heatmapLegend")}</p>
            </section>
          </div>
          <div className="flex flex-col gap-3">
            <section className="ec-card" aria-labelledby="alerts"><h2 id="alerts" className="mb-2">{t("teacher.alerts", { n: al.length })}</h2>
              {al.length === 0 ? <p className="ec-muted">{t("teacher.noAlerts")}</p> : <ul className="flex flex-col gap-2" data-alerts>{al.map((a) => <li key={a.student.id} className="flex flex-wrap items-center gap-2"><Icon name="alert" style={{ color: "var(--ec-warning)" }} /><span className="flex-1"><Link className="ec-link" href={`/professor/aluno?id=${a.student.id}`}>{a.student.nickname}</Link> · {t(`teacher.topic.${a.topic}`)} · {comp(a.competency)} {pct(a.student.scores[a.competency])}</span><Link className="ec-btn" href={`/professor/mensagens?id=${a.student.id}`}>{t("teacher.sendFeedback")}</Link></li>)}</ul>}
            </section>
            <section className="ec-card" aria-labelledby="evo"><h2 id="evo" className="mb-2">{t("teacher.evolution")}</h2><Spark values={hist} label={t("teacher.progress")} /></section>
            <section className="ec-card" aria-labelledby="recs"><h2 id="recs" className="mb-1">{t("teacher.rec.title")}</h2><p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("teacher.rec.hint")}</p><Recommendations list={recs.filter((r) => r.classId === classId)} /></section>
          </div>
        </div>)}
    </Shell>
  );
}

/** Student view: progress by competency, evolution, evidence traceable to the action that produced it, editable recommendations. */
export function StudentScreen() {
  const q = useSearchParams(), classId = useTeacher((s) => s.classId), recs = useTeacher((s) => s.recommendations);
  const [id, setId] = useState(q.get("id") ?? studentsOf(classId).find(visible)?.id ?? "");
  const s = STUDENTS.find((x) => x.id === id);
  return (
    <Shell titleKey="teacher.studentTitle">
      <div className="mb-3 w-[320px] max-w-full" data-screen="teacher-student"><Select label={t("teacher.student")} value={id} onChange={setId} options={STUDENTS.map((x) => ({ value: x.id, label: `${x.nickname} (${x.code}) · ${CLASSES.find((c) => c.id === x.classId)?.name}` }))} /></div>
      {!s ? <Empty icon="user" title={t("teacher.noStudent")} /> : !visible(s) ? <Empty icon="shield" title={t("teacher.noConsentTitle")} hint={t("teacher.noConsentHint", { status: t(`teacher.consent.${s.consent}`) })} action={<Link className="ec-btn" href="/professor/privacidade">{t("nav.privacy")}</Link>} /> : (
        <div className="grid gap-3 lg:grid-cols-2">
          <section className="ec-card" aria-labelledby="pc"><h2 id="pc" className="mb-2">{t("teacher.byCompetency")}</h2>
            <ul className="flex flex-col gap-2">{COMPETENCIES.map((k) => <li key={k}><div className="flex justify-between text-[length:var(--ec-text-sm)]"><span>{comp(k)}</span><span className="ec-num">{pct(s.scores[k])}</span></div><Meter value={s.scores[k]} label={comp(k)} /></li>)}</ul>
            <h3 className="mb-1 mt-3">{t("teacher.skills")}</h3><p className="flex flex-wrap gap-1">{COMPETENCIES.filter((k) => s.scores[k] >= 0.6).map((k) => <Chip key={k} tone="success" icon="check">{comp(k)}</Chip>)}{COMPETENCIES.every((k) => s.scores[k] < 0.6) && <span className="ec-muted">{t("teacher.noSkills")}</span>}</p>
          </section>
          <div className="flex flex-col gap-3">
            <section className="ec-card" aria-labelledby="ev"><h2 id="ev" className="mb-2">{t("teacher.evolution")}</h2><Spark values={s.history} label={t("teacher.progress")} /><p className="mt-2 text-[length:var(--ec-text-sm)]">{t("teacher.engagement")}: <span className="ec-num">{pct(s.engagement)}</span>{s.stuckTopic && <> · <Chip tone="warning" icon="alert">{t("teacher.stuck", { topic: t(`teacher.topic.${s.stuckTopic}`) })}</Chip></>}</p></section>
            <section className="ec-card" aria-labelledby="rc"><h2 id="rc" className="mb-2">{t("teacher.rec.title")}</h2><Recommendations list={recs.filter((r) => r.studentId === s.id)} /><Link className="ec-btn mt-2" href={`/professor/mensagens?id=${s.id}`}><Icon name="send" />{t("teacher.sendFeedback")}</Link></section>
          </div>
          <section className="ec-card lg:col-span-2" aria-labelledby="evd"><h2 id="evd" className="mb-1">{t("teacher.evidence")}</h2><p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("teacher.evidenceHint")}</p>
            <DataTable caption={t("teacher.evidence")} rows={[...s.evidence].sort((a, b) => a.week - b.week)} rowKey={(e) => e.id} columns={[
              { key: "w", header: t("teacher.week"), numeric: true, render: (e) => t("teacher.weeksAgo", { n: e.week }) }, { key: "c", header: t("teacher.competencyCol"), render: (e) => comp(e.competency) }, { key: "k", header: t("teacher.evidenceKind"), render: (e) => t(`evidence.${e.kind}`) },
              { key: "a", header: t("teacher.sourceAction"), render: (e) => <span data-trace>{t(`intervention.${e.action}.name`)} · {t(`era.${e.era}.name`)}, {t("hud.year", { year: fmt(e.year) })}</span> },
            ]} />
          </section>
        </div>)}
    </Shell>
  );
}

/** Coverage of BNCC skills by evidence (RF-076). */
export function BnccScreen() {
  const classId = useTeacher((s) => s.classId), cov = bnccCoverage(classId), means = classMeans(classId);
  return (
    <Shell titleKey="teacher.bnccTitle">
      <div className="mb-3" data-screen="teacher-bncc"><ClassPicker /></div>
      <div className="grid gap-3 lg:grid-cols-2">
        <section className="ec-card" aria-labelledby="cov"><h2 id="cov" className="mb-2">{t("teacher.coverage")}</h2>
          <DataTable caption={t("teacher.coverage")} maxHeight={520} rows={cov} rowKey={(r) => r.skill} columns={[{ key: "s", header: t("teacher.skill"), render: (r) => <span className="ec-num">{r.skill}</span> }, { key: "b", header: t("teacher.coverageCol"), render: (r) => <div className="min-w-[140px]"><Meter value={r.coverage} label={r.skill} /></div> }, { key: "p", header: "%", numeric: true, render: (r) => pct(r.coverage) }, { key: "e", header: t("teacher.evidences"), numeric: true, render: (r) => r.evidences }]} />
          <p className="ec-muted mt-2 text-[length:var(--ec-text-xs)]">{t("teacher.coverageNote")}</p>
        </section>
        <section className="ec-card" aria-labelledby="mat"><h2 id="mat" className="mb-2">{t("teacher.matrix")}</h2><ul className="flex flex-col gap-2">{COMPETENCIES.map((k) => <li key={k}><div className="flex justify-between text-[length:var(--ec-text-sm)]"><span>{comp(k)}</span><span className="ec-num">{pct(means[k])}</span></div><Meter value={means[k]} label={comp(k)} /></li>)}</ul></section>
      </div>
    </Shell>
  );
}

/** Classes, students and tracks (RF-061). Edits are local to this browser. */
export function ManageScreen() {
  const st = useTeacher(), [name, setName] = useState(""), [track, setTrack] = useState<Track>("fundamental");
  const classes = [...CLASSES, ...st.extraClasses];
  return (
    <Shell titleKey="teacher.manageTitle">
      <div className="grid gap-3 lg:grid-cols-[360px_minmax(0,1fr)]" data-screen="teacher-manage">
        <section className="ec-card" aria-labelledby="cl"><h2 id="cl" className="mb-2">{t("teacher.classes")}</h2>
          <ul className="mb-3 flex flex-col gap-1">{classes.map((c) => <li key={c.id}><button type="button" className="ec-btn w-full !justify-between" aria-pressed={st.classId === c.id} onClick={() => st.set({ classId: c.id })}><span>{c.name}</span><span className="ec-chip">{t(`teacher.track.${st.tracks[c.id] ?? c.track}`)} · {studentsOf(c.id).length}</span></button></li>)}</ul>
          <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); if (!name.trim()) return; st.set({ extraClasses: [...st.extraClasses, { id: `x${Date.now()}`, name: name.trim(), track, grade: "" }] }); setName(""); announce(t("teacher.classAdded")); }}>
            <div><label className="ec-label" htmlFor="newclass">{t("teacher.newClass")}</label><input id="newclass" className="ec-input" value={name} onChange={(e) => setName(e.target.value)} /></div>
            <Select label={t("teacher.trackLabel")} value={track} onChange={setTrack} options={(["fundamental", "medio", "tecnico"] as Track[]).map((x) => ({ value: x, label: t(`teacher.track.${x}`) }))} />
            <Button variant="primary" icon="plus" type="submit">{t("teacher.addClass")}</Button>
          </form>
        </section>
        <section className="ec-card" aria-labelledby="stu"><div className="mb-2 flex flex-wrap items-end justify-between gap-2"><h2 id="stu">{t("teacher.students")}</h2><div className="w-[220px]"><Select label={t("teacher.trackLabel")} value={st.tracks[st.classId] ?? classes.find((c) => c.id === st.classId)?.track ?? "fundamental"} onChange={(v) => st.set({ tracks: { ...st.tracks, [st.classId]: v } })} options={(["fundamental", "medio", "tecnico"] as Track[]).map((x) => ({ value: x, label: t(`teacher.track.${x}`) }))} /></div></div>
          {studentsOf(st.classId).length === 0 ? <Empty icon="users" title={t("teacher.emptyClass")} hint={t("teacher.emptyClassHint")} /> : <DataTable caption={t("teacher.students")} maxHeight={520} rows={studentsOf(st.classId)} rowKey={(s) => s.id} columns={[{ key: "c", header: t("teacher.code"), render: (s) => <span className="ec-num">{s.code}</span> }, { key: "n", header: t("teacher.nickname"), render: (s) => s.nickname }, { key: "k", header: t("teacher.consentCol"), render: (s) => <Chip tone={s.consent === "granted" ? "success" : s.consent === "pending" ? "warning" : "danger"} icon={s.consent === "granted" ? "check" : s.consent === "pending" ? "clock" : "close"}>{t(`teacher.consent.${s.consent}`)}</Chip> }, { key: "p", header: t("teacher.progress"), numeric: true, render: (s) => (visible(s) ? pct(meanScore(s)) : "—") }]} />}
        </section>
      </div>
    </Shell>
  );
}

/** Challenge builder (RF-062): a BNCC skill, a scenario or planet parameters, restrictions, a success criterion, a class. */
export function ChallengesScreen() {
  const st = useTeacher();
  const [c, setC] = useState<Omit<Challenge, "id" | "createdAt">>({ title: "", skill: "EF07CI13", scenarioId: "genesis", orbitAU: 1, waterFraction: 0.68, maxActions: 5, blocked: [], metric: "o2", threshold: 15, classId: st.classId });
  const create = () => { const title = c.title.trim() || t("teacher.challenge.defaultTitle", { skill: c.skill }); st.set({ challenges: [{ ...c, title, id: `ch${Date.now()}`, createdAt: Date.now() }, ...st.challenges] }); announce(t("teacher.challenge.created")); };
  return (
    <Shell titleKey="teacher.challengeTitle">
      <div className="grid gap-3 lg:grid-cols-2" data-screen="teacher-challenges">
        <form className="ec-card flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); create(); }} aria-labelledby="nc"><h2 id="nc">{t("teacher.challenge.new")}</h2><p className="ec-muted text-[length:var(--ec-text-sm)]">{t("teacher.challenge.hint")}</p>
          <div><label className="ec-label" htmlFor="ctitle">{t("teacher.challenge.name")}</label><input id="ctitle" className="ec-input" value={c.title} onChange={(e) => setC({ ...c, title: e.target.value })} /></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label={t("teacher.skill")} value={c.skill} onChange={(v) => setC({ ...c, skill: v })} options={BNCC_SKILLS.map((s) => ({ value: s, label: s }))} />
            <Select label={t("teacher.challenge.scenario")} value={c.scenarioId} onChange={(v) => setC({ ...c, scenarioId: v })} options={SCENARIO_IDS.map((s) => ({ value: s, label: t(`genesis.scenario.${s}`) }))} />
            <Slider label={t("param.orbitAU.name")} value={c.orbitAU} min={0.5} max={2} step={0.05} onChange={(v) => setC({ ...c, orbitAU: v })} format={(v) => `${fmt(v, 2)} UA`} />
            <Slider label={t("param.waterFraction.name")} value={c.waterFraction} min={0} max={1} step={0.05} onChange={(v) => setC({ ...c, waterFraction: v })} format={pct} />
            <Slider label={t("teacher.challenge.maxActions")} value={c.maxActions} min={1} max={5} step={1} onChange={(v) => setC({ ...c, maxActions: Math.round(v) })} />
            <Select label={t("teacher.class")} value={c.classId} onChange={(v) => setC({ ...c, classId: v })} options={allClasses().map((x) => ({ value: x.id, label: x.name }))} />
          </div>
          <fieldset><legend className="ec-label">{t("teacher.challenge.blocked")}</legend><div className="flex flex-wrap gap-1">{INTERVENTIONS.filter((i) => i.id !== "scan" && i.id !== "study").map((i) => { const on = c.blocked.includes(i.id); return <button key={i.id} type="button" className="ec-btn" aria-pressed={on} onClick={() => setC({ ...c, blocked: on ? c.blocked.filter((x) => x !== i.id) : [...c.blocked, i.id] })}><Icon name={on ? "lock" : i.icon} size={16} />{t(`intervention.${i.id}.name`)}</button>; })}</div></fieldset>
          <div className="grid gap-3 sm:grid-cols-2"><Select label={t("teacher.challenge.metric")} value={c.metric} onChange={(v) => setC({ ...c, metric: v })} options={["o2", "richness", "temp", "biomass"].map((m) => ({ value: m, label: t(`series.${m}`) }))} /><div><label className="ec-label" htmlFor="thr">{t("teacher.challenge.threshold")}</label><input id="thr" type="number" className="ec-input" value={c.threshold} onChange={(e) => setC({ ...c, threshold: Number(e.target.value) })} /></div></div>
          <Button variant="primary" large icon="flag" type="submit" data-create-challenge>{t("teacher.challenge.assign")}</Button>
        </form>
        <section className="ec-card" aria-labelledby="lc"><h2 id="lc" className="mb-2">{t("teacher.challenge.list")}</h2>
          {st.challenges.length === 0 ? <Empty icon="flag" title={t("teacher.challenge.empty")} hint={t("teacher.challenge.emptyHint")} /> : <ul className="flex flex-col gap-2" data-challenges>{st.challenges.map((x) => <li key={x.id} className="ec-card !p-3"><p className="font-semibold">{x.title}</p><p className="text-[length:var(--ec-text-sm)]"><span className="ec-num">{x.skill}</span> · {t(`genesis.scenario.${x.scenarioId}`)} · {allClasses().find((k) => k.id === x.classId)?.name}</p><p className="ec-muted text-[length:var(--ec-text-sm)]">{t("teacher.challenge.criterion", { metric: t(`series.${x.metric}`), value: fmt(x.threshold, 1), actions: x.maxActions })}{x.blocked.length > 0 && ` · ${t("teacher.challenge.blockedList", { list: x.blocked.map((b) => t(`intervention.${b}.name`)).join(", ") })}`}</p><Button icon="trash" className="mt-1" onClick={() => st.set({ challenges: st.challenges.filter((k) => k.id !== x.id) })}>{t("common.remove")}</Button></li>)}</ul>}
        </section>
      </div>
    </Shell>
  );
}

/** Compare planets and decisions between students (RF-065). */
export function CompareScreen() {
  const classId = useTeacher((s) => s.classId), list = studentsOf(classId).filter(visible);
  const [picked, setPicked] = useState<string[]>([]);
  const ids = picked.length ? picked : list.slice(0, 3).map((s) => s.id), chosen = ids.map((id) => STUDENTS.find((s) => s.id === id)!).filter(Boolean);
  return (
    <Shell titleKey="teacher.compareTitle">
      <div className="mb-3 flex flex-wrap items-end gap-3" data-screen="teacher-compare"><ClassPicker />
        <fieldset><legend className="ec-label">{t("teacher.compare.pick")}</legend><div className="flex flex-wrap gap-1">{list.map((s) => { const on = ids.includes(s.id); return <button key={s.id} type="button" className="ec-btn" aria-pressed={on} onClick={() => setPicked(on ? ids.filter((x) => x !== s.id) : [...ids, s.id].slice(-3))}>{s.nickname}</button>; })}</div></fieldset></div>
      {chosen.length === 0 ? <Empty icon="compare" title={t("teacher.compare.empty")} /> : (
        <div className="grid gap-3 md:grid-cols-3">{chosen.map((s) => (
          <section key={s.id} className="ec-card flex flex-col gap-2" aria-label={s.nickname} data-compare-card>
            <h2 className="!text-[length:var(--ec-text-lg)]">{s.nickname} <span className="ec-muted ec-num text-[length:var(--ec-text-xs)]">{s.code}</span></h2>
            <MiniGlobe scenarioId={s.planet.scenarioId} seed={s.planet.seed} tick={s.planet.tick} label={s.nickname} />
            <p className="text-center text-[length:var(--ec-text-sm)]">{t(`genesis.scenario.${s.planet.scenarioId}`)} · {t("genesis.seed")} {s.planet.seed}</p>
            <Link className="ec-btn" href={`/lab/planeta?cenario=${s.planet.scenarioId}&semente=${s.planet.seed}&tick=${s.planet.tick}`}><Icon name="globe" />{t("teacher.compare.open3d")}</Link>
            <h3>{t("teacher.compare.decisions")}</h3>
            <ol className="flex flex-col gap-1 border-l-2 border-ec-border pl-3 text-[length:var(--ec-text-sm)]">{s.decisions.map((d, i) => <li key={i}><span className="ec-num ec-muted">{t("hud.year", { year: d.year })}</span> · {t(`intervention.${d.action}.name`)} {d.hadPrediction && <Chip tone="info" icon="target">{t("teacher.compare.predicted")}</Chip>}</li>)}</ol>
          </section>))}</div>)}
    </Shell>
  );
}

function classReportLines(classId: string): string[] {
  const c = allClasses().find((x) => x.id === classId), means = classMeans(classId), al = alerts(classId, useTeacher.getState().threshold);
  return [t("synthetic.long"), "", `# ${t("teacher.matrix")}`, ...COMPETENCIES.map((k) => `${comp(k)}: ${pct(means[k])}`), "", `# ${t("teacher.alerts", { n: al.length })}`, ...al.map((a) => `${a.student.nickname} (${a.student.code}): ${t(`teacher.topic.${a.topic}`)} · ${comp(a.competency)} ${pct(a.student.scores[a.competency])}`), "",
    `# ${t("teacher.coverage")}`, ...bnccCoverage(classId).map((r) => `${r.skill}: ${pct(r.coverage)} (${r.evidences} ${t("teacher.evidences").toLowerCase()})`), "", `# ${t("teacher.students")}`, ...studentsOf(classId).map((s) => `${s.code} · ${s.nickname} · ${visible(s) ? pct(meanScore(s)) : t(`teacher.consent.${s.consent}`)}`), "", t("teacher.export.footer", { name: c?.name ?? "" })];
}
/** Exports generated in the browser (RF-066), including the numeric series of a planet for the Mathematics teacher. */
export function ExportScreen() {
  const classId = useTeacher((s) => s.classId), c = allClasses().find((x) => x.id === classId);
  const [scenario, setScenario] = useState("genesis"), [done, setDone] = useState("");
  const say = (name: string) => { setDone(t("teacher.export.done", { name })); announce(t("teacher.export.done", { name })); };
  const classCsv = () => { const name = `ecosfera-turma-${classId}.csv`; download(name, toCsv([t("teacher.code"), t("teacher.nickname"), t("teacher.consentCol"), ...COMPETENCIES.map(comp)], studentsOf(classId).map((s) => [s.code, s.nickname, t(`teacher.consent.${s.consent}`), ...COMPETENCIES.map((k) => (visible(s) ? Math.round(s.scores[k] * 100) : ""))])), "text/csv;charset=utf-8"); say(name); };
  const classPdf = () => { const name = `ecosfera-turma-${classId}.pdf`; download(name, buildPdf(t("teacher.export.reportTitle", { name: c?.name ?? "" }), classReportLines(classId)) as BlobPart, "application/pdf"); say(name); };
  const seriesCsv = () => { const e = new SyntheticEngine({ scenarioId: scenario, level: 3 }), h = e.history(e.scenario.eras[0].start, e.scenario.endTick, 240), name = `ecosfera-series-${scenario}.csv`;
    download(name, toCsv([t("common.year"), ...(["o2", "co2", "temp", "biomass", "richness", "shannon", "geneticDistance"] as const).map((k) => t(`series.${k}`)), ...Object.keys(h.populations)], h.ticks.map((tk, i) => [Math.floor(tk / 12), h.o2[i], h.co2[i], h.temp[i], h.biomass[i], h.richness[i], h.shannon[i], h.geneticDistance[i], ...Object.values(h.populations).map((p) => Math.round(p[i] * 100) / 100)].map((v) => (typeof v === "number" ? Math.round(v * 1000) / 1000 : v)))), "text/csv;charset=utf-8"); say(name); };
  return (
    <Shell titleKey="teacher.exportTitle">
      <div className="grid gap-3 lg:grid-cols-2" data-screen="teacher-export">
        <section className="ec-card flex flex-col gap-3" aria-labelledby="ex1"><h2 id="ex1">{t("teacher.export.class")}</h2><ClassPicker /><div className="flex flex-wrap gap-2"><Button variant="primary" icon="download" onClick={classPdf} data-export="pdf">{t("teacher.export.pdf")}</Button><Button icon="download" onClick={classCsv} data-export="csv">{t("teacher.export.csv")}</Button></div><p className="ec-muted text-[length:var(--ec-text-sm)]">{t("teacher.export.note")}</p></section>
        <section className="ec-card flex flex-col gap-3" aria-labelledby="ex2"><h2 id="ex2">{t("teacher.export.series")}</h2><p className="text-[length:var(--ec-text-sm)]">{t("teacher.export.seriesHint")}</p><Select label={t("teacher.challenge.scenario")} value={scenario} onChange={setScenario} options={SCENARIO_IDS.map((s) => ({ value: s, label: t(`genesis.scenario.${s}`) }))} /><Button icon="download" onClick={seriesCsv} data-export="series">{t("teacher.export.seriesCsv")}</Button></section>
      </div>
      <p role="status" className="mt-3" data-export-status>{done}</p>
    </Shell>
  );
}

/** Feedback and messages to a student (RF-067). Kept in this browser only. */
export function MessagesScreen() {
  const q = useSearchParams(), st = useTeacher();
  const [id, setId] = useState(q.get("id") ?? STUDENTS[0].id), [text, setText] = useState("");
  return (
    <Shell titleKey="teacher.messagesTitle">
      <div className="grid gap-3 lg:grid-cols-2" data-screen="teacher-messages">
        <form className="ec-card flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); if (!text.trim()) return; st.set({ messages: [{ id: `m${Date.now()}`, studentId: id, text: text.trim(), at: Date.now() }, ...st.messages] }); setText(""); announce(t("teacher.msg.sent")); }}>
          <Select label={t("teacher.msg.to")} value={id} onChange={setId} options={STUDENTS.map((s) => ({ value: s.id, label: `${s.nickname} (${s.code})` }))} />
          <div><label className="ec-label" htmlFor="msg">{t("teacher.msg.text")}</label><textarea id="msg" className="ec-input" value={text} onChange={(e) => setText(e.target.value)} /><p className="ec-muted mt-1 text-[length:var(--ec-text-xs)]">{t("teacher.msg.guide")}</p></div>
          <Button variant="primary" icon="send" type="submit" disabled={!text.trim()} data-send>{t("common.send")}</Button>
        </form>
        <section className="ec-card" aria-labelledby="sent"><h2 id="sent" className="mb-2">{t("teacher.msg.history")}</h2>{st.messages.length === 0 ? <Empty icon="send" title={t("teacher.msg.empty")} /> : <ul className="flex flex-col gap-2" data-messages>{st.messages.map((m) => <li key={m.id} className="ec-card !p-3"><p className="ec-muted text-[length:var(--ec-text-xs)]">{STUDENTS.find((s) => s.id === m.studentId)?.nickname} · {new Date(m.at).toLocaleString("pt-BR")}</p><p>{m.text}</p></li>)}</ul>}</section>
      </div>
    </Shell>
  );
}

/** Consent and privacy of the class (RF-068): status per student and the restrictions that follow from it. */
export function PrivacyScreen() {
  const classId = useTeacher((s) => s.classId), list = studentsOf(classId), counts = { granted: 0, pending: 0, denied: 0 };
  list.forEach((s) => counts[s.consent]++);
  return (
    <Shell titleKey="teacher.privacyTitle">
      <div className="mb-3" data-screen="teacher-privacy"><ClassPicker /></div>
      <ul className="mb-3 flex flex-wrap gap-2">{(["granted", "pending", "denied"] as const).map((k) => <li key={k}><Chip tone={k === "granted" ? "success" : k === "pending" ? "warning" : "danger"} icon={k === "granted" ? "check" : k === "pending" ? "clock" : "close"}>{t(`teacher.consent.${k}`)}: <span className="ec-num">{counts[k]}</span></Chip></li>)}</ul>
      <section className="ec-card"><DataTable caption={t("teacher.privacyTitle")} maxHeight={520} rows={list} rowKey={(s) => s.id} columns={[{ key: "c", header: t("teacher.code"), render: (s) => <span className="ec-num">{s.code}</span> }, { key: "n", header: t("teacher.nickname"), render: (s) => s.nickname }, { key: "k", header: t("teacher.consentCol"), render: (s) => <Chip tone={s.consent === "granted" ? "success" : s.consent === "pending" ? "warning" : "danger"} icon={s.consent === "granted" ? "check" : s.consent === "pending" ? "clock" : "close"}>{t(`teacher.consent.${s.consent}`)}</Chip> }, { key: "r", header: t("teacher.restrictions"), render: (s) => (s.restrictions.length ? s.restrictions.map((r) => t(`teacher.restriction.${r}`)).join("; ") : t("teacher.restriction.none")) }]} /><p className="ec-muted mt-2 text-[length:var(--ec-text-sm)]">{t("teacher.privacyNote")}</p></section>
    </Shell>
  );
}

/** Coordination: aggregated reports, comparison between classes, BNCC matrix by class. */
export function CoordinationScreen() {
  const rows = useMemo(() => CLASSES.map((c) => ({ c, means: classMeans(c.id), cov: bnccCoverage(c.id), n: studentsOf(c.id).length, consent: studentsOf(c.id).filter(visible).length })), []);
  const palette = useSettings((s) => s.palette), ramp = palette === "gray" ? "gray" : palette === "cividis" ? "cividis" : "viridis";
  const cell = (v: number) => <span className="ec-num block rounded-[4px] px-1 py-1.5 text-center font-semibold" style={{ background: toHex(samplePalette(ramp, 0.15 + v * 0.8)), color: v > 0.55 ? "#0b0b0b" : "#ffffff" }}>{fmt(v * 100, 0)}</span>;
  const csv = () => download("ecosfera-coordenacao.csv", toCsv([t("teacher.class"), t("teacher.trackLabel"), ...COMPETENCIES.map(comp)], rows.map((r) => [r.c.name, t(`teacher.track.${r.c.track}`), ...COMPETENCIES.map((k) => Math.round(r.means[k] * 100))])), "text/csv;charset=utf-8");
  return (
    <Shell titleKey="teacher.coordTitle" coordinator>
      <div className="flex flex-col gap-3" data-screen="coordination">
        <section className="ec-card" aria-labelledby="cmp"><div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h2 id="cmp">{t("teacher.coord.compare")}</h2><Button icon="download" onClick={csv}>{t("teacher.export.csv")}</Button></div>
          <div className="ec-scroll" tabIndex={0} role="region" aria-label={t("teacher.coord.compare")}><table className="ec-table"><thead><tr><th scope="col">{t("teacher.class")}</th><th scope="col" className="ec-num">{t("teacher.students")}</th>{COMPETENCIES.map((k) => <th key={k} scope="col" className="!whitespace-normal text-[length:var(--ec-text-xs)]">{comp(k)}</th>)}</tr></thead>
            <tbody>{rows.map((r) => <tr key={r.c.id}><th scope="row">{r.c.name}<br /><span className="ec-muted text-[length:var(--ec-text-xs)]">{t(`teacher.track.${r.c.track}`)}</span></th><td className="ec-num">{r.consent}/{r.n}</td>{COMPETENCIES.map((k) => <td key={k} className="!p-1">{cell(r.means[k])}</td>)}</tr>)}</tbody></table></div>
          <p className="ec-muted mt-2 text-[length:var(--ec-text-xs)]">{t("teacher.coord.note")}</p></section>
        <section className="ec-card" aria-labelledby="bm"><h2 id="bm" className="mb-2">{t("teacher.coord.bncc")}</h2>
          <div className="ec-scroll" tabIndex={0} role="region" aria-label={t("teacher.coord.bncc")}><table className="ec-table"><thead><tr><th scope="col">{t("teacher.skill")}</th>{rows.map((r) => <th key={r.c.id} scope="col">{r.c.name}</th>)}</tr></thead><tbody>{BNCC_SKILLS.map((s, i) => <tr key={s}><th scope="row" className="ec-num">{s}</th>{rows.map((r) => <td key={r.c.id} className="!p-1">{cell(r.cov[i].coverage)}</td>)}</tr>)}</tbody></table></div></section>
      </div>
    </Shell>
  );
}

const COLLECTED = ["actions", "predictions", "charts", "time", "reflectionLength"], NOT_COLLECTED = ["name", "location", "camera", "contacts", "freeText", "thirdParties"];
/** Guardian view: clear consent and transparency about what is and is not collected. */
export function GuardianScreen() {
  const [consent, setConsent] = useState<"granted" | "pending" | "denied">("pending");
  return (
    <AppShell title={t("guardian.title")} nav={[{ href: "/responsavel", icon: "shield", key: "nav.guardian" }]} navLabel={t("nav.guardian")}>
      <RoleGate allow={["guardian"]}>
        <div className="flex flex-col gap-3" data-screen="guardian">
          <p className="flex flex-wrap items-center gap-2"><SyntheticBadge /><span className="ec-muted text-[length:var(--ec-text-sm)]">{t("guardian.simulated")}</span></p>
          <section className="ec-card" aria-labelledby="g1"><h2 id="g1" className="mb-2">{t("guardian.consentTitle")}</h2><p className="mb-2 max-w-prose">{t("guardian.consentBody")}</p>
            <p className="mb-2" role="status">{t("guardian.status")}: <Chip tone={consent === "granted" ? "success" : consent === "pending" ? "warning" : "danger"} icon={consent === "granted" ? "check" : consent === "pending" ? "clock" : "close"}>{t(`teacher.consent.${consent}`)}</Chip></p>
            <div className="flex flex-wrap gap-2"><Button variant="primary" large icon="check" aria-pressed={consent === "granted"} onClick={() => setConsent("granted")} data-consent="grant">{t("guardian.grant")}</Button><Button large icon="close" aria-pressed={consent === "denied"} onClick={() => setConsent("denied")} data-consent="deny">{t("guardian.deny")}</Button></div>
            <p className="ec-muted mt-2 text-[length:var(--ec-text-sm)]">{t("guardian.denyEffect")}</p></section>
          <div className="grid gap-3 md:grid-cols-2">
            <section className="ec-card" aria-labelledby="g2"><h2 id="g2" className="mb-2">{t("guardian.collected")}</h2><ul className="flex flex-col gap-2">{COLLECTED.map((k) => <li key={k} className="flex items-start gap-2"><Icon name="check" style={{ color: "var(--ec-success)" }} /><span>{t(`guardian.item.${k}`)}</span></li>)}</ul></section>
            <section className="ec-card" aria-labelledby="g3"><h2 id="g3" className="mb-2">{t("guardian.notCollected")}</h2><ul className="flex flex-col gap-2">{NOT_COLLECTED.map((k) => <li key={k} className="flex items-start gap-2"><Icon name="close" style={{ color: "var(--ec-danger)" }} /><span>{t(`guardian.item.${k}`)}</span></li>)}</ul></section>
          </div>
          <section className="ec-card" aria-labelledby="g4"><h2 id="g4" className="mb-2">{t("guardian.rights")}</h2><p className="max-w-prose">{t("guardian.rightsBody")}</p></section>
        </div>
      </RoleGate>
    </AppShell>
  );
}
