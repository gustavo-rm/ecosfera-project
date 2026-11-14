/**
 * Synthetic engine: a deterministic, scripted stand-in for the real Evolution Engine.
 * "DADOS SINTÉTICOS, APENAS PARA DESENVOLVIMENTO". It reproduces the FORM of the data the spec describes
 * (§24.5 scenarios, homeocaos regime), it is not a simulation and it claims no scientific validity.
 * Every formula here is a PLACEHOLDER to be replaced by the engine's output.
 *
 * frameAt(tick) is a pure function of (scenario, seed, params, overrides, modifiers, tick).
 */
import { fbm3, noise3 } from "../../math/noise";
import { clamp, gauss, hash4, hashString, lerp, smoothstep } from "../../math/rng";
import { getMesh, latLonToDir, nearestCell, type GeodesicMesh } from "../../mesh/geodesic";
import { Biome, DEFAULT_PARAMS, EVENT_DEFS, GENES, ROLE_TROPHIC, STAR_TABLE } from "../../state/catalogs";
import type {
  Archetype, BioFlag, BiosphereFrame, CellFields, CycleDiagram, DetailLevel, EraId, EventType, FoodWebLink, Globals, PlanetEvent,
  PlanetFrame, PlanetParams, SeriesHistory, SpeciesRecord, TimelineMark, TrophicRole, UpdateMode,
} from "../../state/types";
import { SCENARIOS, type EventScript, type LineageScript, type ScenarioDef } from "./scenarios";
import { buildTerrain, oceanMoisture, seaLevelFor, type Terrain } from "./terrain";

/** Live overrides used by the lab console to test each row of the state→appearance table in isolation. */
export interface StateOverrides {
  o2Pct?: number; co2Ppm?: number; ch4Ppm?: number; aerosols?: number; pressureBar?: number; waterFraction?: number;
  tempOffset?: number; surfaceHeat?: number; humidityScale?: number; biomassScale?: number; fertilityScale?: number;
  organicStuck?: number; extinctionPulse?: number; magneticField?: number; starActivity?: number; yearPhase?: number;
  salinityPpt?: number; oceanPh?: number; richnessScale?: number;
}
export type ModifierKind = "event" | "suppress" | "reforest" | "fertilize" | "irrigate" | "cool" | "warm" | "barrier" | "introduce";
export interface Modifier { id: string; kind: ModifierKind; tick: number; cell?: number; eventType?: EventType; eventId?: string; role?: TrophicRole; noTelegraph?: boolean }

export interface EngineConfig { scenarioId: string; level: number; seed?: number; params?: Partial<PlanetParams> }

const ZERO = new Map<number, Float32Array>();
const zeros = (n: number) => { let z = ZERO.get(n); if (!z) { z = new Float32Array(n); ZERO.set(n, z); } return z; };
const DEG = Math.PI / 180;
const GENUS: Record<TrophicRole, string[]> = {
  phototroph: ["Viridia", "Lumina", "Phytara"], chemotroph: ["Thermia"], nitrogenFixer: ["Nitra"], decomposer: ["Saprea"],
  detritivore: ["Detrita"], herbivore: ["Pascua", "Herbira", "Foliax"], mixotroph: ["Mixta"], carnivore: ["Raptia", "Venara"],
};
const EPITHET = ["prima", "minor", "lenta", "velox", "alta", "borealis", "australis", "littoralis", "insularis", "nova", "robusta", "tenuis", "vaga", "umbrosa", "arida", "glacialis"];

interface Region { x: number; y: number; z: number; radius: number }

export class SyntheticEngine {
  readonly scenario: ScenarioDef;
  readonly mesh: GeodesicMesh;
  params: PlanetParams;
  overrides: StateOverrides = {};
  modifiers: Modifier[] = [];
  observedLineage: string | null = null;
  private terrain!: Terrain;
  private terrainKey = "";
  private lineages: LineageScript[] = [];
  private lineageIndex = new Map<string, number>();
  private baseDist: number[] = [];
  private regions: Region[] = [];
  private waterCache: { sea: number; isWater: Uint8Array; moisture: Float32Array } | null = null;
  private popMemo = new Map<number, Float64Array>();
  /** Versions of arrays that rarely change, so the transport layer can skip re-sending them. */
  versions = { terrain: 0, water: 0 };

  constructor(readonly config: EngineConfig) {
    this.scenario = SCENARIOS[config.scenarioId] ?? SCENARIOS.genesis;
    this.mesh = getMesh(config.level);
    this.params = { ...DEFAULT_PARAMS, ...this.scenario.params, ...config.params };
    if (config.seed !== undefined) this.params.seed = config.seed;
    this.rebuildLineages();
  }

  setParams(p: Partial<PlanetParams>) { this.params = { ...this.params, ...p }; this.popMemo.clear(); }
  setOverrides(o: StateOverrides) { this.overrides = o; }
  addModifier(m: Modifier) { this.modifiers.push(m); this.rebuildLineages(); }
  removeModifiersAfter(tick: number) { this.modifiers = this.modifiers.filter((m) => m.tick <= tick); this.rebuildLineages(); }

  private rebuildLineages() {
    const extra: LineageScript[] = [];
    for (const m of this.modifiers) {
      if (m.kind === "introduce" && m.role) {
        const land = m.cell !== undefined; // placed on the chosen cell
        extra.push({
          id: `intro-${m.id}`, parent: null, origin: m.tick, mode: "introduced", role: m.role, realm: m.role === "phototroph" && land ? "both" : "both",
          level: ROLE_TROPHIC[m.role], tempOpt: 18, tempBreadth: 13, cap: m.role === "carnivore" ? 30 : m.role === "herbivore" ? 140 : 380,
          growth: 500, period: 200, amp: 0.2, phase: m.tick * 0.01, mass: m.role === "carnivore" ? 5 : m.role === "herbivore" ? 0.5 : 0.01,
          mobility: m.role === "phototroph" ? 0 : 0.6, founder: true,
          prey: m.role === "herbivore" ? this.scenario.lineages.filter((l) => l.role === "phototroph").map((l) => l.id) : m.role === "carnivore" ? this.scenario.lineages.filter((l) => l.role === "herbivore").map((l) => l.id) : undefined,
        });
      }
      if (m.kind === "barrier") {
        const parent = this.scenario.lineages.find((l) => l.role === "phototroph" && l.realm === "land") ?? this.scenario.lineages.find((l) => l.role === "phototroph");
        if (parent) extra.push({ ...parent, id: `split-${m.id}`, parent: parent.id, origin: m.tick + 600, extinct: undefined, cause: undefined, mode: "allopatric", cap: parent.cap * 0.5, phase: parent.phase + 2, tempOpt: parent.tempOpt + 3, founder: true, factor: undefined });
      }
    }
    this.lineages = [...this.scenario.lineages, ...extra];
    this.lineageIndex = new Map(this.lineages.map((l, i) => [l.id, i]));
    this.baseDist = this.lineages.map(() => 0);
    this.lineages.forEach((l, i) => {
      const pi = l.parent ? this.lineageIndex.get(l.parent) : undefined;
      if (pi !== undefined) this.baseDist[i] = this.baseDist[pi] + this.rate(this.lineages[pi]) * Math.max(0, l.origin - this.lineages[pi].origin) + 0.35;
    });
    this.popMemo.clear();
  }
  private rate(l: LineageScript) { return (l.asexual ? 7e-5 : 5e-5) * (l.founder ? 1.5 : 1); }

