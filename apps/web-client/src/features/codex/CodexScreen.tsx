"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { GENE_BY_ID, GENES, METABOLIC_GENES, REPRODUCTIVE_MODES } from "@/core/state/catalogs";
import type { SpeciesRecord } from "@/core/state/types";
import { fmt, fmtAuto, t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { Icon } from "@/ui/icons";
import { Button, Chip, DataTable, Empty, Loading, Ped, Tabs } from "@/ui/kit";
import { expandParams } from "../hud/panels";
import { PlanetStage } from "../hud/stage";
import { yearsLabel } from "../session/hooks";
import { StudentSession } from "../session/StudentSession";
import { StudentShell } from "../shell/Menu";
import { BehaviorRadar, TagGlyphs, ToleranceCurve } from "./charts";

const MET_ICON: Record<string, string> = { photosynthesis: "sun", chemosynthesis: "volcanism", plant_digestion: "leaf", animal_digestion: "footprint", detritivory: "bone", decomposition: "cycle", nitrogen_fixation: "wind" };
const ROLE_ICON: Record<string, string> = { phototroph: "leaf", chemotroph: "volcanism", herbivore: "footprint", carnivore: "target", detritivore: "bone", decomposer: "cycle", nitrogenFixer: "wind", mixotroph: "spark" };
const val = (s: SpeciesRecord, k: string) => s.phenotype[k] as number;

function GeneRow({ s, id }: { s: SpeciesRecord; id: string }) {
  const g = GENE_BY_ID[id], v = s.phenotype[id];
  const shown = g.unit === "ticks" ? t("codex.years", { n: fmt((v as number) / 12, 1) }) : g.kind === "bool" ? (v ? t("common.yes") : t("common.no")) : g.kind === "cat" ? REPRODUCTIVE_MODES[v as number] : `${g.log ? fmtAuto(v as number) : fmt(v as number, g.kind === "int" ? 0 : 2)}${g.unit ? " " + g.unit : ""}`;
  return <><dt className="ec-muted">{g.labelPt}</dt><dd className="ec-num">{shown}</dd></>;
}

/** Read-only species sheet. The student observes the phenotype; nothing here edits the organism (principle 1). */
function SpeciesSheet({ s, all }: { s: SpeciesRecord; all: SpeciesRecord[] }) {
  const selected = usePlanetStore((st) => st.selectedSpecies);
  const name = (id: string) => all.find((x) => x.id === id)?.name ?? id;
  const eatenBy = all.filter((x) => x.preyIds.includes(s.id));
  useEffect(() => { usePlanetStore.getState().selectSpecies(s.id); return () => usePlanetStore.getState().selectSpecies(null); }, [s.id]);
  return (
    <article className="flex flex-col gap-3" data-species-sheet={s.id}>
      <header className="ec-card flex flex-wrap items-center gap-3">
        <Icon name={ROLE_ICON[s.role]} size={36} />
        <div className="flex-1"><h2>{s.name}</h2><p className="ec-muted">{t(`role.${s.role}`)} · {t("codex.trophicLevel")} {s.trophicLevel + 1} · {t("codex.population")}: <span className="ec-num">{fmt(s.population, 0)}</span></p></div>
        <Chip tone={s.alive ? "success" : "danger"} icon={s.alive ? "check" : "close"}>{s.alive ? t("codex.alive") : t("codex.extinct")}</Chip>
        <Chip icon="eye">{t("codex.readOnly")}</Chip>
      </header>
      <div className="grid gap-3 lg:grid-cols-2">
        <section className="ec-card" aria-labelledby="met"><h3 id="met" className="mb-2">{t("codex.metabolism")}</h3>
          <ul className="grid grid-cols-2 gap-2">{METABOLIC_GENES.map((k) => { const on = !!s.phenotype[k]; return <li key={k} className="flex items-center gap-2" data-capability={on ? "on" : "off"}><Icon name={on ? MET_ICON[k] : "minus"} /><span>{GENE_BY_ID[k].labelPt}<span className="ec-muted text-[length:var(--ec-text-xs)]"> · {on ? t("codex.active") : t("codex.absent")}</span></span></li>; })}</ul>
          <dl className="mt-3 grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{["aerobic_respiration", "anaerobic_respiration", "metabolic_efficiency", "storage_capacity"].map((k) => <GeneRow key={k} s={s} id={k} />)}</dl>
        </section>
        <section className="ec-card" aria-labelledby="tol"><h3 id="tol" className="mb-2">{t("codex.tolerances")}</h3>
          <div className="grid gap-3 sm:grid-cols-3"><ToleranceCurve s={s} opt="temp_optimum" breadth="temp_breadth" unit="°C" /><ToleranceCurve s={s} opt="humidity_optimum" breadth="humidity_breadth" unit="" /><ToleranceCurve s={s} opt="ph_optimum" breadth="ph_breadth" unit="pH" /></div>
          <Ped as="p" k="ped.codex.tradeoff" className="ec-muted mt-2 text-[length:var(--ec-text-sm)]" />
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{["salinity_tolerance", "water_retention", "thermal_insulation"].map((k) => <GeneRow key={k} s={s} id={k} />)}</dl>
        </section>
        <section className="ec-card" aria-labelledby="beh"><h3 id="beh" className="mb-2">{t("codex.behavior")}</h3><BehaviorRadar s={s} />
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{["perception_radius", "risk_aversion", "philopatry"].map((k) => <GeneRow key={k} s={s} id={k} />)}</dl>
        </section>
        <section className="ec-card" aria-labelledby="dist"><h3 id="dist" className="mb-2">{t("codex.distribution")}</h3>
          <div className="relative h-[260px] overflow-hidden rounded-[var(--ec-radius-md)] bg-[#04060d]"><PlanetStage /></div>
          <div className="mt-2 flex flex-wrap items-center gap-2"><Chip icon="eye">{selected === s.id ? t("layer.habitat.name") : t("codex.showOnGlobe")}</Chip><Ped k="ped.codex.fauna" className="ec-muted text-[length:var(--ec-text-xs)]" /></div>
        </section>
        <section className="ec-card" aria-labelledby="life"><h3 id="life" className="mb-2">{t("codex.lifeCycle")}</h3>
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{GENES.filter((g) => g.block === "LIF").map((g) => <GeneRow key={g.id} s={s} id={g.id} />)}</dl>
          <div className="mt-3" role="img" aria-label={`${t("codex.offspring")}: ${fmt(val(s, "offspring_count"))}. ${t("codex.investment")}: ${fmt(val(s, "offspring_investment"), 2)}.`}>
            <p className="text-[length:var(--ec-text-sm)]">{t("codex.offspring")}</p><div className="ec-meter"><span style={{ width: `${(Math.log10(val(s, "offspring_count")) / 3) * 100}%` }} /></div>
            <p className="mt-1 text-[length:var(--ec-text-sm)]">{t("codex.investment")}</p><div className="ec-meter"><span style={{ width: `${(val(s, "offspring_investment") / 0.5) * 100}%`, background: "var(--ec-accent)" }} /></div>
          </div>
          <Ped as="p" k="ped.codex.rk" className="ec-muted mt-2 text-[length:var(--ec-text-sm)]" />
        </section>
        <section className="ec-card" aria-labelledby="mor"><h3 id="mor" className="mb-2">{t("codex.morphology")}</h3>
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{GENES.filter((g) => g.block === "MOR").map((g) => <GeneRow key={g.id} s={s} id={g.id} />)}</dl>
          <h3 className="mb-2 mt-4">{t("codex.tags")}</h3>
          <ul className="flex flex-col gap-1">{GENES.filter((g) => g.block === "TAG").map((g) => <li key={g.id}><TagGlyphs symbols={s.phenotype[g.id] as number[]} label={g.labelPt} /></li>)}</ul>
          <Ped as="p" k="ped.codex.tags" className="ec-muted mt-2 text-[length:var(--ec-text-sm)]" />
        </section>
        <section className="ec-card" aria-labelledby="rel"><h3 id="rel" className="mb-2">{t("codex.relations")}</h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt className="font-semibold">{t("codex.eats")}</dt><dd>{s.preyIds.length ? s.preyIds.map(name).join(", ") : t("codex.nothing")}</dd>
            <dt className="font-semibold">{t("codex.eatenBy")}</dt><dd>{eatenBy.length ? eatenBy.map((x) => x.name).join(", ") : t("codex.nothing")}</dd>
            {s.cycleIds.length > 0 && <><dt className="font-semibold">{t("codex.cycle")}</dt><dd>{s.cycleIds.map(name).join(", ")}</dd></>}
          </dl>
        </section>
        <section className="ec-card" aria-labelledby="hist"><h3 id="hist" className="mb-2">{t("codex.history")}</h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt className="font-semibold">{t("codex.origin")}</dt><dd>{t("codex.originText", { mode: t(`speciation.${s.speciationMode}`), year: fmt(yearsLabel(s.originTick)), lat: fmt(s.originLat, 0), lon: fmt(s.originLon, 0) })}{s.parentId && ` (${name(s.parentId)})`}</dd>
            {s.extinctTick !== null && <><dt className="font-semibold">{t("codex.extinction")}</dt><dd>{t("codex.extinctionText", { year: fmt(yearsLabel(s.extinctTick)), cause: t(`cause.${s.extinctionCause}`) })}</dd></>}
            <dt className="font-semibold">{t("codex.geneticDistance")}</dt><dd className="ec-num">{fmt(s.geneticDistance, 2)}</dd>
          </dl>
          {s.founderEffect && <p className="mt-2"><Chip tone="info" icon="flag">{t("codex.founder")}</Chip></p>}
          {s.asexual && <Ped as="p" k="ped.codex.asexual" className="mt-2 text-[length:var(--ec-text-sm)]" />}
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 text-[length:var(--ec-text-sm)]">{GENES.filter((g) => g.block === "REG" && g.kind !== "sym").map((g) => <GeneRow key={g.id} s={s} id={g.id} />)}</dl>
        </section>
      </div>
    </article>
  );
}

export function CodexScreen() {
  const router = useRouter(), q = useSearchParams();
  const frame = usePlanetStore((s) => s.frame), status = usePlanetStore((s) => s.status);
  const codex = useGameStore((s) => s.codex), known = useGameStore((s) => s.known), diary = useGameStore((s) => s.diary);
  const [tab, setTab] = useState("species");
  const id = q.get("especie");
  const all = frame?.bio.species ?? [];
  const current = id ? all.find((s) => s.id === id) : undefined;
  useEffect(() => { if (current) useGameStore.getState().inspect(current.id); }, [current]);
  const listed = all.filter((s) => known.includes(s.id) || codex.includes(s.id));
  return (
    <StudentShell titleKey="codex.title" wide>
      <StudentSession />
      {status !== "ready" || !frame ? <Loading /> : current ? (
        <><Button icon="flat" className="mb-3" onClick={() => router.push("/jogo/codex")}>{t("codex.back")}</Button><SpeciesSheet s={current} all={all} /></>
      ) : (
        <div data-screen="codex">
          <Tabs label={t("codex.title")} value={tab} onChange={setTab} tabs={[{ id: "species", label: t("codex.tabs.species"), icon: "dna" }, { id: "diary", label: t("codex.tabs.diary"), icon: "book" }]} className="mb-3" />
          {tab === "species" ? (listed.length === 0 ? <Empty icon="dna" title={t("codex.empty")} hint={t("codex.emptyHint")} action={<Link className="ec-btn" href="/jogo">{t("nav.game")}</Link>} /> : (
            <>
              <p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("codex.placeholderNames")}</p>
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{listed.map((s) => { const seen = codex.includes(s.id); return (
                <li key={s.id}><Link href={`/jogo/codex?especie=${s.id}`} className="ec-card flex items-center gap-3 no-underline hover:border-ec-primary" data-species={s.id}>
                  <Icon name={seen ? ROLE_ICON[s.role] : "question"} size={30} />
                  <span className="flex flex-1 flex-col"><span className="font-semibold">{seen ? s.name : t("codex.undiscovered")}</span><span className="ec-muted text-[length:var(--ec-text-sm)]">{seen ? `${t(`role.${s.role}`)} · ${t("codex.trophicLevel")} ${s.trophicLevel + 1}` : t("codex.investigate")}</span></span>
                  <Chip tone={s.alive ? "success" : "danger"} icon={s.alive ? "check" : "close"}>{s.alive ? t("codex.alive") : t("codex.extinct")}</Chip>
                </Link></li>); })}</ul>
            </>
          )) : (diary.length === 0 ? <Empty icon="book" title={t("codex.diaryEmpty")} /> : (
            <DataTable caption={t("codex.tabs.diary")} maxHeight={560} rows={[...diary].reverse()} rowKey={(_, i) => String(i)} columns={[{ key: "y", header: t("common.year"), numeric: true, render: (d) => fmt(yearsLabel(d.tick)) }, { key: "e", header: t("common.era"), render: (d) => t(`era.${d.era}.name`) }, { key: "t", header: t("codex.history"), render: (d) => t(d.key, expandParams(d.params)) }]} />
          ))}
        </div>
      )}
    </StudentShell>
  );
}
