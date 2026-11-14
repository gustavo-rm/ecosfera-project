"use client";
import { create } from "zustand";
import { BASE_LAYERS } from "@/core/appearance/layers";
import { evidence } from "@/core/evidence/bus";
import { getMesh } from "@/core/mesh/geodesic";
import type { PlanetFrame, PlanetParams } from "@/core/state/types";
import { ACHIEVEMENTS, EMPTY_STATS, INTERVENTION_BY_ID, MISSIONS, RESEARCH_BY_ID, type PredictVar, type ResourceId, type Stats } from "@/game/catalog";
import type { TutorAnswer } from "@/game/tutor";
import { feedback } from "@/render/PlanetBody";
import { idbGet, idbSet } from "./idb";
import { usePlanetStore } from "./planetStore";

export type Direction = "up" | "down" | "same";
export interface Prediction { id: string; interventionId: string; variable: PredictVar; direction: Direction; tick: number; dueTick: number; baseline: number; cell: number | null; result?: { observed: Direction; match: boolean; value: number } }
export interface Notice { id: string; key: string; params?: Record<string, string | number>; tone: "info" | "success" | "warning" | "danger"; icon: string; tick: number; action?: { type: "focus" | "species" | "report" | "prediction" | "why" | "restart" | "tutor"; ref?: string | number } }
export interface DiaryEntry { tick: number; era: number; key: string; params?: Record<string, string | number> }

export interface GameStore {
  hydrated: boolean; started: boolean; scenarioId: string; seed: number; params: Partial<PlanetParams>;
  resources: Record<ResourceId, number>; cooldowns: Record<string, number>;
  unlocked: string[]; stats: Stats; achievements: string[]; missionsDone: string[];
  codex: string[]; known: string[]; diary: DiaryEntry[]; scans: number[]; revealAll: boolean;
  predictions: Prediction[]; notices: Notice[]; tutorLog: TutorAnswer[];
  onboarding: number; attempts: number; lastActionTick: number; reportEra: number | null; collapsed: boolean;
  /** Displayed only. It comes from the assessment data; the student cannot buy it (simulated here). */
  playerLevel: 0 | 1 | 2 | 3;
  start(scenarioId: string, params?: Partial<PlanetParams>, seed?: number): Promise<void>;
  resume(): Promise<void>;
  canAfford(id: string): boolean;
  apply(id: string, opts: { cell: number | null; optionId?: string; prediction?: { variable: PredictVar; direction: Direction }; eventId?: string }): boolean;
  unlock(nodeId: string): boolean;
  inspect(lineageId: string): void;
  notify(n: Omit<Notice, "id" | "tick">): void;
  dismiss(id: string): void;
  onFrame(frame: PlanetFrame, prev: PlanetFrame | null): void;
  patch(p: Partial<GameStore>): void;
}

const START_RES: Record<ResourceId, number> = { actionPoints: 5, energy: 100, budget: 60, research: 6, influence: 0, naturalResources: 100 };
export const MAX_AP = 5;
const KEY = "game.v1";
let noticeSeq = 0;
const directionOf = (before: number, after: number): Direction => { const d = (after - before) / Math.max(1e-6, Math.abs(before)); return d > 0.02 ? "up" : d < -0.02 ? "down" : "same"; };

export function readVariable(frame: PlanetFrame, v: PredictVar, cell: number | null): number {
  const g = frame.globals;
  if (v === "temperature") return g.meanTempC + 273.15;
  if (v === "o2") return g.o2Pct;
  if (v === "co2") return g.co2Ppm;
  if (v === "richness") return frame.bio.richness;
  const field = v === "biomass" ? frame.fields.biomassPhoto : frame.fields.humidity;
  if (cell === null) return v === "biomass" ? g.totalBiomass : g.oceanFraction;
  const c = getMesh(frame.level).centers, cx = c[cell * 3], cy = c[cell * 3 + 1], cz = c[cell * 3 + 2];
  let sum = 0, n = 0;
  for (let i = 0; i < frame.cellCount; i++) if (c[i * 3] * cx + c[i * 3 + 1] * cy + c[i * 3 + 2] * cz > 0.97) { sum += field[i]; n++; }
  return n ? sum / n : 0;
}
/** Cells revealed by scans. Base layers need no scan; the others show hatching where the student has not looked yet. */
export function buildRevealMask(level: number, scans: number[]): Uint8Array {
  const mesh = getMesh(level), mask = new Uint8Array(mesh.count), c = mesh.centers, cos = Math.cos((28 * Math.PI) / 180);
  for (const s of scans) { if (s >= mesh.count) continue; for (let i = 0; i < mesh.count; i++) if (c[i * 3] * c[s * 3] + c[i * 3 + 1] * c[s * 3 + 1] + c[i * 3 + 2] * c[s * 3 + 2] > cos) mask[i] = 1; }
  return mask;
}
export function syncReveal() {
  const g = useGameStore.getState(), p = usePlanetStore.getState();
  const needsMask = p.layer !== null && !BASE_LAYERS.includes(p.layer) && !g.revealAll && p.frame;
  p.set({ revealed: needsMask ? buildRevealMask(p.frame!.level, g.scans) : null });
}