  // ---------------------------------------------------------------- time
  eraAt(tick: number): { era: EraId; start: number; end: number } {
    const e = this.scenario.eras;
    let k = 0;
    for (let i = 0; i < e.length; i++) if (tick >= e[i].start) k = i;
    return { era: e[k].era, start: e[k].start, end: k + 1 < e.length ? e[k + 1].start : this.scenario.endTick };
  }
  private eraStart(era: EraId, fallback: number) { return this.scenario.eras.find((e) => e.era === era)?.start ?? fallback; }

  // ---------------------------------------------------------------- events
  private eventScripts(tick: number): EventScript[] {
    const list: EventScript[] = [...this.scenario.events];
    for (const m of this.modifiers) {
      if (m.kind === "event" && m.eventType) list.push({ id: m.id, type: m.eventType, tick: m.tick + (m.noTelegraph ? 0 : EVENT_DEFS[m.eventType].telegraph), lat: this.mesh.latitude[m.cell ?? 0], lon: this.mesh.longitude[m.cell ?? 0], noTelegraph: m.noTelegraph, origin: "student" });
      if (m.kind === "fertilize" && m.cell !== undefined) list.push({ id: `eutro-${m.id}`, type: "eutrophication", tick: m.tick + 240, lat: this.mesh.latitude[m.cell], lon: this.mesh.longitude[m.cell], intensity: 0.7, origin: "student" });
    }
    // Background disturbances (DEC-15): many small ones, few large ones.
    const hasAir = this.params.pressureBar > 0.05 && this.eraAt(tick).era >= 2;
    if (hasAir) {
      for (let b = Math.floor(tick / 60) - 1; b <= Math.floor(tick / 60) + 1; b++) {
        if (b < 0 || hash4(b, this.params.seed, 17, 3) > 0.45) continue;
        const cell = Math.floor(hash4(b, this.params.seed, 5, 9) * this.mesh.count);
        const type: EventType = hash4(b, this.params.seed, 2, 2) < 0.5 && this.eraAt(tick).era >= 6 ? "fire" : "storm";
        list.push({ id: `bg-${b}`, type, tick: b * 60 + 12, lat: this.mesh.latitude[cell], lon: this.mesh.longitude[cell], intensity: 0.35 + 0.4 * hash4(b, 1, 1, this.params.seed), origin: "background" });
      }
    }
    return list;
  }

  eventsAt(tick: number): PlanetEvent[] {
    const out: PlanetEvent[] = [];
    const suppressed = new Set(this.modifiers.filter((m) => m.kind === "suppress" && m.tick <= tick).map((m) => m.eventId));
    for (const s of this.eventScripts(tick)) {
      const def = EVENT_DEFS[s.type];
      const lead = s.noTelegraph || s.origin === "background" ? 0 : def.telegraph;
      const start = s.tick, end = s.tick + def.duration, after = end + def.duration * 0.6;
      if (tick < start - lead || tick > after) continue;
      const base = (s.intensity ?? 1) * (suppressed.has(s.id) ? 0.15 : 1);
      let phase: PlanetEvent["phase"], intensity: number;
      if (tick < start) { phase = "telegraph"; intensity = 0; }
      else if (tick <= end) { phase = "active"; intensity = base * Math.min(1, (tick - start + 1) / (def.duration * 0.15)); }
      else { phase = "aftermath"; intensity = base * 0.45 * (1 - (tick - end) / (def.duration * 0.6)); }
      const d = latLonToDir(s.lat, s.lon);
      out.push({
        id: s.id, type: s.type, scale: s.origin === "background" ? "local" : def.scale, cell: nearestCell(this.mesh, d[0], d[1], d[2]), lat: s.lat, lon: s.lon,
        radiusDeg: def.radiusDeg * (s.origin === "background" ? 0.6 : 1), intensity, phase, startTick: start, endTick: end, telegraphTick: start - lead,
        instrument: def.instrument, causalChain: def.chain, origin: s.origin ?? "engine", suppressed: suppressed.has(s.id),
      });
    }
    return out;
  }

  // ---------------------------------------------------------------- biosphere (global, no cell loop)
  private viability(tempC: number, oceanFraction: number, pressure: number) {
    if (!this.params.lifeSeed) return 0;
    return smoothstep(-22, -6, tempC) * (1 - smoothstep(48, 66, tempC)) * smoothstep(0.02, 0.1, oceanFraction) * smoothstep(0.05, 0.25, pressure);
  }
  private stuckAt(tick: number) {
    if (this.overrides.organicStuck !== undefined) return this.overrides.organicStuck;
    return this.scenario.stuckFrom === undefined ? 0 : smoothstep(this.scenario.stuckFrom, this.scenario.stuckFrom + 1800, tick);
  }

  /** Population (thousands of individuals, placeholder unit) of every lineage at a tick. */
  populations(tick: number, depth = 0): Float64Array {
    const key = Math.round(tick);
    const memo = this.popMemo.get(key);
    if (memo) return memo;
    const ls = this.lineages, out = new Float64Array(ls.length);
    const stuck = this.stuckAt(tick);
    const events = depth === 0 || depth === 1 ? this.eventScripts(tick) : [];
    const env = this.envFactor(tick);
    for (let i = 0; i < ls.length; i++) {
      const l = ls[i];
      if (tick < l.origin || (l.extinct !== undefined && tick >= l.extinct)) continue;
      const age = tick - l.origin;
      const grow = 1 / (1 + Math.exp(-(age - l.growth * 0.5) / (l.growth * 0.12)));
      const seedN = hashString(l.id) % 1000;
      const erratic = noise3(tick / (l.period * 0.41), seedN, 0.5, this.params.seed) * 2 - 1;
      const slow = noise3(tick / (l.period * 2.7), seedN, 7.5, this.params.seed) * 2 - 1;
      // Consumers follow their first prey a quarter of a cycle behind (out-of-phase predator-prey oscillation, §21.1).
      const lead = l.prey ? ls[this.lineageIndex.get(l.prey[0]) ?? i] : l;
      const wave = Math.sin((2 * Math.PI * tick) / lead.period + lead.phase - (l.prey ? Math.PI / 2 : 0));
      let pop = l.cap * grow * Math.max(0.05, 1 + l.amp * wave + l.amp * 0.5 * erratic + l.amp * 0.6 * slow);
      if (l.prey && depth < 2) {
        const prev = this.populations(tick - l.period / 4, depth + 1);
        let f = 0, cnt = 0;
        for (const id of l.prey) { const j = this.lineageIndex.get(id); if (j !== undefined && tick - l.period / 4 >= ls[j].origin) { f += prev[j] / ls[j].cap; cnt++; } }
        if (cnt) pop *= clamp(Math.pow(Math.max(0, (f / cnt) * 1.6), 0.7), 0, 1.25);
      }
      if (l.level === 0 && l.role !== "decomposer") pop *= 1 - 0.93 * stuck;
      for (const e of events) {
        if (tick < e.tick) continue;
        const dt = tick - e.tick;
        if (e.type === "impact") pop *= 1 - (0.45 + 0.5 * (l.fragile ?? (l.mass > 1 ? 0.6 : 0.2))) * Math.exp(-dt / 500);
        else if (e.type === "glaciation" && dt < 1500) pop *= 1 - 0.5 * clamp((l.tempOpt - 6) / 25) * Math.sin(Math.min(1, dt / 900) * Math.PI);
        else if (e.type === "volcanism" && e.origin !== "background") pop *= 1 - 0.18 * Math.exp(-dt / 200);
        else if (e.type === "pandemic" && l.level === 1) pop *= 1 - 0.5 * Math.exp(-dt / 150);
      }
      if (l.extinct !== undefined) pop *= clamp((l.extinct - tick) / 140);
      if (l.factor) pop *= keyframes(l.factor, tick);
      out[i] = pop * env * (this.overrides.biomassScale ?? 1);
    }
    if (this.popMemo.size > 4000) this.popMemo.clear();
    this.popMemo.set(key, out);
    return out;
  }
  private envFactor(tick: number) {
    const a = this.atmosphereAt(tick, 1, false);
    return this.viability(a.meanTempC, a.oceanFraction, a.pressureBar);
  }

