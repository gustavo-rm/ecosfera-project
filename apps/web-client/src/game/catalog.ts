/**
 * Game catalogs: interventions, research trees, missions, achievements, ancestors.
 * PLACEHOLDER balance and pedagogy, to be reviewed by game design and by the domain authority.
 * Rule that never changes (spec §20.5): the student acts on the ENVIRONMENT only. There is no entry here, and there
 * must never be one, that edits genomes, assigns fitness or picks survivors.
 */
import type { ModifierKind } from "@/core/source/synthetic/engine";
import type { EventType, PlanetFrame, TrophicRole } from "@/core/state/types";

export type ResourceId = "actionPoints" | "energy" | "budget" | "research" | "influence" | "naturalResources";
export const RESOURCES: { id: ResourceId; icon: string; renewable: boolean }[] = [
  { id: "actionPoints", icon: "clock", renewable: true }, { id: "energy", icon: "bolt", renewable: true }, { id: "budget", icon: "coin", renewable: true },
  { id: "research", icon: "flask", renewable: false }, { id: "influence", icon: "star", renewable: false }, { id: "naturalResources", icon: "mountain", renewable: false },
];
export type Cost = Partial<Record<ResourceId, number>>;
export interface InterventionDef {
  id: string; icon: string; kind: ModifierKind | "scan" | "study"; cost: Cost; cooldown: number; needsCell: boolean;
  /** Tech node that enables it. The card shows the missing concept instead of a mute lock. */
  requires: string | null; minEra: number;
  /** Variables the student can make a prediction about. */
  predict: PredictVar[]; synergy?: string[]; conflict?: string[];
  options?: { id: string; eventType?: EventType; role?: TrophicRole }[];
}
export type PredictVar = "temperature" | "o2" | "co2" | "biomass" | "richness" | "water";
export const INTERVENTIONS: InterventionDef[] = [
  { id: "scan", icon: "search", kind: "scan", cost: { actionPoints: 1 }, cooldown: 12, needsCell: true, requires: null, minEra: 1, predict: [] },
  { id: "study", icon: "microscope", kind: "study", cost: { actionPoints: 1 }, cooldown: 24, needsCell: false, requires: null, minEra: 1, predict: [], synergy: ["scan"] },
  { id: "irrigate", icon: "water", kind: "irrigate", cost: { actionPoints: 1, energy: 30, naturalResources: 10 }, cooldown: 120, needsCell: true, requires: "tech.irrigation", minEra: 2, predict: ["biomass", "water"], conflict: ["fertilize"] },
  { id: "reforest", icon: "tree", kind: "reforest", cost: { actionPoints: 1, energy: 20 }, cooldown: 240, needsCell: true, requires: "tech.reforest", minEra: 6, predict: ["co2", "biomass", "temperature"], synergy: ["irrigate"] },
  { id: "fertilize", icon: "seed", kind: "fertilize", cost: { actionPoints: 1, budget: 20 }, cooldown: 180, needsCell: true, requires: "tech.fertilizer", minEra: 4, predict: ["biomass", "o2"], conflict: ["irrigate"] },
  { id: "cool", icon: "glaciation", kind: "cool", cost: { actionPoints: 2, energy: 60 }, cooldown: 600, needsCell: false, requires: "tech.climate", minEra: 2, predict: ["temperature", "biomass"], conflict: ["warm"] },
  { id: "warm", icon: "sun", kind: "warm", cost: { actionPoints: 2, energy: 40 }, cooldown: 600, needsCell: false, requires: "tech.climate", minEra: 2, predict: ["temperature", "co2"], conflict: ["cool"] },
  { id: "barrier", icon: "mountain", kind: "barrier", cost: { actionPoints: 2, energy: 80, naturalResources: 30 }, cooldown: 1200, needsCell: true, requires: "tech.barrier", minEra: 5, predict: ["richness"] },
  { id: "introduce", icon: "dna", kind: "introduce", cost: { actionPoints: 2, research: 10 }, cooldown: 600, needsCell: true, requires: "tech.seedbank", minEra: 4, predict: ["richness", "biomass"],
    options: [{ id: "phototroph", role: "phototroph" }, { id: "herbivore", role: "herbivore" }, { id: "carnivore", role: "carnivore" }, { id: "decomposer", role: "decomposer" }] },
  { id: "trigger", icon: "bolt", kind: "event", cost: { actionPoints: 1, energy: 10 }, cooldown: 240, needsCell: true, requires: "tech.sensors", minEra: 2, predict: ["biomass", "temperature", "richness"],
    options: [{ id: "fire", eventType: "fire" }, { id: "storm", eventType: "storm" }, { id: "drought", eventType: "drought" }, { id: "volcanism", eventType: "volcanism" }] },
  { id: "suppress", icon: "shield", kind: "suppress", cost: { actionPoints: 2, energy: 50 }, cooldown: 360, needsCell: false, requires: "tech.shield", minEra: 2, predict: ["biomass", "richness"] },
];
export const INTERVENTION_BY_ID = Object.fromEntries(INTERVENTIONS.map((i) => [i.id, i]));
/** Extension point reserved for the "Modo Relojoeiro" (isolated artificial selection, optional in the spec). Not built. */
export const WATCHMAKER_MODE_ENABLED = false;

