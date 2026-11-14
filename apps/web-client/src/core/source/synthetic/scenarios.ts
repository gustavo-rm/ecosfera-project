import type { DeathCause, EraId, EventType, PlanetParams, SpeciationMode, TrophicRole } from "../../state/types";

/** Scripted lineage. The script only shapes the FORM of the data; it is not a simulation (see ADR 0005). */
export interface LineageScript {
  id: string; parent: string | null; origin: number; extinct?: number; cause?: DeathCause; mode: SpeciationMode;
  role: TrophicRole; realm: "water" | "land" | "both"; level: number;
  tempOpt: number; tempBreadth: number; humOpt?: number;
  cap: number; growth: number; period: number; amp: number; phase: number;
  mass: number; mobility: number; asexual?: boolean; founder?: boolean; bottleneck?: number;
  prey?: string[]; cycle?: string[]; regionIndex?: number; latBand?: [number, number];
  factor?: [number, number][];
  /** Extra vulnerability to global catastrophes, 0..1. */
  fragile?: number;
}
export interface EventScript { id: string; type: EventType; tick: number; lat: number; lon: number; intensity?: number; noTelegraph?: boolean; origin?: "engine" | "student" | "background" }
export interface ScenarioDef {
  id: string; params: Partial<PlanetParams>;
  eras: { era: EraId; start: number }[]; endTick: number; previewTick: number;
  /** Tells the atmosphere/ocean/heat story of a newborn planet (Eras 1 to 4). */
  primordial: boolean;
  lineages: LineageScript[]; events: EventScript[];
  /** Start of decomposer suppression (Sem Decompositores). */
  stuckFrom?: number;
  regions?: number;
}

type L = Partial<LineageScript> & Pick<LineageScript, "id" | "parent" | "origin" | "role">;
const ROLE_DEFAULTS: Record<TrophicRole, Partial<LineageScript>> = {
  phototroph: { realm: "water", level: 0, cap: 900, mass: 1e-5, mobility: 0, growth: 500, period: 180, amp: 0.16 },
  chemotroph: { realm: "water", level: 0, cap: 220, mass: 1e-6, mobility: 0, growth: 500, period: 240, amp: 0.1 },
  nitrogenFixer: { realm: "both", level: 0, cap: 260, mass: 1e-6, mobility: 0, growth: 400, period: 200, amp: 0.14 },
  decomposer: { realm: "both", level: 0, cap: 420, mass: 1e-6, mobility: 0.05, growth: 400, period: 150, amp: 0.15 },
  detritivore: { realm: "both", level: 1, cap: 160, mass: 0.002, mobility: 0.3, growth: 450, period: 170, amp: 0.2 },
  herbivore: { realm: "water", level: 1, cap: 200, mass: 0.05, mobility: 0.5, growth: 450, period: 190, amp: 0.26 },
  mixotroph: { realm: "water", level: 1, cap: 120, mass: 0.001, mobility: 0.3, growth: 400, period: 160, amp: 0.2 },
  carnivore: { realm: "water", level: 2, cap: 42, mass: 2, mobility: 0.8, growth: 500, period: 190, amp: 0.3 },
};
let phaseSeq = 0;
function lin(l: L): LineageScript {
  const d = ROLE_DEFAULTS[l.role];
  phaseSeq += 1.7;
  return {
    mode: l.parent ? "allopatric" : "ancestral", tempOpt: 18, tempBreadth: 14, phase: phaseSeq + (l.level ?? d.level ?? 0) * 1.3,
    ...(d as Required<Pick<LineageScript, "realm" | "level" | "cap" | "mass" | "mobility" | "growth" | "period" | "amp">>), ...l,
  };
}