  /** Global atmosphere, climate and ocean values. PLACEHOLDER energy balance. */
  private atmosphereAt(tick: number, producersNorm: number, withEvents = true) {
    const p = this.params, o = this.overrides, sc = this.scenario;
    const e2 = this.eraStart(2, 0), e4 = this.eraStart(4, 0), e6 = this.eraStart(6, 0);
    const primitive = sc.primordial ? 1 - smoothstep(e4, e6, tick) : 0;
    const surfaceHeat = o.surfaceHeat ?? (sc.primordial ? 1 - smoothstep(0, e2 * 0.95, tick) : 0);
    const oceanFill = sc.primordial ? smoothstep(e2 * 0.85, e2 + 0.75 * (this.eraStart(3, e2 + 1200) - e2), tick) : 1;
    let aerosols = o.aerosols ?? 0, glaciation = 0;
    if (withEvents) {
      for (const e of this.eventsAt(tick)) {
        if (e.type === "volcanism") aerosols += 0.4 * e.intensity * (e.origin === "background" ? 0.2 : 1);
        if (e.type === "impact") aerosols += 0.95 * (e.phase === "active" ? Math.max(e.intensity, 0.5) : e.intensity * 1.6);
        if (e.type === "fire") aerosols += 0.03 * e.intensity;
        if (e.type === "glaciation") glaciation = Math.max(glaciation, e.phase === "active" ? e.intensity : e.intensity * 1.5);
      }
    }
    let cool = 0, co2Extra = 0;
    for (const m of this.modifiers) {
      const dt = tick - m.tick;
      if (dt < 0) continue;
      if (m.kind === "cool") { cool += 2.5 * Math.exp(-dt / 500); aerosols += 0.08 * Math.exp(-dt / 500); }
      if (m.kind === "warm") co2Extra += 180 * Math.exp(-dt / 3000);
      if (m.kind === "reforest") co2Extra -= 12 * (1 - Math.exp(-dt / 400));
    }
    aerosols = clamp(aerosols);
    const erosion = clamp((0.25 - (o.magneticField ?? p.magneticField)) / 0.25) * (o.starActivity ?? p.starActivity) * 0.75 * clamp(tick / 6000 + (sc.primordial ? 0 : 1));
    const pressureBar = o.pressureBar ?? p.pressureBar * (sc.primordial ? 0.4 + 0.6 * smoothstep(0, e2, tick) : 1) * (1 - erosion);
    const o2Pct = o.o2Pct ?? p.o2Pct * (1 - primitive) * (0.2 + 0.8 * clamp(producersNorm));
    const co2Ppm = Math.max(1, o.co2Ppm ?? p.co2Ppm * (1 + 30 * primitive) + co2Extra);
    const ch4Ppm = o.ch4Ppm ?? p.ch4Ppm * (1 + 100 * primitive);
    const star = STAR_TABLE[p.starType];
    const starFlux = (star.luminosity * (0.72 + 0.28 * clamp(p.starAgeGyr / 4.6, 0, 1.6))) / (p.orbitAU * p.orbitAU) * (sc.primordial ? 1 - 0.2 * primitive : 1);
    const teq = 278.5 * Math.pow(Math.max(0, starFlux * (1 - p.albedo)) / 0.7 * 0.7, 0.25) - 273.15;
    const gh = Math.max(0, 33 * Math.min(1.7, Math.pow(pressureBar, 0.4)) * (1 + 0.15 * Math.log2(co2Ppm / 400))) + (pressureBar > 0 ? 4 * Math.log10(1 + ch4Ppm / 1.8) : 0);
    let meanTempC = teq + gh - 13 * aerosols - 18 * glaciation - cool + (o.tempOffset ?? 0);
    const waterParam = o.waterFraction ?? p.waterFraction;
    if (meanTempC > 50 && waterParam > 0.02 && pressureBar > 0.05) meanTempC += (meanTempC - 50) * 1.2; // water-vapor feedback
    meanTempC += 1100 * surfaceHeat * surfaceHeat;
    const boil = smoothstep(70, 125, meanTempC);
    const oceanFraction = surfaceHeat > 0.35 ? 0 : waterParam * oceanFill * (1 - boil) * (1 - 0.08 * glaciation) * (pressureBar < 0.006 ? 0 : 1);
    return { primitive, surfaceHeat, aerosols, glaciation, pressureBar, o2Pct, co2Ppm, ch4Ppm, starFlux, meanTempC, boil, oceanFraction, waterParam, erosion };
  }

  private producersNorm(pops: Float64Array) {
    let s = 0, c = 0;
    this.lineages.forEach((l, i) => { if (l.level === 0 && l.role === "phototroph") { s += pops[i]; c += l.cap; } });
    return c ? clamp((s / c) * 2.2) : 0;
  }