export interface Stats {
  predictions: number; correctPredictions: number; chartsOpened: number; layersViewed: string[]; scans: number; interventions: number; eventsWitnessed: string[];
  speciesInspected: string[]; tutorQuestions: number; reflections: number; collapses: number; recoveries: number; maxEra: number; iceAgeSeen: boolean; iceAgeReverted: boolean; maxLevels: number; cyclesSeen: boolean;
}
export const EMPTY_STATS: Stats = { predictions: 0, correctPredictions: 0, chartsOpened: 0, layersViewed: [], scans: 0, interventions: 0, eventsWitnessed: [], speciesInspected: [], tutorQuestions: 0, reflections: 0, collapses: 0, recoveries: 0, maxEra: 1, iceAgeSeen: false, iceAgeReverted: false, maxLevels: 0, cyclesSeen: false };

export interface ResearchNode { id: string; tree: "science" | "tech"; era: number; cost: number; requires: string[]; column: number; row: number;
  /** Mastery shown through play, never through screen time. Returns progress 0..1. */
  mastery: (s: Stats) => number }
const n = (id: string, tree: ResearchNode["tree"], era: number, cost: number, requires: string[], column: number, row: number, mastery: ResearchNode["mastery"]): ResearchNode => ({ id, tree, era, cost, requires, column, row, mastery });
const frac = (v: number, goal: number) => Math.min(1, v / goal);
export const RESEARCH: ResearchNode[] = [
  n("sci.habitableZone", "science", 1, 0, [], 0, 1, () => 1),
  n("sci.geology", "science", 1, 4, ["sci.habitableZone"], 1, 0, (s) => frac(s.scans, 1)),
  n("sci.atmosphere", "science", 2, 4, ["sci.habitableZone"], 1, 1, (s) => frac(s.layersViewed.length, 1)),
  n("sci.waterCycle", "science", 2, 5, ["sci.habitableZone"], 1, 2, (s) => frac(s.layersViewed.length, 2)),
  n("sci.oceans", "science", 2, 6, ["sci.waterCycle"], 2, 3, (s) => frac(s.scans, 2)),
  n("sci.greenhouse", "science", 3, 8, ["sci.atmosphere"], 2, 1, (s) => frac(s.chartsOpened, 1)),
  n("sci.cycles", "science", 3, 8, ["sci.atmosphere", "sci.waterCycle"], 2, 2, (s) => frac(s.chartsOpened, 2)),
  n("sci.photosynthesis", "science", 4, 10, ["sci.cycles"], 3, 1, (s) => frac(s.predictions, 1)),
  n("sci.decomposition", "science", 4, 10, ["sci.cycles"], 3, 2, (s) => frac(s.tutorQuestions, 1)),
  n("sci.soil", "science", 4, 10, ["sci.geology", "sci.cycles"], 3, 0, (s) => frac(s.scans, 3)),
  n("sci.speciation", "science", 5, 14, ["sci.photosynthesis"], 4, 1, (s) => frac(s.speciesInspected.length, 2)),
  n("sci.foodWeb", "science", 6, 16, ["sci.speciation", "sci.decomposition"], 5, 1, (s) => frac(s.maxLevels, 3)),
  n("sci.resilience", "science", 7, 18, ["sci.foodWeb"], 6, 1, (s) => frac(s.eventsWitnessed.length, 2)),
  n("sci.coevolution", "science", 8, 22, ["sci.resilience"], 7, 1, (s) => (s.cyclesSeen ? 1 : 0)),
  n("tech.scanner", "tech", 1, 0, [], 0, 0, () => 1),
  n("tech.sensors", "tech", 2, 5, ["sci.atmosphere"], 1, 0, (s) => frac(s.layersViewed.length, 2)),
  n("tech.irrigation", "tech", 2, 6, ["sci.waterCycle"], 1, 1, (s) => frac(s.scans, 2)),
  n("tech.climate", "tech", 3, 10, ["sci.greenhouse"], 2, 0, (s) => frac(s.predictions, 1)),
  n("tech.fertilizer", "tech", 4, 10, ["sci.soil"], 3, 0, (s) => frac(s.interventions, 1)),
  n("tech.reforest", "tech", 6, 12, ["sci.photosynthesis"], 3, 1, (s) => frac(s.correctPredictions, 1)),
  n("tech.barrier", "tech", 5, 14, ["sci.speciation"], 4, 0, (s) => frac(s.speciesInspected.length, 3)),
  n("tech.seedbank", "tech", 6, 16, ["sci.foodWeb"], 5, 0, (s) => frac(s.correctPredictions, 2)),
  n("tech.shield", "tech", 7, 18, ["sci.resilience"], 6, 0, (s) => frac(s.eventsWitnessed.length, 3)),
];
export const RESEARCH_BY_ID = Object.fromEntries(RESEARCH.map((r) => [r.id, r]));

