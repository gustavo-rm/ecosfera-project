import { BIOME_COLORS } from "../state/catalogs";
import type { CellFields, PlanetFrame } from "../state/types";
import type { RGB } from "./palettes";

export type LayerId = "temperature" | "biome" | "population" | "water" | "mineral" | "nitrogen" | "organicMatter" | "precipitation" | "o2" | "co2" | "elevation"
  | "fertility" | "biomass" | "richness" | "habitat" | "disturbance" | "salinity" | "ph";
export interface LayerDef {
  id: LayerId; group: "climate" | "life" | "resources" | "chemistry" | "terrain";
  kind: "sequential" | "diverging" | "categorical"; unit: string; min: number; max: number;
  value: (f: CellFields, i: number, frame: PlanetFrame) => number;
  /** Research node that unlocks the layer (progressive disclosure). Null = available from the start. */
  requires: string | null;
  /** Only meaningful over water or over land. */
  domain?: "water" | "land";
}
const L = (id: LayerId, group: LayerDef["group"], kind: LayerDef["kind"], unit: string, min: number, max: number, value: LayerDef["value"], requires: string | null = null, domain?: LayerDef["domain"]): LayerDef => ({ id, group, kind, unit, min, max, value, requires, domain });

/** Data layers over the globe (RF-054). The first four are the ones the GDD lists; the others are revealed by research. */
export const LAYERS: LayerDef[] = [
  L("temperature", "climate", "diverging", "°C", -50, 50, (f, i) => f.temperature[i]),
  L("biome", "life", "categorical", "", 0, 12, (f, i) => f.biome[i]),
  L("population", "life", "sequential", "", 0, 3, (f, i) => f.biomassHerb[i] + f.biomassCarn[i] * 2),
  L("water", "resources", "sequential", "", 0, 1, (f, i) => f.water[i]),
  L("precipitation", "climate", "sequential", "mm/mês", 0, 260, (f, i) => f.precipitation[i], "sci.waterCycle"),
  L("elevation", "terrain", "diverging", "m", -8000, 8000, (f, i, fr) => f.elevation[i] - (fr.globals.seaLevelM < -9e4 ? 0 : fr.globals.seaLevelM)),
  L("fertility", "resources", "sequential", "", 0, 1, (f, i) => f.soilFertility[i], "sci.soil", "land"),
  L("biomass", "life", "sequential", "", 0, 1.2, (f, i) => f.biomassPhoto[i], "sci.photosynthesis"),
  L("richness", "life", "sequential", "linhagens", 0, 10, (f, i) => f.richness[i], "sci.speciation"),
  L("habitat", "life", "sequential", "", 0, 1, (f, i) => (f.observed ? f.observed[i] : 0), "sci.speciation"),
  L("o2", "chemistry", "sequential", "%", 0, 30, (f, i) => f.o2[i], "sci.atmosphere"),
  L("co2", "chemistry", "sequential", "ppm", 0, 2000, (f, i) => f.co2[i], "sci.greenhouse"),
  L("mineral", "resources", "sequential", "", 0, 1, (f, i) => f.mineral[i], "sci.geology"),
  L("nitrogen", "resources", "sequential", "", 0, 1, (f, i) => f.nitrogen[i], "sci.cycles"),
  L("organicMatter", "resources", "sequential", "", 0, 1, (f, i) => f.organicMatter[i], "sci.decomposition"),
  L("disturbance", "climate", "sequential", "", 0, 1, (f, i) => Math.max(f.fire[i], f.drought[i], f.storm[i], f.ash[i], f.eutro[i], f.crater[i], f.bioMark[i]), "sci.resilience"),
  L("salinity", "chemistry", "sequential", "ppt", 0, 45, (f, i) => f.salinity[i], "sci.oceans", "water"),
  L("ph", "chemistry", "diverging", "pH", 3, 11, (f, i) => f.ph[i], "sci.oceans"),
];
export const LAYER_BY_ID = Object.fromEntries(LAYERS.map((l) => [l.id, l])) as Record<LayerId, LayerDef>;
export const BASE_LAYERS: LayerId[] = ["temperature", "biome", "population", "water"];

export function categoryColor(layer: LayerId, value: number): RGB {
  if (layer === "biome") return BIOME_COLORS[Math.max(0, Math.min(BIOME_COLORS.length - 1, Math.round(value)))];
  return [0.5, 0.5, 0.5];
}