  bioAt(tick: number, pops: Float64Array, a: ReturnType<SyntheticEngine["atmosphereAt"]>): BiosphereFrame {
    const ls = this.lineages;
    const species: SpeciesRecord[] = [];
    let total = 0, wDist = 0, alive = 0;
    const strategies = new Set<number>();
    for (let i = 0; i < ls.length; i++) total += pops[i];
    for (let i = 0; i < ls.length; i++) {
      const l = ls[i];
      if (tick < l.origin) continue;
      const isAlive = pops[i] > l.cap * 0.004;
      const endT = l.extinct !== undefined ? Math.min(tick, l.extinct) : tick;
      const dist = this.baseDist[i] + this.rate(l) * (endT - l.origin);
      const rec = this.record(l, i, pops[i], isAlive, dist, tick);
      species.push(rec);
      if (isAlive) {
        alive++; wDist += dist * pops[i];
        if (pops[i] > total * 0.02) strategies.add(capabilityMask(l.role));
      }
    }
    const living = species.filter((s) => s.alive);
    let shannon = 0;
    const livingTotal = living.reduce((s, x) => s + x.population, 0);
    for (const s of living) { const q = s.population / livingTotal; if (q > 0) shannon -= q * Math.log(q); }
    const links: FoodWebLink[] = [];
    const aliveIds = new Set(living.map((s) => s.id));
    for (const s of living) {
      for (const prey of s.preyIds) if (aliveIds.has(prey)) {
        const pj = this.lineageIndex.get(prey)!;
        links.push({ from: prey, to: s.id, flux: 0.1 * Math.sqrt((pops[pj] / ls[pj].cap) * (s.population / ls[s.index].cap)), kind: "trophic" });
      }
      const next = s.cycleIds[0];
      if (next && aliveIds.has(next) && s.cycleIds.every((c) => aliveIds.has(c))) links.push({ from: s.id, to: next, flux: 0.03, kind: "cycle" });
    }
    const levels = living.reduce((m, s) => Math.max(m, s.trophicLevel), -1) + 1;
    const pyramid: number[] = [];
    for (let k = 0; k < Math.max(levels, 1); k++) {
      const at = living.filter((s) => s.trophicLevel === k);
      const norm = at.reduce((sum, s) => sum + s.population / ls[s.index].cap, 0) / Math.max(1, Math.sqrt(at.length));
      pyramid.push(1000 * Math.pow(0.1, k) * norm); // PLACEHOLDER: about 10% passes to the next level (§8.1)
    }
    let orig = 0, ext = 0, recentExt = 0;
    for (const l of ls) {
      if (l.origin > tick - 1000 && l.origin <= tick && l.origin > this.scenario.eras[0].start - 1) orig++;
      if (l.extinct !== undefined && l.extinct <= tick) { if (l.extinct > tick - 1000) ext++; if (l.extinct > tick - 300) recentExt++; }
    }
    const flags: BioFlag[] = [];
    for (const l of ls) {
      if (l.founder && l.origin <= tick && l.origin >= this.scenario.eras[0].start) flags.push({ type: "founder", lineageId: l.id, tick: l.origin });
      if (l.bottleneck !== undefined && l.bottleneck <= tick && (l.extinct === undefined || l.extinct > tick)) flags.push({ type: "bottleneck", lineageId: l.id, tick: l.bottleneck });
    }
    const cycleLinks = links.filter((x) => x.kind === "cycle").length;
    return {
      species, links, pyramid, shannon, richness: alive, evenness: alive > 1 ? shannon / Math.log(alive) : 0,
      geneticDistance: livingTotal ? wDist / livingTotal : 0, metabolicStrategies: strategies.size, trophicLevels: levels,
      connectance: alive > 1 ? links.length / (alive * (alive - 1)) : 0, intransitiveShare: links.length ? cycleLinks / links.length : 0,
      originationRate: orig, extinctionRate: ext, massExtinction: recentExt >= 3, flags, cycles: this.cycles(a, pops),
    };
  }

  private record(l: LineageScript, index: number, population: number, alive: boolean, geneticDistance: number, tick: number): SpeciesRecord {
    const h = hashString(l.id + this.params.seed);
    const j = (k: number) => hash4(h, k, 3, 1);
    const ph: Record<string, number | number[]> = {};
    const has = (roles: TrophicRole[]) => (roles.includes(l.role) ? 1 : 0);
    const consumer = l.level >= 1;
    for (const gdef of GENES) {
      const k = hashString(gdef.id) % 997;
      if (gdef.kind === "sym") { ph[gdef.id] = Array.from({ length: gdef.id === "neutral_marker" ? 4 : 6 }, (_, s) => Math.floor(hash4(h, k, s, 11) * 8)); continue; }
      if (gdef.kind === "bool") { ph[gdef.id] = 0; continue; }
      const lo = gdef.min ?? 0, hi = gdef.max ?? 1;
      ph[gdef.id] = gdef.log ? Math.exp(lerp(Math.log(lo), Math.log(hi), 0.3 + 0.4 * j(k))) : lerp(lo, hi, 0.25 + 0.5 * j(k));
      if (gdef.kind === "int") ph[gdef.id] = Math.round(ph[gdef.id] as number);
    }
    Object.assign(ph, {
      photosynthesis: has(["phototroph", "mixotroph"]), chemosynthesis: has(["chemotroph"]), plant_digestion: has(["herbivore", "mixotroph"]),
      animal_digestion: has(["carnivore"]), detritivory: has(["detritivore"]), decomposition: has(["decomposer"]), nitrogen_fixation: has(["nitrogenFixer"]),
      aerobic_respiration: l.origin > (this.scenario.primordial ? 5600 : -1e9) || consumer ? 1 : 0, anaerobic_respiration: l.asexual ? 1 : 0,
      adult_mass: l.mass, mobility: l.mobility, temp_optimum: l.tempOpt, temp_breadth: l.tempBreadth,
      humidity_optimum: l.humOpt ?? 0.6, reproductive_mode: l.asexual ? 0 : j(77) < 0.3 ? 2 : 1, dormancy_capable: l.level === 0 && j(78) < 0.6 ? 1 : 0,
      offense_investment: l.role === "carnivore" ? 0.5 + 0.4 * j(79) : 0.1 * j(79), w_attack: l.role === "carnivore" ? 0.6 + 0.3 * j(80) : 0.05,
      w_flee: l.role === "herbivore" ? 0.6 + 0.3 * j(81) : 0.2 * j(81), w_move: l.mobility * (0.6 + 0.4 * j(82)),
      height: l.realm === "land" && l.level === 0 ? clamp(Math.pow(l.mass, 0.5) * 2, 0.02, 60) : 0.01 + j(83) * 0.3,
      offspring_count: Math.round(clamp(40 / Math.pow(l.mass + 0.001, 0.45), 1, 1000)), offspring_investment: clamp(0.02 + 0.08 * Math.log10(l.mass + 1.001) + 0.03 * j(84), 0.01, 0.5),
    });
    const pi = l.parent ? this.lineageIndex.get(l.parent) : undefined;
    const region = l.regionIndex !== undefined ? this.regions[l.regionIndex] : undefined;
    return {
      id: l.id, index, name: `${GENUS[l.role][h % GENUS[l.role].length]} ${EPITHET[(h >>> 5) % EPITHET.length]}`, parentId: pi !== undefined ? l.parent : null,
      role: l.role, trophicLevel: l.level, realm: l.realm, originTick: l.origin, extinctTick: l.extinct !== undefined && tick >= l.extinct ? l.extinct : null,
      extinctionCause: l.extinct !== undefined && tick >= l.extinct ? l.cause ?? "ENVIRONMENTAL" : null, speciationMode: l.mode,
      originLat: region ? Math.asin(region.y) / DEG : (j(90) - 0.5) * 100, originLon: region ? Math.atan2(region.z, region.x) / DEG : (j(91) - 0.5) * 360,
      asexual: !!l.asexual, founderEffect: !!l.founder, phenotype: ph, preyIds: l.prey ?? [], cycleIds: l.cycle ?? [], geneticDistance, population, alive,
    };
  }

