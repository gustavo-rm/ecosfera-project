import type { CrustType, EraId, EventType, Instrument, PlanetParams, StarType, TrophicRole } from "./types";

/** Nine eras (Dossiê GDD §7). Names live in i18n under `era.<id>.name`. */
export const ERA_IDS: EraId[] = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export type ParamDimension = "astronomical" | "physical" | "geological" | "atmospheric" | "hydrological" | "biological";
export type PlayerLevel = 0 | 1 | 2 | 3; // Aprendiz, Explorador, Investigador, Guardião
export interface ParamDef {
  key: keyof PlanetParams; dimension: ParamDimension; min: number; max: number; step: number; unit: string;
  log?: boolean; minLevel: PlayerLevel; options?: string[]; kind?: "range" | "select" | "toggle";
}
/** Levers of the Gênese screen (Dossiê §5.2). `minLevel` drives progressive disclosure. */
export const PARAM_DEFS: ParamDef[] = [
  { key: "orbitAU", dimension: "astronomical", min: 0.1, max: 5, step: 0.01, unit: "UA", log: true, minLevel: 0 },
  { key: "starType", dimension: "astronomical", min: 0, max: 4, step: 1, unit: "", minLevel: 0, kind: "select", options: ["M", "K", "G", "F", "A"] },
  { key: "massEarths", dimension: "astronomical", min: 0.1, max: 8, step: 0.05, unit: "M⊕", log: true, minLevel: 1 },
  { key: "radiusEarths", dimension: "astronomical", min: 0.4, max: 2.2, step: 0.05, unit: "R⊕", minLevel: 1 },
  { key: "axialTiltDeg", dimension: "astronomical", min: 0, max: 60, step: 1, unit: "°", minLevel: 0 },
  { key: "moons", dimension: "astronomical", min: 0, max: 4, step: 1, unit: "", minLevel: 0 },
  { key: "dayHours", dimension: "astronomical", min: 6, max: 96, step: 1, unit: "h", minLevel: 1 },
  { key: "eccentricity", dimension: "astronomical", min: 0, max: 0.6, step: 0.01, unit: "", minLevel: 2 },
  { key: "starAgeGyr", dimension: "astronomical", min: 0.5, max: 10, step: 0.1, unit: "Ga", minLevel: 2 },
  { key: "starActivity", dimension: "astronomical", min: 0, max: 1, step: 0.01, unit: "", minLevel: 3 },
  { key: "magneticField", dimension: "physical", min: 0, max: 1, step: 0.01, unit: "", minLevel: 1 },
  { key: "relief", dimension: "geological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 0 },
  { key: "volcanism", dimension: "geological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 1 },
  { key: "tectonics", dimension: "geological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 2 },
  { key: "crust", dimension: "geological", min: 0, max: 3, step: 1, unit: "", minLevel: 2, kind: "select", options: ["basaltic", "granitic", "ferrous", "carbonaceous"] },
  { key: "minerals", dimension: "geological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 3 },
  { key: "pressureBar", dimension: "atmospheric", min: 0, max: 10, step: 0.05, unit: "bar", minLevel: 0 },
  { key: "co2Ppm", dimension: "atmospheric", min: 10, max: 100000, step: 10, unit: "ppm", log: true, minLevel: 1 },
  { key: "o2Pct", dimension: "atmospheric", min: 0, max: 35, step: 0.5, unit: "%", minLevel: 1 },
  { key: "ch4Ppm", dimension: "atmospheric", min: 0.1, max: 5000, step: 0.1, unit: "ppm", log: true, minLevel: 3 },
  { key: "albedo", dimension: "atmospheric", min: 0.05, max: 0.8, step: 0.01, unit: "", minLevel: 2 },
  { key: "ozone", dimension: "atmospheric", min: 0, max: 1, step: 0.01, unit: "", minLevel: 3 },
  { key: "waterFraction", dimension: "hydrological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 0 },
  { key: "landDistribution", dimension: "hydrological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 1 },
  { key: "salinityPpt", dimension: "hydrological", min: 0, max: 45, step: 0.5, unit: "ppt", minLevel: 2 },
  { key: "oceanPh", dimension: "hydrological", min: 3, max: 11, step: 0.1, unit: "pH", minLevel: 2 },
  { key: "soilFertility", dimension: "biological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 0 },
  { key: "nutrients", dimension: "biological", min: 0, max: 1, step: 0.01, unit: "", minLevel: 1 },
  { key: "lifeSeed", dimension: "biological", min: 0, max: 1, step: 1, unit: "", minLevel: 0, kind: "toggle" },
];
export const DIMENSIONS: ParamDimension[] = ["astronomical", "physical", "geological", "atmospheric", "hydrological", "biological"];

export const DEFAULT_PARAMS: PlanetParams = {
  seed: 7, massEarths: 1, radiusEarths: 1, orbitAU: 1, starType: "G", starAgeGyr: 4.6, moons: 1, dayHours: 24, axialTiltDeg: 23, eccentricity: 0.02,
  starActivity: 0.3, magneticField: 0.7, relief: 0.55, volcanism: 0.3, tectonics: 0.4, crust: "granitic", minerals: 0.5,
  pressureBar: 1, o2Pct: 21, co2Ppm: 400, ch4Ppm: 1.8, albedo: 0.3, ozone: 0.6,
  waterFraction: 0.68, salinityPpt: 35, oceanPh: 8.1, landDistribution: 0.35, soilFertility: 0.6, nutrients: 0.6, lifeSeed: true,
};

/** PLACEHOLDER (science): relative luminosity and display color per star type. To be reviewed by the domain authority. */
export const STAR_TABLE: Record<StarType, { luminosity: number; color: [number, number, number]; size: number }> = {
  M: { luminosity: 0.08, color: [1.0, 0.56, 0.36], size: 0.5 },
  K: { luminosity: 0.4, color: [1.0, 0.78, 0.56], size: 0.8 },
  G: { luminosity: 1, color: [1.0, 0.95, 0.86], size: 1 },
  F: { luminosity: 2.5, color: [0.96, 0.97, 1.0], size: 1.25 },
  A: { luminosity: 8, color: [0.8, 0.87, 1.0], size: 1.7 },
};
/** PLACEHOLDER (science): rock/soil palette per crust composition, linear-ish sRGB. */
export const CRUST_COLORS: Record<CrustType, [number, number, number]> = {
  basaltic: [0.30, 0.29, 0.30], granitic: [0.58, 0.50, 0.42], ferrous: [0.60, 0.33, 0.22], carbonaceous: [0.20, 0.19, 0.18],
};

export enum Biome { DeepOcean, ShallowOcean, IceSheet, Tundra, Boreal, Temperate, Grassland, Desert, Savanna, Tropical, Alpine, Barren, Lava }
export const BIOME_COUNT = 13;
/** Stylized base colors per biome class (representation, not data). */
export const BIOME_COLORS: [number, number, number][] = [
  [0.03, 0.12, 0.30], [0.08, 0.32, 0.48], [0.92, 0.95, 0.98], [0.56, 0.58, 0.50], [0.20, 0.36, 0.28], [0.25, 0.45, 0.22],
  [0.55, 0.60, 0.30], [0.80, 0.68, 0.45], [0.66, 0.60, 0.30], [0.10, 0.40, 0.16], [0.52, 0.50, 0.50], [0.45, 0.40, 0.36], [0.85, 0.25, 0.05],
];

export interface EventDef { type: EventType; scale: "local" | "regional" | "global"; radiusDeg: number; duration: number; telegraph: number; instrument: Instrument; chain: string[]; inEngineCatalog: boolean }
/** Event catalog (§20.2) plus the two abstract biological events of the Dossiê (not in the engine catalog; see DIVERGENCIAS.md). */
export const EVENT_DEFS: Record<EventType, EventDef> = {
  fire: { type: "fire", scale: "local", radiusDeg: 7, duration: 36, telegraph: 12, instrument: "smokeSensor", chain: ["dryVegetation", "fire", "biomassLoss", "mineralsReleased", "regrowth"], inEngineCatalog: true },
  drought: { type: "drought", scale: "regional", radiusDeg: 26, duration: 240, telegraph: 48, instrument: "hygrometer", chain: ["lessRain", "waterDrop", "producerStress", "populationDrop"], inEngineCatalog: true },
  storm: { type: "storm", scale: "local", radiusDeg: 12, duration: 24, telegraph: 8, instrument: "barometer", chain: ["pressureDrop", "storm", "biomassLoss", "organicSpread"], inEngineCatalog: true },
  glaciation: { type: "glaciation", scale: "global", radiusDeg: 180, duration: 900, telegraph: 120, instrument: "thermometer", chain: ["cooling", "iceAdvance", "seaLevelDrop", "rangeShift", "coldSelection"], inEngineCatalog: true },
  volcanism: { type: "volcanism", scale: "regional", radiusDeg: 14, duration: 120, telegraph: 36, instrument: "seismograph", chain: ["eruption", "aerosols", "cooling", "producerStress", "populationDrop"], inEngineCatalog: true },
  impact: { type: "impact", scale: "global", radiusDeg: 16, duration: 360, telegraph: 60, instrument: "telescope", chain: ["impact", "dust", "darkening", "producerCollapse", "massExtinction", "radiation"], inEngineCatalog: true },
  eutrophication: { type: "eutrophication", scale: "regional", radiusDeg: 15, duration: 180, telegraph: 30, instrument: "waterProbe", chain: ["nutrientExcess", "algaeBloom", "oxygenDrop", "deadZone"], inEngineCatalog: true },
  pandemic: { type: "pandemic", scale: "regional", radiusDeg: 22, duration: 120, telegraph: 24, instrument: "bioSensor", chain: ["pathogenSpread", "populationDrop", "resistance"], inEngineCatalog: false },
  invasive: { type: "invasive", scale: "regional", radiusDeg: 18, duration: 240, telegraph: 24, instrument: "bioSensor", chain: ["newLineage", "competition", "nicheShift"], inEngineCatalog: false },
};
export const EVENT_TYPES = Object.keys(EVENT_DEFS) as EventType[];

export type GeneBlock = "MET" | "MOR" | "TOL" | "LIF" | "BEH" | "TAG" | "REG";
export interface GeneDef { id: string; block: GeneBlock; kind: "bool" | "real" | "int" | "cat" | "sym"; min?: number; max?: number; log?: boolean; unit?: string; labelPt: string }
const g = (id: string, block: GeneBlock, kind: GeneDef["kind"], labelPt: string, min?: number, max?: number, unit?: string, log?: boolean): GeneDef => ({ id, block, kind, labelPt, min, max, unit, log });
/**
 * Gene catalog, Appendix A of the engine spec, as transcribed in docs/frontend/BRIEFING.md §4.
 * `labelPt` is normative domain text: it is NOT externalized as an editable UI string and must not be reworded.
 */
export const GENES: GeneDef[] = [
  g("photosynthesis", "MET", "bool", "Fotossíntese"), g("chemosynthesis", "MET", "bool", "Quimiossíntese"), g("plant_digestion", "MET", "bool", "Digestão vegetal"),
  g("animal_digestion", "MET", "bool", "Digestão animal"), g("detritivory", "MET", "bool", "Consumo de detritos"), g("decomposition", "MET", "bool", "Decomposição"),
  g("nitrogen_fixation", "MET", "bool", "Fixação de nitrogênio"), g("aerobic_respiration", "MET", "bool", "Respiração aeróbia"), g("anaerobic_respiration", "MET", "bool", "Respiração anaeróbia"),
  g("metabolic_efficiency", "MET", "real", "Eficiência metabólica", 0.1, 1), g("storage_capacity", "MET", "real", "Capacidade de reserva", 0.1, 2),
  g("adult_mass", "MOR", "real", "Massa adulta", 1e-6, 1e4, "kg", true), g("height", "MOR", "real", "Altura", 0, 100, "m"), g("canopy_area", "MOR", "real", "Área de captação", 0, 1000, "m²"),
  g("growth_rate", "MOR", "real", "Taxa de crescimento", 0.01, 0.5), g("structural_investment", "MOR", "real", "Investimento estrutural", 0, 1), g("offense_investment", "MOR", "real", "Investimento em ataque", 0, 1),
  g("mobility", "MOR", "real", "Mobilidade (0 = séssil)", 0, 1),
  g("temp_optimum", "TOL", "real", "Temperatura ideal", -40, 60, "°C"), g("temp_breadth", "TOL", "real", "Amplitude térmica", 1, 40, "°C"), g("humidity_optimum", "TOL", "real", "Umidade ideal", 0, 1),
  g("humidity_breadth", "TOL", "real", "Amplitude de umidade", 0.05, 1), g("ph_optimum", "TOL", "real", "pH ideal", 3, 11), g("ph_breadth", "TOL", "real", "Amplitude de pH", 0.5, 6),
  g("salinity_tolerance", "TOL", "real", "Tolerância à salinidade", 0, 45, "ppt"), g("water_retention", "TOL", "real", "Retenção de água", 0, 1), g("thermal_insulation", "TOL", "real", "Isolamento térmico", 0, 1),
  g("maturity_age", "LIF", "int", "Idade de maturidade", 1, 500, "ticks"), g("lifespan_modifier", "LIF", "real", "Modificador de longevidade", 0.5, 2), g("reproduction_threshold", "LIF", "real", "Limiar de reprodução", 0.3, 0.95),
  g("offspring_count", "LIF", "int", "Número de descendentes", 1, 1000, "", true), g("offspring_investment", "LIF", "real", "Investimento por descendente", 0.01, 0.5), g("reproductive_mode", "LIF", "cat", "Modo de reprodução", 0, 2),
  g("dormancy_capable", "LIF", "bool", "Capacidade de dormência"), g("dispersal_distance", "LIF", "int", "Distância de dispersão", 0, 10, "células"),
  g("w_forage", "BEH", "real", "Prioridade de alimentação", 0, 1), g("w_drink", "BEH", "real", "Prioridade de hidratação", 0, 1), g("w_move", "BEH", "real", "Prioridade de deslocamento", 0, 1),
  g("w_reproduce", "BEH", "real", "Prioridade de reprodução", 0, 1), g("w_flee", "BEH", "real", "Prioridade de fuga", 0, 1), g("w_attack", "BEH", "real", "Prioridade de ataque", 0, 1),
  g("w_rest", "BEH", "real", "Prioridade de repouso", 0, 1), g("w_aggregate", "BEH", "real", "Tendência a agrupar-se", 0, 1), g("perception_radius", "BEH", "real", "Raio de percepção", 1, 5, "células"),
  g("risk_aversion", "BEH", "real", "Aversão ao risco", 0, 1), g("philopatry", "BEH", "real", "Apego ao local de origem", 0, 1),
  g("appearance_tag", "TAG", "sym", "Aparência"), g("defense_tag", "TAG", "sym", "Marcador de defesa"), g("offense_tag", "TAG", "sym", "Marcador de ataque"), g("mating_tag", "TAG", "sym", "Marcador reprodutivo"),
  g("combat_condition", "TAG", "sym", "Regra de ataque"), g("trade_condition", "TAG", "sym", "Regra de troca"), g("mating_condition", "TAG", "sym", "Regra de acasalamento"),
  g("mutation_rate_modifier", "REG", "real", "Modificador de mutação", 0.1, 10, "", true), g("recombination_rate_modifier", "REG", "real", "Modificador de recombinação", 0.1, 10, "", true),
  g("plasticity", "REG", "real", "Plasticidade fenotípica", 0, 0.3), g("neutral_marker", "REG", "sym", "Marcador neutro (linha de base)"),
];
export const GENE_BY_ID: Record<string, GeneDef> = Object.fromEntries(GENES.map((x) => [x.id, x]));
export const METABOLIC_GENES = ["photosynthesis", "chemosynthesis", "plant_digestion", "animal_digestion", "detritivory", "decomposition", "nitrogen_fixation"] as const;
export const BEHAVIOR_WEIGHTS = ["w_forage", "w_drink", "w_move", "w_reproduce", "w_flee", "w_attack", "w_rest", "w_aggregate"] as const;
export const REPRODUCTIVE_MODES = ["assexuado", "sexuado", "facultativo"] as const; // values of the spec, Appendix A

export const ROLE_TROPHIC: Record<TrophicRole, number> = { phototroph: 0, chemotroph: 0, nitrogenFixer: 0, decomposer: 0, detritivore: 1, herbivore: 1, mixotroph: 1, carnivore: 2 };
