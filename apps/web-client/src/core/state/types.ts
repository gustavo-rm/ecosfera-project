/**
 * Internal visual state of the planet (PlanetVisualState).
 * This is the ONLY model that render, HUD and dashboards read. It is internal to the frontend and says
 * nothing about transport. Field names follow the engine spec (§7.1) and the Dossiê (§5.2) where they exist.
 */
export type StarType = "M" | "K" | "G" | "F" | "A";
export type CrustType = "basaltic" | "granitic" | "ferrous" | "carbonaceous";

/** Creation parameters of the planet, six dimensions (Dossiê §5.2). */
export interface PlanetParams {
  seed: number;
  // Astronomical
  massEarths: number; radiusEarths: number; orbitAU: number; starType: StarType; starAgeGyr: number;
  moons: number; dayHours: number; axialTiltDeg: number; eccentricity: number; starActivity: number;
  // Physical (gravity, radiation and received energy are derived, see derivePhysical)
  magneticField: number;
  // Geological
  relief: number; volcanism: number; tectonics: number; crust: CrustType; minerals: number;
  // Chemical / atmospheric
  pressureBar: number; o2Pct: number; co2Ppm: number; ch4Ppm: number; albedo: number; ozone: number;
  // Hydrological
  waterFraction: number; salinityPpt: number; oceanPh: number; landDistribution: number;
  // Biological / edaphic
  soilFertility: number; nutrients: number; lifeSeed: boolean;
}

export type EraId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
export type UpdateMode = "normal" | "fast";
export type DetailLevel = "full" | "reduced" | "aggregate";
export type Archetype = "molten" | "airless" | "greenhouse" | "snowball" | "desert" | "ocean" | "archipelago" | "temperate" | "postExtinction" | "primordial";

export interface Globals {
  tick: number; year: number; yearPhase: number;
  era: EraId; eraProgress: number; eraStartTick: number; eraEndTick: number;
  meanTempC: number; o2Pct: number; co2Ppm: number; ch4Ppm: number; pressureBar: number; aerosols: number;
  oceanPh: number; salinityPpt: number;
  /** Meters above the elevation datum. is_water = elevation < seaLevelM. */
  seaLevelM: number;
  oceanFraction: number; iceFraction: number; cloudCover: number;
  /** 1 = molten young surface (Era 1), 0 = solid. */
  surfaceHeat: number;
  magneticField: number; starActivity: number;
  /** Stellar flux at the orbit, Earth = 1. */
  starFlux: number;
  /** 0..1 HUD indicators. */
  biodiversity: number; prosperity: number;
  totalBiomass: number;
  /** 0..1, transient desaturation after a mass extinction. */
  extinctionPulse: number;
  /** 0..1, organic matter that nobody decomposes. */
  organicStuck: number;
  viability: number;
  archetype: Archetype;
}

/** Per-cell fields. Every array has `cellCount` entries, in the order defined by core/mesh/cellOrder.ts. */
export interface CellFields {
  elevation: Float32Array; isWater: Uint8Array;
  temperature: Float32Array; humidity: Float32Array; precipitation: Float32Array; solarFlux: Float32Array;
  salinity: Float32Array; ph: Float32Array; o2: Float32Array; co2: Float32Array; soilFertility: Float32Array;
  // Resources (§8.1). LIGHT = solarFlux, CO2/O2 = co2/o2, LIVING_BIOMASS = sum of biomass*.
  water: Float32Array; mineral: Float32Array; nitrogen: Float32Array; organicMatter: Float32Array;
  // Derived
  biomassPhoto: Float32Array; biomassHerb: Float32Array; biomassCarn: Float32Array;
  richness: Uint8Array; domProducer: Int16Array; domHerb: Int16Array; domCarn: Int16Array;
  biome: Uint8Array; ice: Float32Array; cloud: Float32Array; lava: Float32Array; bloom: Float32Array;
  // Disturbance masks, 0..1
  fire: Float32Array; drought: Float32Array; storm: Float32Array; ash: Float32Array; eutro: Float32Array; crater: Float32Array; bioMark: Float32Array;
  /** Density of the lineage under observation (on demand), or null. */
  observed: Float32Array | null;
}
export type ScalarFieldKey = { [K in keyof CellFields]: CellFields[K] extends Float32Array ? K : never }[keyof CellFields];