  /** PLACEHOLDER stocks and flows in relative units, enough to animate the cycle diagrams from the same state. */
  private cycles(a: ReturnType<SyntheticEngine["atmosphereAt"]>, pops: Float64Array): CycleDiagram[] {
    const ls = this.lineages;
    let prod = 0, cons = 0, dec = 0, fix = 0;
    ls.forEach((l, i) => {
      const n = pops[i] / l.cap;
      if (l.role === "decomposer" || l.role === "detritivore") dec += n; else if (l.role === "nitrogenFixer") fix += n; else if (l.level === 0) prod += n; else cons += n;
    });
    const stuck = this.stuckAt(this.lastTick);
    const photo = prod * 10, resp = (prod * 4 + cons * 3 + dec * 2), decomp = dec * 5 * (1 - stuck), volc = this.params.volcanism * 2 + a.aerosols * 6;
    return [
      { element: "carbon", stocks: [{ id: "atmosphere", value: a.co2Ppm / 4 }, { id: "biomass", value: (prod + cons) * 40 }, { id: "organic", value: 30 + 400 * stuck + dec * 5 }, { id: "ocean", value: 380 * a.oceanFraction }, { id: "rock", value: 900 }],
        fluxes: [{ id: "photosynthesis", from: "atmosphere", to: "biomass", value: photo }, { id: "respiration", from: "biomass", to: "atmosphere", value: resp }, { id: "death", from: "biomass", to: "organic", value: prod * 3 + cons * 2 }, { id: "decomposition", from: "organic", to: "atmosphere", value: decomp }, { id: "volcanism", from: "rock", to: "atmosphere", value: volc }, { id: "dissolution", from: "atmosphere", to: "ocean", value: 2 * a.oceanFraction }] },
      { element: "nitrogen", stocks: [{ id: "atmosphere", value: 780 * a.pressureBar }, { id: "soil", value: 60 * this.params.nutrients * (1 - 0.9 * stuck) }, { id: "biomass", value: (prod + cons) * 8 }, { id: "organic", value: 10 + 90 * stuck }],
        fluxes: [{ id: "fixation", from: "atmosphere", to: "soil", value: fix * 4 }, { id: "uptake", from: "soil", to: "biomass", value: prod * 3 }, { id: "death", from: "biomass", to: "organic", value: prod * 1.5 + cons }, { id: "mineralization", from: "organic", to: "soil", value: decomp * 0.6 }, { id: "denitrification", from: "soil", to: "atmosphere", value: 0.8 }] },
      { element: "oxygen", stocks: [{ id: "atmosphere", value: a.o2Pct * 10 }, { id: "ocean", value: 40 * a.oceanFraction }, { id: "rock", value: 500 }],
        fluxes: [{ id: "photosynthesis", from: "biomassO", to: "atmosphere", value: photo }, { id: "respiration", from: "atmosphere", to: "biomassO", value: resp }, { id: "oxidation", from: "atmosphere", to: "rock", value: 1 + volc * 0.3 }, { id: "dissolution", from: "atmosphere", to: "ocean", value: 1.5 * a.oceanFraction }] },
      { element: "water", stocks: [{ id: "ocean", value: 1000 * a.oceanFraction }, { id: "atmosphere", value: 12 * a.oceanFraction + 200 * a.boil * a.waterParam }, { id: "ice", value: 0 }, { id: "land", value: 30 * a.oceanFraction }],
        fluxes: [{ id: "evaporation", from: "ocean", to: "atmosphere", value: 8 * a.oceanFraction * (1 + a.meanTempC / 40) }, { id: "precipitation", from: "atmosphere", to: "land", value: 3 * a.oceanFraction }, { id: "precipitationOcean", from: "atmosphere", to: "ocean", value: 5 * a.oceanFraction }, { id: "runoff", from: "land", to: "ocean", value: 3 * a.oceanFraction }, { id: "transpiration", from: "land", to: "atmosphere", value: prod * 0.8 }] },
    ];
  }
  private lastTick = 0;

  // ---------------------------------------------------------------- frame
  private ensureTerrain(tick: number) {
    const p = this.params;
    const drift = Math.round(p.tectonics * clamp(tick / 40000) * 0.6 * 40) / 40;
    const key = [p.seed, p.landDistribution, p.relief, p.tectonics, p.volcanism, drift, this.mesh.level].join("|");
    if (key !== this.terrainKey) {
      this.terrain = buildTerrain(this.mesh, p, drift);
      this.terrainKey = key; this.versions.terrain++; this.waterCache = null; this.regions = [];
    }
  }
  private ensureWater(sea: number) {
    if (this.waterCache && Math.abs(this.waterCache.sea - sea) < 2) return this.waterCache;
    const n = this.mesh.count, isWater = new Uint8Array(n), el = this.terrain.elevation;
    for (let i = 0; i < n; i++) isWater[i] = el[i] < sea ? 1 : 0;
    this.waterCache = { sea, isWater, moisture: oceanMoisture(this.mesh, isWater) };
    this.versions.water++;
    return this.waterCache;
  }
  /** Land regions for island scenarios, by farthest-point sampling over land cells. */
  private ensureRegions(isWater: Uint8Array) {
    const want = this.scenario.regions ?? 0;
    if (!want || this.regions.length === want) return;
    const c = this.mesh.centers, land: number[] = [];
    for (let i = 0; i < this.mesh.count; i++) if (!isWater[i]) land.push(i);
    if (!land.length) return;
    const picked = [land[Math.floor(hash4(this.params.seed, 4, 4, 4) * land.length)]];
    while (picked.length < want) {
      let best = land[0], bestD = -1;
      for (const i of land) {
        let d = 2;
        for (const q of picked) d = Math.min(d, 1 - (c[i * 3] * c[q * 3] + c[i * 3 + 1] * c[q * 3 + 1] + c[i * 3 + 2] * c[q * 3 + 2]));
        if (d > bestD) { bestD = d; best = i; }
      }
      picked.push(best);
    }
    this.regions = picked.map((i) => ({ x: c[i * 3], y: c[i * 3 + 1], z: c[i * 3 + 2], radius: 30 * DEG }));
  }