export interface MissionDef { id: string; kind: "mission" | "era"; era: number; bncc: string[]; progress: (f: PlanetFrame, s: Stats) => number }
const m = (id: string, kind: MissionDef["kind"], era: number, bncc: string[], progress: MissionDef["progress"]): MissionDef => ({ id, kind, era, bncc, progress });
export const MISSIONS: MissionDef[] = [
  m("era1", "era", 1, ["EF06CI11", "EF06CI14"], (f) => (f.globals.era > 1 ? 1 : f.globals.eraProgress)),
  m("era2", "era", 2, [], (f) => (f.globals.era > 2 ? 1 : f.globals.era < 2 ? 0 : Math.min(1, f.globals.oceanFraction / 0.3))),
  m("era3", "era", 3, ["EM13CNT201"], (f) => (f.globals.era > 3 ? 1 : f.globals.era < 3 ? 0 : f.globals.eraProgress)),
  m("era4", "era", 4, [], (f) => Math.min(1, f.globals.o2Pct / 5)),
  m("era5", "era", 5, ["EF09CI11"], (f) => Math.min(1, f.bio.richness / 8)),
  m("era6", "era", 6, ["EF07CI07", "EF07CI08"], (f) => Math.min(1, f.bio.species.filter((x) => x.alive && x.realm === "land").length / 5)),
  m("era7", "era", 7, ["EF08CI16"], (f, s) => (f.globals.era > 7 ? 1 : f.globals.era < 7 ? 0 : s.eventsWitnessed.length >= 2 && !f.bio.massExtinction ? f.globals.eraProgress : f.globals.eraProgress * 0.5)),
  m("era8", "era", 8, [], (f) => (f.globals.era < 8 ? 0 : Math.min(1, f.bio.trophicLevels / 4) * f.globals.eraProgress)),
  m("habitable", "mission", 1, ["EF06CI11", "EF06CI14"], (f) => Math.min(1, f.globals.viability + (f.globals.surfaceHeat > 0.3 ? 0 : 0))),
  m("air", "mission", 3, ["EF07CI13"], (_f, s) => Math.min(1, (s.layersViewed.includes("temperature") ? 0.34 : 0) + (s.predictions > 0 ? 0.33 : 0) + (s.chartsOpened > 0 ? 0.33 : 0))),
  m("web", "mission", 6, ["EF07CI07", "EF07CI08"], (f) => Math.min(1, f.bio.trophicLevels / 3)),
  m("weather", "mission", 7, ["EF08CI14", "EF08CI15", "EF08CI16"], (_f, s) => Math.min(1, s.eventsWitnessed.filter((e) => e === "drought" || e === "storm").length / 2)),
  m("life", "mission", 5, ["EF09CI11"], (f, s) => Math.min(1, (f.bio.species.filter((x) => x.speciationMode !== "ancestral").length >= 2 ? 0.5 : 0) + Math.min(0.5, s.speciesInspected.length / 6))),
  m("future", "mission", 8, ["EF09CI14", "EF09CI16"], (_f, s) => Math.min(1, s.correctPredictions / 3)),
];
export interface AchievementDef { id: string; icon: string; earned: (s: Stats) => boolean }
/** Discovery-based achievements, never repetition-based. */
export const ACHIEVEMENTS: AchievementDef[] = [
  { id: "firstPrediction", icon: "target", earned: (s) => s.correctPredictions >= 1 },
  { id: "iceAge", icon: "glaciation", earned: (s) => s.iceAgeSeen && s.iceAgeReverted },
  { id: "threeLevels", icon: "pyramid", earned: (s) => s.maxLevels >= 3 },
  { id: "recovered", icon: "reset", earned: (s) => s.recoveries >= 1 },
  { id: "cartographer", icon: "search", earned: (s) => s.scans >= 5 },
  { id: "cycleFound", icon: "cycle", earned: (s) => s.cyclesSeen },
  { id: "naturalist", icon: "book", earned: (s) => s.speciesInspected.length >= 6 },
  { id: "dataReader", icon: "chart", earned: (s) => s.chartsOpened >= 4 },
];
export const PLAYER_LEVELS = ["apprentice", "explorer", "investigator", "guardian"] as const;
