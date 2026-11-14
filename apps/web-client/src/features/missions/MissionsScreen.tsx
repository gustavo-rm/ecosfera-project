"use client";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ACHIEVEMENTS, MISSIONS, PLAYER_LEVELS } from "@/game/catalog";
import { fmt, t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { Icon } from "@/ui/icons";
import { Chip, DataTable, Empty, Loading, Meter, Ped, Tabs } from "@/ui/kit";
import { yearsLabel } from "../session/hooks";
import { StudentSession } from "../session/StudentSession";
import { StudentShell } from "../shell/Menu";

/** Self-regulation in friendly language: goals, habits of inquiry and level. No grades, no pressure (principle 10). */
export function ProgressPanel() {
  const stats = useGameStore((s) => s.stats), level = useGameStore((s) => s.playerLevel), done = useGameStore((s) => s.missionsDone);
  const rows: [string, number, string][] = [["progress.predictions", stats.predictions, "target"], ["progress.confirmed", stats.correctPredictions, "check"], ["progress.charts", stats.chartsOpened, "chart"], ["progress.scans", stats.scans, "search"], ["progress.species", stats.speciesInspected.length, "dna"], ["progress.questions", stats.tutorQuestions, "chat"], ["progress.recoveries", stats.recoveries, "reset"]];
  return (
    <div className="grid gap-3 lg:grid-cols-2" data-progress>
      <section className="ec-card" aria-labelledby="nivel"><h2 id="nivel" className="mb-2">{t("level")}</h2>
        <ol className="flex flex-wrap gap-2">{PLAYER_LEVELS.map((l, i) => <li key={l}><Chip tone={i === level ? "success" : undefined} icon={i < level ? "check" : i === level ? "star" : "lock"}>{t(`level.${l}`)}{i === level && <span className="ec-sr-only"> (atual)</span>}</Chip></li>)}</ol>
        <p className="mt-2">{level < 3 ? t("progress.nextLevel", { level: t(`level.${PLAYER_LEVELS[level + 1]}`) }) : t("progress.top")}</p><p className="ec-muted mt-1 text-[length:var(--ec-text-sm)]">{t("level.note")}</p>
      </section>
      <section className="ec-card" aria-labelledby="habitos"><h2 id="habitos" className="mb-2">{t("progress.habits")}</h2>
        <ul className="grid grid-cols-2 gap-2">{rows.map(([k, v, icon]) => <li key={k} className="flex items-center gap-2"><Icon name={icon} /><span>{t(k)}: <strong className="ec-num">{v}</strong></span></li>)}</ul>
        <p className="ec-muted mt-2 text-[length:var(--ec-text-sm)]">{t("progress.noScores")}</p>
      </section>
      <section className="ec-card lg:col-span-2" aria-labelledby="metas"><h2 id="metas" className="mb-2">{t("progress.goals")}</h2><Meter value={done.length / MISSIONS.length} label={t("progress.goals")} valueText={`${done.length}/${MISSIONS.length}`} /><p className="ec-num mt-1">{done.length}/{MISSIONS.length}</p></section>
    </div>
  );
}

export function MissionsScreen() {
  const q = useSearchParams();
  const [tab, setTab] = useState(q.get("aba") === "previsoes" ? "predictions" : q.get("aba") === "progresso" ? "progress" : "missions");
  const frame = usePlanetStore((s) => s.frame);
  const g = useGameStore();
  if (!frame) return <StudentShell titleKey="missions.title"><StudentSession /><Loading /></StudentShell>;
  const card = (m: (typeof MISSIONS)[number]) => { const done = g.missionsDone.includes(m.id), p = done ? 1 : m.progress(frame, g.stats); return (
    <li key={m.id} className="ec-card flex flex-col gap-1" data-mission={m.id}>
      <div className="flex items-start justify-between gap-2"><h3 className="!text-[length:var(--ec-text-md)]">{t(`mission.${m.id}.name`)}</h3><Chip tone={done ? "success" : undefined} icon={done ? "check" : "clock"}>{done ? t("missions.done") : t("missions.inProgress")}</Chip></div>
      <Ped as="p" k={`ped.mission.${m.id}.desc`} className="text-[length:var(--ec-text-sm)]" />
      <Meter value={p} label={t("mission.progress")} />
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t(`era.${m.era}.name`)}{m.bncc.length > 0 && ` · ${t("missions.bncc", { codes: m.bncc.join(", ") })}`}</p>
    </li>); };
  return (
    <StudentShell titleKey="missions.title">
      <StudentSession />
      <Tabs label={t("missions.title")} value={tab} onChange={setTab} className="mb-3" tabs={[{ id: "missions", label: t("missions.tabs.missions"), icon: "target" }, { id: "achievements", label: t("missions.tabs.achievements"), icon: "star" }, { id: "predictions", label: t("missions.tabs.predictions"), icon: "compare" }, { id: "progress", label: t("missions.tabs.progress"), icon: "user" }]} />
      <div role="tabpanel" data-screen="missions" data-tab={tab}>
        {tab === "missions" && <><h2 className="mb-2">{t("missions.missionList")}</h2><ul className="mb-4 grid gap-2 sm:grid-cols-2">{MISSIONS.filter((m) => m.kind === "mission").map(card)}</ul><h2 className="mb-2">{t("missions.eraGoals")}</h2><ul className="grid gap-2 sm:grid-cols-2">{MISSIONS.filter((m) => m.kind === "era").map(card)}</ul></>}
        {tab === "achievements" && <ul className="grid gap-2 sm:grid-cols-2">{ACHIEVEMENTS.map((a) => { const got = g.achievements.includes(a.id); return <li key={a.id} className="ec-card flex items-center gap-3" style={{ opacity: got ? 1 : 0.75 }}><Icon name={got ? a.icon : "question"} size={30} /><span className="flex flex-1 flex-col"><span className="font-semibold">{t(`achievement.${a.id}.name`)}</span><Ped k={`ped.achievement.${a.id}.desc`} className="ec-muted text-[length:var(--ec-text-sm)]" /></span><Chip tone={got ? "success" : undefined} icon={got ? "check" : "lock"}>{got ? t("missions.earned") : t("missions.notEarned")}</Chip></li>; })}</ul>}
        {tab === "predictions" && (g.predictions.length === 0 ? <Empty icon="target" title={t("missions.noPredictions")} hint={t("missions.noPredictionsHint")} /> : (
          <DataTable caption={t("missions.tabs.predictions")} rows={[...g.predictions].reverse()} rowKey={(p) => p.id} columns={[
            { key: "w", header: t("missions.when"), numeric: true, render: (p) => fmt(yearsLabel(p.tick)) }, { key: "a", header: t("missions.action"), render: (p) => t(`intervention.${p.interventionId}.name`) }, { key: "v", header: t("compare.variable"), render: (p) => t(`predict.var.${p.variable}`) },
            { key: "p", header: t("missions.predicted"), render: (p) => <span className="inline-flex items-center gap-1"><Icon name={p.direction === "same" ? "flat" : p.direction} size={16} />{t(`predict.${p.direction}`)}</span> },
            { key: "o", header: t("missions.observed"), render: (p) => (p.result ? <span className="inline-flex items-center gap-1"><Icon name={p.result.observed === "same" ? "flat" : p.result.observed} size={16} />{t(`predict.${p.result.observed}`)}</span> : t("missions.pending", { year: fmt(yearsLabel(p.dueTick)) })) },
            { key: "r", header: t("codex.status"), render: (p) => (p.result ? <Chip tone={p.result.match ? "success" : "info"} icon={p.result.match ? "check" : "info"}>{p.result.match ? t("missions.match") : t("missions.differ")}</Chip> : "—") },
          ]} />))}
        {tab === "progress" && <ProgressPanel />}
      </div>
    </StudentShell>
  );
}