  frameAt(tick: number, mode: UpdateMode = "normal", annualMean = false): PlanetFrame {
    this.lastTick = tick;
    const p = this.params, o = this.overrides, mesh = this.mesh, n = mesh.count, c = mesh.centers;
    this.ensureTerrain(tick);
    const T = this.terrain;
    const pops = this.populations(tick);
    const a = this.atmosphereAt(tick, this.producersNorm(pops));
    const sea = seaLevelFor(T, a.oceanFraction);
    const water = this.ensureWater(sea);
    this.ensureRegions(water.isWater);
    const events = this.eventsAt(tick);
    const era = this.eraAt(tick);
    const yearPhase = o.yearPhase ?? (annualMean ? 0.25 : (tick % 12) / 12);
    const season = annualMean && o.yearPhase === undefined ? 0 : Math.cos(2 * Math.PI * yearPhase);
    const stuck = this.stuckAt(tick);
    const viable = this.viability(a.meanTempC, a.oceanFraction, a.pressureBar);

    const F = (shared?: Float32Array) => shared ?? new Float32Array(n);
    const anyEvent = (t: EventType[]) => events.some((e) => t.includes(e.type) && e.intensity > 0);
    const f: CellFields = {
      elevation: T.elevation, isWater: water.isWater,
      temperature: F(), humidity: F(), precipitation: F(), solarFlux: F(), salinity: F(), ph: F(), o2: F(), co2: F(), soilFertility: F(),
      water: F(), mineral: F(), nitrogen: F(), organicMatter: F(), biomassPhoto: F(), biomassHerb: F(), biomassCarn: F(),
      richness: new Uint8Array(n), domProducer: new Int16Array(n).fill(-1), domHerb: new Int16Array(n).fill(-1), domCarn: new Int16Array(n).fill(-1),
      biome: new Uint8Array(n), ice: F(), cloud: F(), lava: F(), bloom: F(),
      fire: anyEvent(["fire"]) ? F() : zeros(n), drought: anyEvent(["drought"]) ? F() : zeros(n), storm: anyEvent(["storm"]) ? F() : zeros(n),
      ash: anyEvent(["volcanism", "impact", "fire"]) ? F() : zeros(n), eutro: anyEvent(["eutrophication"]) ? F() : zeros(n),
      crater: anyEvent(["impact"]) ? F() : zeros(n), bioMark: anyEvent(["pandemic", "invasive"]) ? F() : zeros(n), observed: null,
    };

    // --- event masks
    for (const e of events) {
      if (e.intensity <= 0 || e.type === "glaciation") continue;
      const d = latLonToDir(e.lat, e.lon), cosR = Math.cos(e.radiusDeg * DEG), r = e.radiusDeg * DEG;
      for (let i = 0; i < n; i++) {
        const dot = c[i * 3] * d[0] + c[i * 3 + 1] * d[1] + c[i * 3 + 2] * d[2];
        if (dot < cosR) continue;
        const ang = Math.acos(Math.min(1, dot)), m = (1 - smoothstep(r * 0.35, r, ang)) * e.intensity;
        switch (e.type) {
          case "fire": if (!water.isWater[i]) { f.fire[i] = Math.max(f.fire[i], m * (0.5 + 0.5 * T.noiseA[i])); f.ash[i] = Math.max(f.ash[i], m * 0.4); } break;
          case "drought": f.drought[i] = Math.max(f.drought[i], m); break;
          case "storm": f.storm[i] = Math.max(f.storm[i], m); break;
          case "volcanism": f.ash[i] = Math.max(f.ash[i], m); if (ang < r * 0.22) f.lava[i] = Math.max(f.lava[i], e.intensity * (1 - ang / (r * 0.22))); break;
          case "impact": { const cr = 1 - smoothstep(r * 0.2, r * 0.45, ang); f.crater[i] = Math.max(f.crater[i], cr * Math.max(e.intensity, 0.6)); f.ash[i] = Math.max(f.ash[i], m); if (e.phase === "active") f.lava[i] = Math.max(f.lava[i], cr * e.intensity * 0.8); break; }
          case "eutrophication": if (water.isWater[i] || water.moisture[i] > 0.6) f.eutro[i] = Math.max(f.eutro[i], m); break;
          default: f.bioMark[i] = Math.max(f.bioMark[i], m);
        }
      }
    }
    for (const h of T.hotspots) f.lava[h] = Math.max(f.lava[h], 0.55 * p.volcanism + 0.2);

    // --- modifiers with a footprint
    let boostVeg: Float32Array | null = null, boostFert: Float32Array | null = null, boostHum: Float32Array | null = null;
    for (const m of this.modifiers) {
      if (m.cell === undefined || tick < m.tick || !["reforest", "fertilize", "irrigate"].includes(m.kind)) continue;
      const k = Math.exp(-(tick - m.tick) / 2400) * Math.min(1, (tick - m.tick + 6) / 60), r = 15 * DEG, cosR = Math.cos(r), ci = m.cell * 3;
      const target = m.kind === "reforest" ? (boostVeg ??= new Float32Array(n)) : m.kind === "fertilize" ? (boostFert ??= new Float32Array(n)) : (boostHum ??= new Float32Array(n));
      for (let i = 0; i < n; i++) {
        const dot = c[i * 3] * c[ci] + c[i * 3 + 1] * c[ci + 1] + c[i * 3 + 2] * c[ci + 2];
        if (dot > cosR) target[i] = Math.max(target[i], k * (1 - smoothstep(r * 0.4, r, Math.acos(Math.min(1, dot)))));
      }
    }

    // --- climate
    const grad = clamp(38 * (1.3 - 0.3 * Math.min(a.pressureBar, 2)), 20, 55) * (1 - 0.6 * a.boil);
    const waterAvail = a.pressureBar < 0.02 ? 0 : Math.min(1, a.oceanFraction * 2.4 + 0.04 + a.boil);
    const tilt = p.axialTiltDeg / 23.5;
    const tAnnual = new Float32Array(n);
    let iceCells = 0, cloudSum = 0;
    for (let i = 0; i < n; i++) {
      const lat = mesh.latitude[i] * DEG, sl = Math.sin(lat), al = Math.abs(sl), isW = water.isWater[i] === 1;
      const elevRel = T.elevation[i] - (sea < -9e4 ? T.sorted[0] : sea);
      const ta = a.meanTempC + 11 - grad * Math.pow(al, 1.6) - (isW ? 0 : 6.5 * Math.max(0, elevRel) / 1000) + (T.noiseA[i] - 0.5) * 3;
      tAnnual[i] = ta;
      const t = ta + tilt * 9 * sl * season * (isW ? 0.35 : 1);
      f.temperature[i] = t;
      const band = 0.45 + 0.4 * Math.cos(6 * lat);
      let hum = (isW ? 0.85 : 0.22 + 0.78 * water.moisture[i]) * (0.45 + 0.7 * band) * waterAvail * (0.8 + 0.4 * T.noiseB[i]) * (0.35 + 0.65 * smoothstep(-45, 5, t));
      hum = hum * (1 - 0.85 * f.drought[i]) * (o.humidityScale ?? 1) + (boostHum ? boostHum[i] * 0.4 : 0);
      hum = clamp(Math.max(hum, f.storm[i] * 0.95));
      f.humidity[i] = hum;
      f.precipitation[i] = 260 * hum * hum * (1 + 2 * f.storm[i]);
      const cl = clamp(hum * 1.25 - 0.3 + f.storm[i] * 0.9 + f.ash[i] * 0.35);
      f.cloud[i] = a.pressureBar < 0.03 ? 0 : a.surfaceHeat > 0.2 ? 0.3 * T.noiseB[i] : lerp(cl, 1, a.boil) * clamp(a.pressureBar * 3);
      cloudSum += f.cloud[i];
      const dry = a.waterParam < 0.02 ? 0.15 : 1;
      const ice = a.surfaceHeat > 0.2 ? 0 : (isW ? smoothstep(-1, -9, t) : smoothstep(-5, -15, t) * (0.7 + 0.3 * smoothstep(0.03, 0.25, hum + 0.1 * a.glaciation))) * dry;
      f.ice[i] = ice; if (ice > 0.5) iceCells++;
      f.solarFlux[i] = ((1361 * a.starFlux) / Math.PI) * Math.max(0.04, Math.cos(lat - p.axialTiltDeg * DEG * season)) * (1 - 0.5 * a.aerosols);
      f.lava[i] = Math.max(f.lava[i], a.surfaceHeat * (0.55 + 0.45 * T.noiseA[i]));
      f.salinity[i] = isW ? (o.salinityPpt ?? p.salinityPpt) * (1 + 0.07 * (t - 15) / 15) * (1 - 0.4 * ice) : 0;
      f.ph[i] = isW ? (o.oceanPh ?? p.oceanPh) - 0.18 * Math.log2(a.co2Ppm / 400) - 1.3 * f.eutro[i] : 6.6 - 0.8 * (hum - 0.5);
      f.water[i] = isW ? 1 : hum;
      f.mineral[i] = clamp(p.minerals * (0.5 + 0.9 * T.noiseB[i]) + 0.5 * f.ash[i] * (1 - a.aerosols) + 0.3 * T.ridge[i]);
    }

    // --- biosphere per cell
    const ls = this.lineages;
    const contrib = new Float32Array(n);
    const bestP = new Float32Array(n), bestH = new Float32Array(n), bestC = new Float32Array(n);
    let nfix = 0;
    const observedIdx = this.observedLineage ? this.lineageIndex.get(this.observedLineage) : undefined;
    if (observedIdx !== undefined) f.observed = new Float32Array(n);
    for (let li = 0; li < ls.length; li++) {
      const l = ls[li], norm = pops[li] / l.cap;
      if (l.role === "nitrogenFixer") nfix = Math.max(nfix, norm);
      if (norm < 0.004 || l.role === "decomposer") continue;
      const reg = l.regionIndex !== undefined ? this.regions[l.regionIndex] : undefined;
      const group = l.level === 0 ? 0 : l.role === "carnivore" ? 2 : 1;
      const arr = group === 0 ? f.biomassPhoto : group === 1 ? f.biomassHerb : f.biomassCarn;
      const best = group === 0 ? bestP : group === 1 ? bestH : bestC, dom = group === 0 ? f.domProducer : group === 1 ? f.domHerb : f.domCarn;
      for (let i = 0; i < n; i++) {
        const isW = water.isWater[i] === 1;
        if ((l.realm === "water" && !isW) || (l.realm === "land" && isW)) continue;
        let s = gauss(f.temperature[i], l.tempOpt, l.tempBreadth);
        if (s < 0.02) continue;
        if (isW) { if (l.level === 0) s *= 0.3 + 0.7 * smoothstep(-3500, -150, T.elevation[i] - sea); s *= 1 - f.ice[i]; }
        else {
          if (l.humOpt !== undefined) s *= gauss(f.humidity[i], l.humOpt, 0.32);
          if (l.level === 0) s *= 0.25 + 0.75 * clamp(p.soilFertility * (0.4 + 0.6 * f.humidity[i]) * (o.fertilityScale ?? 1) * 1.6);
          s *= (1 - f.ice[i]) * (1 - 0.9 * f.fire[i]) * (1 - 0.7 * f.drought[i]);
        }
        if (reg) s *= 1 - smoothstep(reg.radius * 0.5, reg.radius, Math.acos(clamp(c[i * 3] * reg.x + c[i * 3 + 1] * reg.y + c[i * 3 + 2] * reg.z, -1, 1)));
        s *= (1 - 0.9 * f.crater[i]) * (1 - 0.6 * f.ash[i] * (l.level === 0 ? 1 : 0.4));
        const v = norm * s;
        if (v < 0.01) continue;
        arr[i] += v;
        if (v > 0.05) contrib[i]++;
        if (v > best[i]) { best[i] = v; dom[i] = li; }
        if (li === observedIdx) f.observed![i] = v;
      }
    }
    let biomassSum = 0;
    const co2Local = a.co2Ppm, o2Local = a.o2Pct;
    for (let i = 0; i < n; i++) {
      const isW = water.isWater[i] === 1;
      if (boostVeg && !isW) f.biomassPhoto[i] += boostVeg[i] * 0.7 * (1 - f.ice[i]) * viable;
      f.biomassPhoto[i] = Math.min(1.3, f.biomassPhoto[i]); f.biomassHerb[i] = Math.min(1.3, f.biomassHerb[i]); f.biomassCarn[i] = Math.min(1.3, f.biomassCarn[i]);
      const living = f.biomassPhoto[i] + f.biomassHerb[i] * 0.3 + f.biomassCarn[i] * 0.1;
      biomassSum += living;
      f.richness[i] = Math.min(255, Math.round(contrib[i] * (o.richnessScale ?? 1)));
      f.bloom[i] = isW ? clamp((f.biomassPhoto[i] - 0.3) * 1.1 * (0.25 + 0.75 * smoothstep(-2500, -100, T.elevation[i] - sea)) + f.eutro[i] * 0.9) : 0;
      f.organicMatter[i] = clamp(0.12 * living + stuck * 0.95 * smoothstep(0, 0.25, living + (this.scenario.stuckFrom !== undefined || o.organicStuck ? 0.3 * (isW ? 0.4 : 1) * (1 - f.ice[i]) : 0)) + f.storm[i] * 0.1);
      f.nitrogen[i] = clamp(p.nutrients * (0.45 + 0.55 * nfix) * (1 - 0.92 * stuck) * (isW ? 0.8 : 0.5 + 0.5 * f.humidity[i]) + (boostFert ? boostFert[i] * 0.6 : 0) + f.eutro[i] * 0.5);
      f.soilFertility[i] = isW ? 0 : clamp((p.soilFertility * (0.35 + 0.65 * f.humidity[i]) * (0.8 + 0.4 * T.noiseB[i]) * (1 - f.ice[i]) + 0.15 * f.organicMatter[i] * (1 - stuck)) * (o.fertilityScale ?? 1) * (1 - 0.5 * stuck) + (boostFert ? boostFert[i] * 0.5 : 0));
      f.o2[i] = o2Local * (1 + 0.04 * (f.biomassPhoto[i] - 0.3)) * (1 - 0.85 * f.eutro[i] * (isW ? 1 : 0));
      f.co2[i] = co2Local * (1 - 0.03 * f.biomassPhoto[i] + 0.25 * f.fire[i]);
      f.biome[i] = classifyBiome(tAnnual[i], f.precipitation[i], T.elevation[i] - sea, isW, f.ice[i], f.lava[i], f.humidity[i]);
    }

    const bio = this.bioAt(tick, pops, a);
    const prev = this.bioPulse(tick);
    const meanBiomass = biomassSum / n;
    const archetype = classifyArchetype(a, iceCells / n, p, prev, this.scenario.regions ? true : p.landDistribution > 0.8 && a.oceanFraction > 0.7);
    const globals: Globals = {
      tick, year: Math.floor(tick / 12), yearPhase, era: era.era, eraProgress: clamp((tick - era.start) / (era.end - era.start)), eraStartTick: era.start, eraEndTick: era.end,
      meanTempC: a.meanTempC, o2Pct: a.o2Pct, co2Ppm: a.co2Ppm, ch4Ppm: a.ch4Ppm, pressureBar: a.pressureBar, aerosols: a.aerosols,
      oceanPh: (o.oceanPh ?? p.oceanPh) - 0.18 * Math.log2(a.co2Ppm / 400), salinityPpt: o.salinityPpt ?? p.salinityPpt, seaLevelM: sea,
      oceanFraction: a.oceanFraction, iceFraction: iceCells / n, cloudCover: cloudSum / n, surfaceHeat: a.surfaceHeat,
      magneticField: o.magneticField ?? p.magneticField, starActivity: o.starActivity ?? p.starActivity, starFlux: a.starFlux,
      biodiversity: clamp(bio.shannon / 2.6), prosperity: clamp(meanBiomass * 2.2 * (1 - 0.6 * prev)), totalBiomass: meanBiomass,
      extinctionPulse: o.extinctionPulse ?? prev, organicStuck: stuck, viability: viable, archetype,
    };
    const detail: DetailLevel = mode === "fast" ? "aggregate" : annualMean ? "reduced" : "full";
    return { tick, level: mesh.level, cellCount: n, params: p, globals, fields: f, events, bio, meta: { synthetic: true, scenarioId: this.scenario.id, mode, detail } };
  }