/** Mature food web used by the scenarios that start with an established biosphere. Origins are negative (before tick 0). */
function matureWeb(): LineageScript[] {
  return [
    lin({ id: "alga", parent: null, origin: -9000, role: "phototroph", asexual: true, tempOpt: 20, tempBreadth: 16 }),
    lin({ id: "decomp", parent: "alga", origin: -8200, role: "decomposer", asexual: true, tempBreadth: 22 }),
    lin({ id: "fixer", parent: "alga", origin: -7900, role: "nitrogenFixer", asexual: true }),
    lin({ id: "kelp", parent: "alga", origin: -7000, role: "phototroph", cap: 500, mass: 0.4, tempOpt: 13, tempBreadth: 9, mode: "sympatric" }),
    lin({ id: "grazer", parent: "alga", origin: -6400, role: "herbivore", prey: ["alga", "kelp"], cycle: ["filter", "nibbler"] }),
    lin({ id: "filter", parent: "grazer", origin: -5800, role: "herbivore", prey: ["alga"], cap: 170, mass: 0.01, mobility: 0.1, cycle: ["nibbler", "grazer"], mode: "sympatric" }),
    lin({ id: "nibbler", parent: "grazer", origin: -5300, role: "herbivore", prey: ["kelp", "alga"], cap: 150, cycle: ["grazer", "filter"] }),
    lin({ id: "hunter", parent: "grazer", origin: -4900, role: "carnivore", prey: ["grazer", "nibbler", "filter"] }),
    lin({ id: "moss", parent: "kelp", origin: -4200, role: "phototroph", realm: "land", cap: 700, mass: 0.02, humOpt: 0.7, tempOpt: 14, founder: true }),
    lin({ id: "fern", parent: "moss", origin: -3400, role: "phototroph", realm: "land", cap: 620, mass: 3, humOpt: 0.75, tempOpt: 23, tempBreadth: 9, mode: "parapatric" }),
    lin({ id: "shrub", parent: "moss", origin: -2900, role: "phototroph", realm: "land", cap: 480, mass: 12, humOpt: 0.4, tempOpt: 20, tempBreadth: 12, mode: "parapatric" }),
    lin({ id: "crawler", parent: "nibbler", origin: -3000, role: "herbivore", realm: "land", prey: ["moss", "fern"], cap: 180, mass: 0.3, founder: true }),
    lin({ id: "browser", parent: "crawler", origin: -2200, role: "herbivore", realm: "land", prey: ["fern", "shrub"], cap: 110, mass: 60, fragile: 0.9 }),
    lin({ id: "worm", parent: "decomp", origin: -2600, role: "detritivore", realm: "land", cap: 200 }),
    lin({ id: "stalker", parent: "hunter", origin: -1900, role: "carnivore", realm: "land", prey: ["crawler", "browser"], cap: 30, mass: 25, fragile: 0.8 }),
    lin({ id: "apex", parent: "stalker", origin: -1100, role: "carnivore", realm: "land", level: 3, prey: ["stalker", "browser"], cap: 9, mass: 300, fragile: 1, mode: "sympatric" }),
  ];
}