export const useGameStore = create<GameStore>((set, get) => {
  const save = () => { const { hydrated: _h, notices: _n, ...s } = get(); void idbSet(KEY, JSON.parse(JSON.stringify(s))); };
  return {
    hydrated: false, started: false, scenarioId: "genesis", seed: 7, params: {},
    resources: { ...START_RES }, cooldowns: {}, unlocked: ["sci.habitableZone", "tech.scanner"], stats: { ...EMPTY_STATS }, achievements: [], missionsDone: [],
    codex: [], known: [], diary: [], scans: [], revealAll: false, predictions: [], notices: [], tutorLog: [],
    onboarding: 0, attempts: 0, lastActionTick: 0, reportEra: null, collapsed: false, playerLevel: 0,

    async start(scenarioId, params = {}, seed) {
      const attempts = get().attempts + 1, wasCollapsed = get().collapsed;
      set({
        started: true, scenarioId, params, seed: seed ?? params.seed ?? 7, resources: { ...START_RES }, cooldowns: {}, predictions: [], notices: [], diary: [], scans: [], known: [],
        attempts, lastActionTick: 0, reportEra: null, collapsed: false, stats: { ...get().stats, collapses: get().stats.collapses },
      });
      if (wasCollapsed) set({ stats: { ...get().stats, recoveries: get().stats.recoveries } });
      await usePlanetStore.getState().init({ scenarioId, level: 5, seed, params });
      save();
    },
    async resume() {
      if (get().hydrated) return;
      const saved = await idbGet<Partial<GameStore>>(KEY);
      set({ ...(saved ?? {}), hydrated: true, notices: [] });
      const g = get();
      if (g.started && usePlanetStore.getState().status === "idle") await usePlanetStore.getState().init({ scenarioId: g.scenarioId, level: 5, seed: g.seed, params: g.params });
    },
    canAfford(id) {
      const def = INTERVENTION_BY_ID[id], r = get().resources;
      return Object.entries(def.cost).every(([k, v]) => r[k as ResourceId] >= (v ?? 0));
    },
    apply(id, opts) {
      const def = INTERVENTION_BY_ID[id], frame = usePlanetStore.getState().frame, g = get();
      if (!def || !frame || !g.canAfford(id) || (g.cooldowns[id] ?? 0) > frame.tick) return false;
      if (def.requires && !g.unlocked.includes(def.requires)) return false;
      const resources = { ...g.resources };
      for (const [k, v] of Object.entries(def.cost)) resources[k as ResourceId] -= v ?? 0;
      const patch: Partial<GameStore> = { resources, cooldowns: { ...g.cooldowns, [id]: frame.tick + def.cooldown }, lastActionTick: frame.tick, stats: { ...g.stats, interventions: g.stats.interventions + 1 } };
      // Immediate visual answer at the point of the gesture; the new state arrives afterwards (RNF-002).
      if (opts.cell !== null) feedback.trigger(opts.cell);
      const option = def.options?.find((o) => o.id === opts.optionId) ?? def.options?.[0];
      if (def.kind === "scan" && opts.cell !== null) {
        patch.scans = [...g.scans, opts.cell]; patch.resources = { ...resources, research: resources.research + 2 }; patch.stats = { ...patch.stats!, scans: g.stats.scans + 1 };
        evidence.emit({ type: "scan_done", cells: 1 });
      } else if (def.kind === "study") patch.resources = { ...resources, research: resources.research + 5 };
      else usePlanetStore.getState().command({ type: "intervene", id: `i${frame.tick}-${id}`, kind: def.kind as never, cell: opts.cell ?? undefined, eventType: option?.eventType, role: option?.role, eventId: opts.eventId });
      if (opts.prediction) {
        const pr: Prediction = { id: `p${frame.tick}-${id}`, interventionId: id, variable: opts.prediction.variable, direction: opts.prediction.direction, tick: frame.tick, dueTick: frame.tick + 240, baseline: readVariable(frame, opts.prediction.variable, opts.cell), cell: opts.cell };
        patch.predictions = [...g.predictions, pr]; patch.stats = { ...patch.stats!, predictions: g.stats.predictions + 1 };
        evidence.emit({ type: "prediction_declared", interventionId: id, variable: pr.variable, direction: pr.direction });
      }
      evidence.emit({ type: "intervention_applied", interventionId: id, hadPrediction: !!opts.prediction });
      set(patch); syncReveal(); save();
      return true;
    },
    unlock(nodeId) {
      const node = RESEARCH_BY_ID[nodeId], g = get();
      if (!node || g.unlocked.includes(nodeId) || node.requires.some((r) => !g.unlocked.includes(r)) || node.mastery(g.stats) < 1 || g.resources.research < node.cost) return false;
      set({ unlocked: [...g.unlocked, nodeId], resources: { ...g.resources, research: g.resources.research - node.cost } }); save();
      return true;
    },
    inspect(lineageId) {
      const g = get();
      evidence.emit({ type: "species_inspected", lineageId });
      if (!g.codex.includes(lineageId)) { set({ codex: [...g.codex, lineageId], stats: { ...g.stats, speciesInspected: [...g.stats.speciesInspected, lineageId] }, resources: { ...g.resources, research: g.resources.research + 1 } }); save(); }
    },
    notify(n) { set({ notices: [...get().notices.slice(-5), { ...n, id: `n${++noticeSeq}`, tick: usePlanetStore.getState().frame?.tick ?? 0 }] }); },
    dismiss(id) { set({ notices: get().notices.filter((n) => n.id !== id) }); },
    patch(p) { set(p); save(); },

    /** Game rules that react to the observed state. Read-only with respect to the world (principle 2). */
    onFrame(frame, prev) {
      const g = get(), gl = frame.globals;
      if (!g.started) return;
      evidence.setContext(frame.tick, gl.era);
      const stats = { ...g.stats }, patch: Partial<GameStore> = {};
      const dt = prev ? Math.max(0, frame.tick - prev.tick) : 0;
      const resources = { ...g.resources, energy: Math.min(100, g.resources.energy + dt * 0.12), budget: Math.min(100, g.resources.budget + dt * 0.03 * (0.4 + gl.prosperity)) };
      const diary = [...g.diary];
      if (prev && prev.globals.era !== gl.era && frame.tick > prev.tick) {
        resources.actionPoints = MAX_AP; resources.research += 3;
        diary.push({ tick: frame.tick, era: gl.era, key: "diary.newEra", params: { era: gl.era } });
        patch.reportEra = prev.globals.era;
        g.notify({ key: "notice.newEra", params: { era: gl.era }, tone: "success", icon: "flag", action: { type: "report" } });
      }
      stats.maxEra = Math.max(stats.maxEra, gl.era); stats.maxLevels = Math.max(stats.maxLevels, frame.bio.trophicLevels);
      const sensors = g.unlocked.includes("tech.sensors");
      for (const e of frame.events) {
        if (e.origin === "background") continue;
        const was = prev?.events.find((x) => x.id === e.id)?.phase;
        if (e.phase === "telegraph" && was !== "telegraph" && sensors) g.notify({ key: "notice.telegraph", params: { name: e.type, instrument: e.instrument }, tone: "warning", icon: "telescope", action: { type: "focus", ref: e.cell } });
        if (e.phase === "active" && was !== "active") {
          if (!stats.eventsWitnessed.includes(e.type)) stats.eventsWitnessed = [...stats.eventsWitnessed, e.type];
          diary.push({ tick: frame.tick, era: gl.era, key: "diary.event", params: { name: e.type } });
          g.notify({ key: "notice.event", params: { name: e.type }, tone: "danger", icon: e.type, action: { type: "why", ref: e.id } });
          if (e.type === "glaciation") stats.iceAgeSeen = true;
        }
      }
      if (stats.iceAgeSeen && !stats.iceAgeReverted && prev?.events.some((e) => e.type === "glaciation") && !frame.events.some((e) => e.type === "glaciation")) stats.iceAgeReverted = true;
      // New lineages are announced; the Códex entry is filled when the student investigates it.
      const known = [...g.known];
      for (const s of frame.bio.species) if (s.alive && !known.includes(s.id)) {
        known.push(s.id);
        if (prev && known.length <= 40) { g.notify({ key: s.role === "phototroph" && s.realm === "water" ? "notice.bloom" : "notice.newLineage", params: { name: s.name }, tone: "info", icon: "leaf", action: { type: "species", ref: s.id } }); diary.push({ tick: frame.tick, era: gl.era, key: "diary.lineage", params: { name: s.name } }); }
      }
      if (prev) for (const s of frame.bio.species) { const before = prev.bio.species.find((x) => x.id === s.id); if (before?.alive && !s.alive && g.known.includes(s.id)) diary.push({ tick: frame.tick, era: gl.era, key: "diary.extinction", params: { name: s.name } }); }
      // Predictions come due: compare what was expected with what happened.
      const predictions = g.predictions.map((p) => {
        if (p.result || frame.tick < p.dueTick) return p;
        const value = readVariable(frame, p.variable, p.cell), observed = directionOf(p.baseline, value), match = observed === p.direction;
        evidence.emit({ type: "prediction_compared", interventionId: p.interventionId, variable: p.variable, predicted: p.direction, observed, match });
        if (match) stats.correctPredictions++;
        g.notify({ key: match ? "notice.predictionMatch" : "notice.predictionDiffer", params: { variable: p.variable }, tone: match ? "success" : "info", icon: "target", action: { type: "prediction", ref: p.id } });
        return { ...p, result: { observed, match, value } };
      });
      // Collapse is a legitimate outcome: explain it and offer a safe restart (RP-010).
      const hadLife = (prev?.bio.richness ?? 0) > 0;
      if (!g.collapsed && ((hadLife && frame.bio.richness === 0) || (prev && prev.globals.viability > 0.05 && gl.viability <= 0.05 && frame.params.lifeSeed && gl.era >= 4))) {
        patch.collapsed = true; stats.collapses++;
        g.notify({ key: "notice.collapse", tone: "danger", icon: "alert", action: { type: "why" } });
      }
      if (g.collapsed && frame.bio.richness >= 3) { patch.collapsed = false; stats.recoveries++; evidence.emit({ type: "collapse_recovered", scenarioId: g.scenarioId, attempts: g.attempts }); }
      const missionsDone = [...g.missionsDone];
      for (const m of MISSIONS) if (!missionsDone.includes(m.id) && m.progress(frame, stats) >= 1) {
        missionsDone.push(m.id); resources.research += 4; evidence.emit({ type: "mission_goal_met", missionId: m.id });
        if (prev) g.notify({ key: "notice.mission", params: { id: m.id }, tone: "success", icon: "target" });
      }
      const achievements = [...g.achievements];
      for (const a of ACHIEVEMENTS) if (!achievements.includes(a.id) && a.earned(stats)) { achievements.push(a.id); g.notify({ key: "notice.achievement", params: { id: `achievement.${a.id}.name` }, tone: "success", icon: a.icon }); }
      // Simulated assessment output. In production the level comes from the stealth assessment, not from the client.
      const score = stats.correctPredictions * 2 + stats.chartsOpened + stats.scans + stats.speciesInspected.length + missionsDone.length * 2;
      patch.playerLevel = score >= 40 ? 3 : score >= 20 ? 2 : score >= 8 ? 1 : 0;
      set({ ...patch, stats, resources, predictions, missionsDone, achievements, known, diary: diary.slice(-80) });
      if (dt > 0 && Math.floor(frame.tick / 120) !== Math.floor((prev?.tick ?? 0) / 120)) save();
    },
  };
});