  /** 0..1 pulse after a mass extinction: desaturation that fades as diversity comes back. */
  private bioPulse(tick: number) {
    let pulse = 0;
    for (const e of this.eventScripts(tick)) if (e.type === "impact" && tick >= e.tick) pulse = Math.max(pulse, Math.exp(-(tick - e.tick) / 700));
    return pulse;
  }

  // ---------------------------------------------------------------- history
  history(fromTick: number, toTick: number, samples = 160): SeriesHistory {
    const h: SeriesHistory = { ticks: [], o2: [], co2: [], temp: [], biomass: [], shannon: [], richness: [], geneticDistance: [], strategies: [], webComplexity: [], originations: [], extinctions: [], populations: {}, marks: [] };
    const ids = this.lineages.filter((l) => l.origin <= toTick).map((l) => l.id);
    for (const id of ids) h.populations[id] = [];
    const step = Math.max(1, (toTick - fromTick) / Math.max(1, samples - 1));
    for (let k = 0; k < samples; k++) {
      const t = Math.min(toTick, Math.round(fromTick + k * step));
      if (h.ticks.length && t === h.ticks[h.ticks.length - 1]) continue;
      const pops = this.populations(t), a = this.atmosphereAt(t, this.producersNorm(pops));
      this.lastTick = t;
      const bio = this.bioAt(t, pops, a);
      h.ticks.push(t); h.o2.push(a.o2Pct); h.co2.push(a.co2Ppm); h.temp.push(Math.min(a.meanTempC, 400));
      h.biomass.push(this.lineages.reduce((s, l, i) => s + (pops[i] / l.cap) * (l.level === 0 ? 1 : 0.3), 0));
      h.shannon.push(bio.shannon); h.richness.push(bio.richness); h.geneticDistance.push(bio.geneticDistance); h.strategies.push(bio.metabolicStrategies);
      h.webComplexity.push(bio.trophicLevels + bio.connectance * 10 + bio.intransitiveShare * 5); h.originations.push(bio.originationRate); h.extinctions.push(bio.extinctionRate);
      for (const id of ids) h.populations[id].push(pops[this.lineageIndex.get(id)!]);
    }
    h.marks = this.marks(fromTick, toTick);
    return h;
  }