const genesis: ScenarioDef = {
  id: "genesis", params: {}, primordial: true, endTick: 20000, previewTick: 17500,
  eras: [{ era: 1, start: 0 }, { era: 2, start: 1200 }, { era: 3, start: 2400 }, { era: 4, start: 3600 }, { era: 5, start: 6000 }, { era: 6, start: 9600 }, { era: 7, start: 13200 }, { era: 8, start: 15600 }],
  lineages: [
    lin({ id: "anc", parent: null, origin: 3700, role: "phototroph", asexual: true, tempOpt: 24, tempBreadth: 18, growth: 900 }),
    lin({ id: "dec1", parent: "anc", origin: 4600, role: "decomposer", asexual: true, tempBreadth: 22 }),
    lin({ id: "fix1", parent: "anc", origin: 5200, role: "nitrogenFixer", asexual: true }),
    lin({ id: "alg1", parent: "anc", origin: 6100, role: "phototroph", cap: 700, mass: 0.001, tempOpt: 17, tempBreadth: 11, mode: "sympatric" }),
    lin({ id: "her1", parent: "alg1", origin: 6300, role: "herbivore", prey: ["anc", "alg1"], cycle: ["her2", "her3"] }),
    lin({ id: "her2", parent: "her1", origin: 6900, role: "herbivore", prey: ["alg1"], cap: 170, mass: 0.01, mobility: 0.15, cycle: ["her3", "her1"], mode: "sympatric" }),
    lin({ id: "det1", parent: "dec1", origin: 7000, role: "detritivore" }),
    lin({ id: "her3", parent: "her1", origin: 7300, role: "herbivore", prey: ["anc", "alg1"], cap: 140, cycle: ["her1", "her2"], fragile: 0.9 }),
    lin({ id: "car1", parent: "her1", origin: 7400, role: "carnivore", prey: ["her1", "her2", "her3"] }),
    lin({ id: "bg1", parent: "alg1", origin: 8000, extinct: 8900, cause: "STARVATION", role: "mixotroph", cap: 60 }),
    lin({ id: "pla1", parent: "alg1", origin: 9700, role: "phototroph", realm: "land", cap: 700, mass: 0.02, humOpt: 0.7, tempOpt: 15, founder: true }),
    lin({ id: "her4", parent: "her2", origin: 10300, role: "herbivore", realm: "land", prey: ["pla1", "pla2"], cap: 180, mass: 0.3, founder: true }),
    lin({ id: "pla2", parent: "pla1", origin: 10400, role: "phototroph", realm: "land", cap: 620, mass: 3, humOpt: 0.75, tempOpt: 24, tempBreadth: 8, mode: "parapatric" }),
    lin({ id: "pla3", parent: "pla1", origin: 11000, role: "phototroph", realm: "land", cap: 430, mass: 15, humOpt: 0.4, tempOpt: 20, tempBreadth: 6, mode: "parapatric", fragile: 0.9 }),
    lin({ id: "her5", parent: "her4", origin: 11200, role: "herbivore", realm: "land", prey: ["pla2", "pla3"], cap: 100, mass: 70, fragile: 0.7 }),
    lin({ id: "car2", parent: "car1", origin: 11500, role: "carnivore", realm: "land", prey: ["her4", "her5"], cap: 30, mass: 20 }),
    lin({ id: "bg2", parent: "her4", origin: 12000, extinct: 12800, cause: "PREDATION", role: "herbivore", realm: "land", prey: ["pla1"], cap: 50 }),
    lin({ id: "top1", parent: "car2", origin: 12300, role: "carnivore", realm: "land", level: 3, prey: ["car2", "her5"], cap: 9, mass: 280, fragile: 1, mode: "sympatric" }),
    // Mass extinction at the impact (tick 15000): the scripted victims are the large and the specialists.
    lin({ id: "rad1", parent: "her4", origin: 15300, role: "herbivore", realm: "land", prey: ["pla1", "pla2", "rad4"], cap: 150, mass: 1.5 }),
    lin({ id: "rad2", parent: "car2", origin: 15450, role: "carnivore", realm: "land", prey: ["her4", "rad1"], cap: 34, mass: 6 }),
    lin({ id: "rad3", parent: "her2", origin: 15500, role: "mixotroph", prey: ["alg1"], cap: 130, mode: "sympatric" }),
    lin({ id: "rad4", parent: "pla2", origin: 15700, role: "phototroph", realm: "land", cap: 520, mass: 8, humOpt: 0.45, tempOpt: 19, tempBreadth: 11 }),
    lin({ id: "rad5", parent: "rad1", origin: 16400, role: "herbivore", realm: "land", prey: ["rad4", "pla2"], cap: 90, mass: 30, mode: "parapatric" }),
    lin({ id: "rad6", parent: "rad2", origin: 17000, role: "carnivore", realm: "land", level: 3, prey: ["rad2", "rad5"], cap: 10, mass: 120, mode: "sympatric" }),
  ],
  events: [
    { id: "ev-volc", type: "volcanism", tick: 13500, lat: 22, lon: -40 },
    { id: "ev-glac", type: "glaciation", tick: 14000, lat: 90, lon: 0 },
    { id: "ev-impact", type: "impact", tick: 15000, lat: -8, lon: 35 },
  ],
};
for (const [id, cause] of [["her3", "STARVATION"], ["pla3", "ENVIRONMENTAL"], ["top1", "STARVATION"]] as const) {
  const l = genesis.lineages.find((x) => x.id === id)!;
  l.extinct = 15000 + (id === "pla3" ? 60 : id === "her3" ? 150 : 240); l.cause = cause;
}

