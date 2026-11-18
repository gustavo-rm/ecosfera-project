/**
 * Rule-based tutor (stands in for the LLM tutor; same output shape so the swap is transparent).
 * Every answer follows Dossiê §10: it cites a concrete datum of the student's planet, asks a leading question
 * before explaining, shows the causal chain as linked steps and points to one next step.
 * ALL TEXT IS A PEDAGOGICAL PLACEHOLDER (keys under `ped.`), pending review.
 */
import { fmt } from "@/i18n";
import { EVENT_DEFS } from "@/core/state/catalogs";
import type { PlanetFrame } from "@/core/state/types";

export interface TutorAnswer {
  id: string; questionId: string; source: "rules" | "llm";
  dataKey: string; dataParams: Record<string, string | number>;
  promptKey: string; chain: string[]; nextKey: string; tick: number;
}
export const QUICK_QUESTIONS = ["o2", "temperature", "species", "next"] as const;
export type QuestionId = (typeof QUICK_QUESTIONS)[number];
let seq = 0;

export function answerQuestion(q: QuestionId, frame: PlanetFrame, past: PlanetFrame | null): TutorAnswer {
  const g = frame.globals, p = past?.globals ?? g, years = Math.max(1, Math.round((frame.tick - (past?.tick ?? frame.tick)) / 12));
  const active = frame.events.filter((e) => e.origin !== "background" && e.phase !== "telegraph").sort((a, b) => b.intensity - a.intensity)[0];
  const base = { id: `a${++seq}`, questionId: q, source: "rules" as const, tick: frame.tick };
  const ev = (type: string) => EVENT_DEFS[type as keyof typeof EVENT_DEFS].chain.map((c) => `ped.chain.${c}`);
  if (q === "o2") {
    const data = { dataKey: "ped.tutor.data.o2", dataParams: { now: fmt(g.o2Pct, 1), before: fmt(p.o2Pct, 1), years } };
    if (frame.events.some((e) => e.type === "eutrophication" && e.intensity > 0.1)) return { ...base, ...data, promptKey: "ped.tutor.prompt.o2Water", chain: ev("eutrophication"), nextKey: "ped.tutor.next.openO2Layer" };
    if (g.organicStuck > 0.3) return { ...base, ...data, promptKey: "ped.tutor.prompt.decomposers", chain: ["ped.chain.noDecomposers", "ped.chain.matterStuck", "ped.chain.nutrientsDrop", "ped.chain.producerCollapse", "ped.chain.oxygenDrop"], nextKey: "ped.tutor.next.openCycles" };
    if (active && (active.type === "impact" || active.type === "volcanism")) return { ...base, ...data, promptKey: "ped.tutor.prompt.light", chain: [...ev(active.type).slice(0, 4), "ped.chain.oxygenDrop"], nextKey: "ped.tutor.next.openSeries" };
    if (g.era <= 4) return { ...base, ...data, promptKey: "ped.tutor.prompt.whoMakesO2", chain: ["ped.chain.fewProducers", "ped.chain.littlePhotosynthesis", "ped.chain.lowOxygen"], nextKey: "ped.tutor.next.watchBloom" };
    return { ...base, ...data, promptKey: "ped.tutor.prompt.balance", chain: ["ped.chain.producers", "ped.chain.photosynthesis", "ped.chain.respiration", "ped.chain.o2Balance"], nextKey: "ped.tutor.next.openSeries" };
  }
  if (q === "temperature") {
    const data = { dataKey: "ped.tutor.data.temperature", dataParams: { now: fmt(Math.min(g.meanTempC, 9999), 1), before: fmt(Math.min(p.meanTempC, 9999), 1), years } };
    if (frame.events.some((e) => e.type === "glaciation" && e.intensity > 0.1)) return { ...base, ...data, promptKey: "ped.tutor.prompt.ice", chain: ev("glaciation"), nextKey: "ped.tutor.next.openTempLayer" };
    if (g.aerosols > 0.15) return { ...base, ...data, promptKey: "ped.tutor.prompt.light", chain: ["ped.chain.aerosols", "ped.chain.darkening", "ped.chain.cooling", "ped.chain.producerStress"], nextKey: "ped.tutor.next.openTempLayer" };
    if (g.surfaceHeat > 0.2) return { ...base, ...data, promptKey: "ped.tutor.prompt.young", chain: ["ped.chain.formationHeat", "ped.chain.moltenSurface", "ped.chain.slowCooling"], nextKey: "ped.tutor.next.advanceTime" };
    if (g.co2Ppm > 2000 || g.ch4Ppm > 100) return { ...base, ...data, promptKey: "ped.tutor.prompt.greenhouse", chain: ["ped.chain.greenhouseGases", "ped.chain.heatTrapped", "ped.chain.warming"], nextKey: "ped.tutor.next.openCo2" };
    return { ...base, ...data, promptKey: "ped.tutor.prompt.energy", chain: ["ped.chain.starlight", "ped.chain.albedo", "ped.chain.greenhouseGases", "ped.chain.temperatureBalance"], nextKey: "ped.tutor.next.openTempLayer" };
  }
  if (q === "species") {
    const data = { dataKey: "ped.tutor.data.species", dataParams: { now: frame.bio.richness, before: past?.bio.richness ?? frame.bio.richness, years, levels: frame.bio.trophicLevels } };
    if (frame.bio.richness === 0) return { ...base, ...data, promptKey: "ped.tutor.prompt.needs", chain: g.viability < 0.05 ? ["ped.chain.harshConditions", "ped.chain.noLiquidWater", "ped.chain.noLife"] : ["ped.chain.lifeNotYet", "ped.chain.chemistryFirst"], nextKey: g.viability < 0.05 ? "ped.tutor.next.restart" : "ped.tutor.next.advanceTime" };
    if (frame.bio.massExtinction || g.extinctionPulse > 0.3) return { ...base, ...data, promptKey: "ped.tutor.prompt.whoSurvives", chain: ev("impact"), nextKey: "ped.tutor.next.openPhylogeny" };
    if (g.organicStuck > 0.3) return { ...base, ...data, promptKey: "ped.tutor.prompt.decomposers", chain: ["ped.chain.noDecomposers", "ped.chain.matterStuck", "ped.chain.nutrientsDrop", "ped.chain.producerCollapse", "ped.chain.populationDrop"], nextKey: "ped.tutor.next.openCycles" };
    if (frame.bio.originationRate > frame.bio.extinctionRate) return { ...base, ...data, promptKey: "ped.tutor.prompt.newNiches", chain: ["ped.chain.emptyNiches", "ped.chain.isolation", "ped.chain.divergence", "ped.chain.newLineages"], nextKey: "ped.tutor.next.openPhylogeny" };
    return { ...base, ...data, promptKey: "ped.tutor.prompt.balanceLife", chain: ["ped.chain.producers", "ped.chain.herbivores", "ped.chain.carnivores", "ped.chain.energyLoss"], nextKey: "ped.tutor.next.openWeb" };
  }
  const telegraph = frame.events.find((e) => e.phase === "telegraph" && e.origin !== "background");
  if (telegraph) return { ...base, dataKey: "ped.tutor.data.telegraph", dataParams: { name: `event.${telegraph.type}.name`, years: Math.max(1, Math.round((telegraph.startTick - frame.tick) / 12)) }, promptKey: "ped.tutor.prompt.prepare", chain: ev(telegraph.type), nextKey: "ped.tutor.next.predict" };
  return { ...base, dataKey: "ped.tutor.data.status", dataParams: { richness: frame.bio.richness, temp: fmt(Math.min(g.meanTempC, 9999), 0) }, promptKey: "ped.tutor.prompt.hypothesis", chain: ["ped.chain.observe", "ped.chain.predict", "ped.chain.act", "ped.chain.compare"], nextKey: "ped.tutor.next.predict" };
}

/** Text arrives in small pieces, as it will from a streaming LLM (RNF-003). */
export async function* streamText(text: string, instant: boolean): AsyncGenerator<string> {
  if (instant) { yield text; return; }
  const words = text.split(" ");
  let out = "";
  for (const w of words) { out += (out ? " " : "") + w; yield out; await new Promise((r) => setTimeout(r, 28)); }
}