  marks(fromTick: number, toTick: number): TimelineMark[] {
    const m: TimelineMark[] = [];
    for (const e of this.scenario.eras) if (e.start >= fromTick && e.start <= toTick) m.push({ tick: e.start, kind: "era", labelKey: `era.${e.era}.name` });
    for (const s of this.eventScripts(toTick)) if (s.origin !== "background" && s.tick >= fromTick && s.tick <= toTick) m.push({ tick: s.tick, kind: "event", labelKey: `event.${s.type}.name`, ref: s.id });
    for (const s of this.scenario.events) if (!m.some((x) => x.ref === s.id) && s.tick >= fromTick && s.tick <= toTick) m.push({ tick: s.tick, kind: "event", labelKey: `event.${s.type}.name`, ref: s.id });
    for (const l of this.lineages) {
      if (l.extinct !== undefined && l.extinct >= fromTick && l.extinct <= toTick) m.push({ tick: l.extinct, kind: "extinction", labelKey: "mark.extinction", ref: l.id });
      if (l.parent && l.origin >= fromTick && l.origin <= toTick) m.push({ tick: l.origin, kind: "speciation", labelKey: `speciation.${l.mode}`, ref: l.id });
    }
    for (const mod of this.modifiers) if (mod.tick >= fromTick && mod.tick <= toTick) m.push({ tick: mod.tick, kind: "intervention", labelKey: `intervention.${mod.kind}.name`, ref: mod.id });
    return m.sort((x, y) => x.tick - y.tick);
  }
}

function keyframes(k: [number, number][], t: number): number {
  if (t <= k[0][0]) return k[0][1];
  for (let i = 1; i < k.length; i++) if (t <= k[i][0]) return lerp(k[i - 1][1], k[i][1], (t - k[i - 1][0]) / (k[i][0] - k[i - 1][0]));
  return k[k.length - 1][1];
}
function capabilityMask(role: TrophicRole): number {
  return { phototroph: 1, chemotroph: 2, herbivore: 4, carnivore: 8, detritivore: 16, decomposer: 32, nitrogenFixer: 64, mixotroph: 5 }[role];
}

/** PLACEHOLDER biome classification from temperature, precipitation and elevation (to be reviewed by the domain authority). */
export function classifyBiome(tAnnual: number, precip: number, elevRel: number, isWater: boolean, ice: number, lava: number, humidity: number): Biome {
  if (lava > 0.6) return Biome.Lava;
  if (ice > 0.5) return Biome.IceSheet;
  if (isWater) return elevRel < -1500 ? Biome.DeepOcean : Biome.ShallowOcean;
  if (humidity < 0.04) return Biome.Barren;
  if (elevRel > 3800) return Biome.Alpine;
  if (tAnnual < -4) return Biome.Tundra;
  if (precip < 22) return Biome.Desert;
  if (tAnnual < 5) return Biome.Boreal;
  if (tAnnual < 18) return precip < 60 ? Biome.Grassland : Biome.Temperate;
  return precip < 85 ? Biome.Savanna : Biome.Tropical;
}

function classifyArchetype(a: { surfaceHeat: number; pressureBar: number; boil: number; oceanFraction: number; primitive: number; meanTempC: number }, iceFraction: number, p: PlanetParams, pulse: number, islands: boolean): Archetype {
  if (a.surfaceHeat > 0.35) return "molten";
  if (a.pressureBar < 0.03) return "airless";
  if (a.boil > 0.5 || a.meanTempC > 90) return "greenhouse";
  if (iceFraction > 0.75) return "snowball";
  if (pulse > 0.35) return "postExtinction";
  if (a.primitive > 0.5) return "primordial";
  if (a.oceanFraction < 0.15) return "desert";
  if (a.oceanFraction > 0.92) return "ocean";
  if (islands) return "archipelago";
  return "temperate";
}

export { fbm3 as _fbm3 };