const gradient: ScenarioDef = {
  id: "gradient", primordial: false, endTick: 7200, previewTick: 5200,
  params: { seed: 21, waterFraction: 0.45, landDistribution: 0.05, axialTiltDeg: 12, relief: 0.3, tectonics: 0.15 },
  eras: [{ era: 5, start: 0 }, { era: 6, start: 3000 }],
  lineages: [
    ...matureWeb().filter((l) => ["alga", "decomp", "fixer", "grazer", "hunter", "worm"].includes(l.id)),
    // A wide-ranging ancestor forms a cline along the thermal gradient, then splits (parapatric).
    lin({ id: "cline", parent: "alga", origin: -3000, role: "phototroph", realm: "land", cap: 900, mass: 1, tempOpt: 14, tempBreadth: 20, humOpt: 0.55, factor: [[2400, 1], [3400, 0.55]] }),
    lin({ id: "cold", parent: "cline", origin: 2400, role: "phototroph", realm: "land", cap: 520, mass: 0.6, tempOpt: 2, tempBreadth: 7, humOpt: 0.5, mode: "parapatric" }),
    lin({ id: "warm", parent: "cline", origin: 2700, role: "phototroph", realm: "land", cap: 600, mass: 2.5, tempOpt: 25, tempBreadth: 7, humOpt: 0.6, mode: "parapatric" }),
    lin({ id: "roam", parent: "grazer", origin: -1500, role: "herbivore", realm: "land", prey: ["cline", "cold", "warm"], cap: 200, mass: 4, tempBreadth: 20, factor: [[3600, 1], [4600, 0.6]] }),
    lin({ id: "roamN", parent: "roam", origin: 3900, role: "herbivore", realm: "land", prey: ["cold", "cline"], cap: 110, mass: 9, tempOpt: 3, tempBreadth: 8, mode: "parapatric" }),
    lin({ id: "pred", parent: "hunter", origin: -600, role: "carnivore", realm: "land", prey: ["roam", "roamN"], cap: 28, mass: 15 }),
  ],
  events: [],
};

const archipelago: ScenarioDef = {
  id: "archipelago", primordial: false, endTick: 7200, previewTick: 5600, regions: 5,
  params: { seed: 12, waterFraction: 0.84, landDistribution: 0.95, relief: 0.6, tectonics: 0.5, volcanism: 0.55 },
  eras: [{ era: 5, start: 0 }, { era: 6, start: 2400 }],
  lineages: [
    ...matureWeb().filter((l) => ["alga", "decomp", "fixer", "kelp", "grazer", "filter", "hunter"].includes(l.id)),
    lin({ id: "isl0", parent: "kelp", origin: -800, role: "phototroph", realm: "land", cap: 380, mass: 0.5, humOpt: 0.7, regionIndex: 0, tempBreadth: 16 }),
    ...[1, 2, 3, 4].map((k) => lin({ id: `isl${k}`, parent: "isl0", origin: [0, 500, 1300, 2200, 3000][k], role: "phototroph", realm: "land", cap: 300 + 30 * k, mass: 0.3 * 2 ** k, humOpt: 0.6, regionIndex: k, tempBreadth: 15, mode: "allopatric", founder: true })),
    lin({ id: "bird0", parent: "grazer", origin: 900, role: "herbivore", realm: "land", prey: ["isl0"], cap: 90, mass: 0.02, mobility: 0.9, regionIndex: 0, founder: true }),
    ...[1, 2, 3].map((k) => lin({ id: `bird${k}`, parent: "bird0", origin: [0, 2100, 3300, 4300][k], role: "herbivore", realm: "land", prey: [`isl${k}`], cap: 70, mass: 0.02 * (1 + k), mobility: 0.8, regionIndex: k, mode: "allopatric", founder: true })),
  ],
  events: [{ id: "ev-storm-a", type: "storm", tick: 1800, lat: 10, lon: 60 }, { id: "ev-volc-a", type: "volcanism", tick: 3900, lat: -15, lon: -100 }],
};