export type EventType = "fire" | "drought" | "storm" | "glaciation" | "volcanism" | "impact" | "eutrophication" | "pandemic" | "invasive";
export type EventPhase = "telegraph" | "active" | "aftermath";
export type Instrument = "seismograph" | "telescope" | "barometer" | "hygrometer" | "thermometer" | "waterProbe" | "smokeSensor" | "bioSensor";

export interface PlanetEvent {
  id: string; type: EventType; scale: "local" | "regional" | "global";
  cell: number; lat: number; lon: number; radiusDeg: number;
  /** 0..1 current strength. */
  intensity: number; phase: EventPhase;
  startTick: number; endTick: number; telegraphTick: number;
  instrument: Instrument;
  /** i18n keys of the causal chain, for the "por quê?". */
  causalChain: string[];
  origin: "engine" | "student" | "background";
  suppressed: boolean;
}

export type TrophicRole = "phototroph" | "chemotroph" | "herbivore" | "carnivore" | "detritivore" | "decomposer" | "nitrogenFixer" | "mixotroph";
export type SpeciationMode = "ancestral" | "allopatric" | "parapatric" | "sympatric" | "introduced";
export type DeathCause = "STARVATION" | "SENESCENCE" | "PREDATION" | "ENVIRONMENTAL";

/** Read-only record of a lineage, as the observer (M7) would report it. */
export interface SpeciesRecord {
  id: string; index: number; name: string; parentId: string | null;
  role: TrophicRole; trophicLevel: number; realm: "water" | "land" | "both";
  originTick: number; extinctTick: number | null; extinctionCause: DeathCause | null;
  speciationMode: SpeciationMode; originLat: number; originLon: number;
  asexual: boolean; founderEffect: boolean;
  /** Effective phenotype values by gene id (Appendix A). Booleans are 0/1, tags are arrays of symbols. */
  phenotype: Record<string, number | number[]>;
  preyIds: string[];
  /** Ids of lineages in an intransitive (rock-paper-scissors) competition cycle with this one. */
  cycleIds: string[];
  geneticDistance: number;
  population: number; alive: boolean;
}

export interface FoodWebLink { from: string; to: string; flux: number; kind: "trophic" | "cycle" }
export interface BioFlag { type: "bottleneck" | "founder"; lineageId: string; tick: number }
export interface CycleFlux { id: string; from: string; to: string; value: number }
export interface CycleDiagram { element: "carbon" | "nitrogen" | "oxygen" | "water"; stocks: { id: string; value: number }[]; fluxes: CycleFlux[] }

export interface BiosphereFrame {
  species: SpeciesRecord[];
  links: FoodWebLink[];
  /** Energy flow per trophic level, index 0 = producers. */
  pyramid: number[];
  shannon: number; richness: number; evenness: number;
  geneticDistance: number; metabolicStrategies: number; trophicLevels: number; connectance: number; intransitiveShare: number;
  originationRate: number; extinctionRate: number; massExtinction: boolean;
  flags: BioFlag[];
  cycles: CycleDiagram[];
}

export interface PlanetFrame {
  tick: number; level: number; cellCount: number;
  params: PlanetParams; globals: Globals; fields: CellFields; events: PlanetEvent[]; bio: BiosphereFrame;
  meta: { synthetic: boolean; scenarioId: string; mode: UpdateMode; detail: DetailLevel };
}

/** History for dashboards. Arrays are aligned with `ticks`. */
export interface SeriesHistory {
  ticks: number[]; o2: number[]; co2: number[]; temp: number[]; biomass: number[]; shannon: number[]; richness: number[];
  geneticDistance: number[]; strategies: number[]; webComplexity: number[]; originations: number[]; extinctions: number[];
  populations: Record<string, number[]>;
  marks: TimelineMark[];
}
export interface TimelineMark { tick: number; kind: "era" | "event" | "extinction" | "speciation" | "intervention"; labelKey: string; labelParams?: Record<string, string | number>; ref?: string }

export interface RegimeMetrics { dominance: number; populationCV: number; extinctionsPer1000: number; coexisting: number; autocorrelation: number }