const catastrophe: ScenarioDef = {
  id: "catastrophe", primordial: false, endTick: 6000, previewTick: 1900,
  params: { seed: 33 },
  eras: [{ era: 7, start: 0 }, { era: 8, start: 3600 }],
  lineages: [
    ...matureWeb().map((l) => {
      const dies: Record<string, [number, DeathCause]> = { kelp: [1860, "ENVIRONMENTAL"], browser: [1920, "STARVATION"], apex: [2000, "STARVATION"], stalker: [2080, "STARVATION"], fern: [1850, "ENVIRONMENTAL"], nibbler: [1980, "STARVATION"] };
      return dies[l.id] ? { ...l, extinct: dies[l.id][0], cause: dies[l.id][1] } : { ...l, bottleneck: 1800 };
    }),
    lin({ id: "nova1", parent: "moss", origin: 2500, role: "phototroph", realm: "land", cap: 560, mass: 1.2, humOpt: 0.7, tempOpt: 22, tempBreadth: 10 }),
    lin({ id: "nova2", parent: "crawler", origin: 2700, role: "herbivore", realm: "land", prey: ["nova1", "moss", "shrub"], cap: 160, mass: 2 }),
    lin({ id: "nova3", parent: "crawler", origin: 2900, role: "carnivore", realm: "land", prey: ["crawler", "nova2"], cap: 32, mass: 4, mode: "sympatric" }),
    lin({ id: "nova4", parent: "alga", origin: 2600, role: "phototroph", cap: 520, mass: 0.2, tempOpt: 15, tempBreadth: 10, mode: "sympatric" }),
    lin({ id: "nova5", parent: "grazer", origin: 3100, role: "herbivore", prey: ["nova4", "alga"], cap: 150, mass: 0.2, cycle: ["grazer", "filter"] }),
    lin({ id: "nova6", parent: "nova2", origin: 3700, role: "herbivore", realm: "land", prey: ["nova1", "shrub"], cap: 90, mass: 35, mode: "parapatric" }),
    lin({ id: "nova7", parent: "nova3", origin: 4300, role: "carnivore", realm: "land", level: 3, prey: ["nova3", "nova6"], cap: 9, mass: 90, mode: "sympatric" }),
  ],
  events: [{ id: "ev-impact", type: "impact", tick: 1800, lat: 12, lon: 20 }],
};

const noDecomposers: ScenarioDef = {
  id: "noDecomposers", primordial: false, endTick: 6000, previewTick: 2600, stuckFrom: 600,
  params: { seed: 44 },
  eras: [{ era: 6, start: 0 }, { era: 7, start: 3000 }],
  lineages: matureWeb().map((l) => (l.role === "decomposer" || l.role === "detritivore" ? { ...l, extinct: 700, cause: "ENVIRONMENTAL" as DeathCause } : l)),
  events: [],
};

export const SCENARIOS: Record<string, ScenarioDef> = { genesis, gradient, archipelago, catastrophe, noDecomposers };
export const SCENARIO_IDS = Object.keys(SCENARIOS);

/** Archetype presets for the visual catalog and the lab (section 7.3). They reuse the Gênese story at a given tick. */
export const ARCHETYPE_PRESETS: Record<string, { scenarioId: string; tick: number; params: Partial<PlanetParams> }> = {
  molten: { scenarioId: "genesis", tick: 150, params: {} },
  condensation: { scenarioId: "genesis", tick: 1750, params: {} },
  microbial: { scenarioId: "genesis", tick: 5200, params: {} },
  terra: { scenarioId: "genesis", tick: 12900, params: {} },
  ocean: { scenarioId: "genesis", tick: 12900, params: { waterFraction: 0.97, seed: 5 } },
  desert: { scenarioId: "genesis", tick: 12900, params: { waterFraction: 0.06, seed: 9, crust: "ferrous" } },
  snowball: { scenarioId: "genesis", tick: 12900, params: { orbitAU: 1.55, seed: 3 } },
  archipelago: { scenarioId: "archipelago", tick: 5600, params: {} },
  airless: { scenarioId: "genesis", tick: 12900, params: { pressureBar: 0, waterFraction: 0, magneticField: 0, seed: 15, crust: "basaltic", lifeSeed: false } },
  greenhouse: { scenarioId: "genesis", tick: 12900, params: { orbitAU: 0.72, co2Ppm: 60000, pressureBar: 6, seed: 8 } },
  postExtinction: { scenarioId: "catastrophe", tick: 2150, params: {} },
  recovery: { scenarioId: "catastrophe", tick: 5600, params: {} },
};
