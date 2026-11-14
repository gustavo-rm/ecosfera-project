/**
 * State -> appearance. Pure and deterministic (principle 8): the same frame and view options always give the
 * same channels and uniforms. This is where every row of the "variável do estado → efeito no planeta" table lives.
 *
 * Per-cell channels (4 floats each), consumed by render/shaders:
 *   A = (height above sea / 8000 m [signed], ice, lava/emissive, cloud cover)
 *   B = (r, g, b of the stylized land surface, vegetation cover)
 *   C = (data layer value 0..1, revealed 0..1, water tint [bloom], fire)
 *   D = (drought, storm, dark matter [ash, crater, dead zone], highlight [habitat, bio event])
 */
import { hash4, clamp, lerp, smoothstep } from "../math/rng";
import type { GeodesicMesh } from "../mesh/geodesic";
import { CRUST_COLORS, STAR_TABLE } from "../state/catalogs";
import type { PlanetFrame } from "../state/types";
import { categoryColor, LAYER_BY_ID, type LayerId } from "./layers";

export const HEIGHT_SCALE_M = 8000;
export interface ViewOptions {
  layer: LayerId | null;
  /** Per-cell 1 = revealed by research/scan. Null = everything revealed. */
  revealed: Uint8Array | null;
  /** Highlight the distribution of the observed lineage (Códex "habitat"). */
  showHabitat: boolean;
}
export interface PlanetUniforms {
  skyColor: [number, number, number]; atmoDensity: number; haze: number; terminatorSoftness: number;
  cloudColor: [number, number, number]; cloudOpacity: number;
  oceanShallow: [number, number, number]; oceanDeep: [number, number, number];
  starColor: [number, number, number]; starIntensity: number; starSize: number;
  surfaceHeat: number; desaturate: number; aurora: number; sunDim: number; erosion: number;
  /** 0 natural, 1 scalar via LUT, 2 categorical via channel B. */
  layerMode: 0 | 1 | 2; layerKind: "sequential" | "diverging" | "categorical";
  axialTiltDeg: number; yearPhase: number; eccentricity: number; moons: number; dayHours: number; seed: number;
}
export interface Appearance { A: Float32Array; B: Float32Array; C: Float32Array; D: Float32Array; grad: Float32Array; uniforms: PlanetUniforms; gradKey: string }

export function createAppearance(n: number): Appearance {
  return { A: new Float32Array(n * 4), B: new Float32Array(n * 4), C: new Float32Array(n * 4), D: new Float32Array(n * 4), grad: new Float32Array(n * 3), uniforms: null as unknown as PlanetUniforms, gradKey: "" };
}

export function computeUniforms(frame: PlanetFrame, view: ViewOptions): PlanetUniforms {
  const g = frame.globals, p = frame.params;
  const o2f = clamp(g.o2Pct / 21);
  const haze = g.pressureBar <= 0.02 ? 0 : clamp(Math.log10(Math.max(1, g.co2Ppm / 400)) / 2.5) * 0.6 + clamp(Math.log10(1 + g.ch4Ppm / 1.8) / 3) * 0.6;
  const blue: [number, number, number] = [0.30 * (0.4 + 0.6 * o2f) + 0.2 * (1 - o2f), 0.52 * (0.45 + 0.55 * o2f) + 0.22 * (1 - o2f), 1.0 * (0.5 + 0.5 * o2f)];
  const orange: [number, number, number] = [0.98, 0.55, 0.24];
  const dust: [number, number, number] = [0.27, 0.23, 0.2];
  const k = clamp(haze), a = clamp(g.aerosols * 0.85);
  const sky = blue.map((b, i) => lerp(lerp(b, orange[i], k), dust[i], a)) as [number, number, number];
  const boil = smoothstep(70, 125, g.meanTempC) * (g.surfaceHeat > 0.3 ? 0 : 1);
  const star = STAR_TABLE[p.starType];
  const prim = 1 - o2f;
  const phAcid = clamp((7.2 - g.oceanPh) / 3), sal = (g.salinityPpt - 35) / 35;
  const layer = view.layer ? LAYER_BY_ID[view.layer] : null;
  return {
    skyColor: sky, atmoDensity: clamp(Math.pow(Math.max(0, g.pressureBar), 0.5) * 0.58), haze: clamp(haze * 0.55 + g.aerosols * 0.8 + boil * 0.5),
    terminatorSoftness: 0.02 + 0.22 * clamp(g.pressureBar),
    cloudColor: [lerp(1, 0.96, boil) - 0.35 * a, lerp(1, 0.86, boil) - 0.38 * a - 0.08 * k, lerp(1, 0.62, boil) - 0.4 * a - 0.2 * k],
    cloudOpacity: g.pressureBar < 0.03 ? 0 : clamp(0.55 + 0.4 * boil + 0.25 * a + 0.15 * k),
    oceanShallow: [lerp(0.05, 0.12, prim * 0.6) + 0.1 * phAcid + 0.02 * sal, lerp(0.36, 0.33, prim * 0.6) + 0.02 * sal, lerp(0.52, 0.3, prim * 0.6) - 0.12 * phAcid - 0.03 * sal],
    oceanDeep: [lerp(0.01, 0.04, prim * 0.6) + 0.04 * phAcid, lerp(0.07, 0.11, prim * 0.6), lerp(0.23, 0.14, prim * 0.6) - 0.05 * phAcid],
    starColor: star.color, starIntensity: clamp(0.55 + 0.45 * Math.sqrt(g.starFlux), 0.35, 1.6), starSize: clamp((star.size / Math.max(0.1, p.orbitAU)) * 0.9, 0.25, 3.5),
    surfaceHeat: g.surfaceHeat, desaturate: clamp(g.extinctionPulse * 0.75), aurora: g.pressureBar < 0.03 ? 0 : clamp(g.magneticField * (0.25 + 1.5 * g.starActivity)),
    sunDim: 1 - 0.55 * a, erosion: clamp((0.25 - g.magneticField) / 0.25) * g.starActivity * clamp(g.pressureBar * 4),
    layerMode: !layer ? 0 : layer.kind === "categorical" ? 2 : 1, layerKind: layer?.kind ?? "sequential",
    axialTiltDeg: p.axialTiltDeg, yearPhase: g.yearPhase, eccentricity: p.eccentricity, moons: p.moons, dayHours: p.dayHours, seed: p.seed,
  };
}

const V_COLD = [0.20, 0.38, 0.27], V_TEMP = [0.26, 0.52, 0.20], V_TROP = [0.10, 0.42, 0.13], V_DRY = [0.62, 0.62, 0.28];
const SAND: [number, number, number] = [0.80, 0.68, 0.46];
const DARK_MATTER: [number, number, number] = [0.13, 0.10, 0.08];

export function computeAppearance(frame: PlanetFrame, mesh: GeodesicMesh, view: ViewOptions, out: Appearance): Appearance {
  const f = frame.fields, g = frame.globals, n = frame.cellCount;
  const { A, B, C, D } = out;
  const rock = CRUST_COLORS[frame.params.crust];
  const dryWorld = g.seaLevelM < -9e4;
  // Without an ocean there is no sea level: heights are measured from the lowest point and compressed.
  const sea = dryWorld ? f.elevation.reduce((m, v) => Math.min(m, v), 0) : g.seaLevelM;
  const layer = view.layer ? LAYER_BY_ID[view.layer] : null;
  const span = layer ? layer.max - layer.min : 1;
  const stuck = g.organicStuck, rich = 1 / 6;
  for (let i = 0; i < n; i++) {
    const o = i * 4, hRel = dryWorld ? 0.002 + ((f.elevation[i] - sea) / HEIGHT_SCALE_M) * 0.45 : (f.elevation[i] - sea) / HEIGHT_SCALE_M, isW = f.isWater[i] === 1;
    A[o] = hRel; A[o + 1] = f.ice[i]; A[o + 2] = f.lava[i]; A[o + 3] = f.cloud[i];
    // --- stylized land color: crust palette -> altitude -> aridity -> soil fertility -> vegetation -> dead matter
    const hum = f.humidity[i], fert = f.soilFertility[i];
    const alt = smoothstep(0.15, 0.6, hRel), arid = isW ? 0 : (1 - smoothstep(0.1, 0.42, hum)) * (g.oceanFraction > 0.02 ? 0.7 : 0.15) * smoothstep(-2, 14, f.temperature[i]);
    let r = lerp(rock[0], 0.63, alt * 0.6), gr = lerp(rock[1], 0.61, alt * 0.6), b = lerp(rock[2], 0.6, alt * 0.6);
    r = lerp(r, SAND[0], arid); gr = lerp(gr, SAND[1], arid); b = lerp(b, SAND[2], arid);
    const soil = fert * 0.5;
    r = lerp(r, r * 0.62, soil); gr = lerp(gr, gr * 0.55, soil); b = lerp(b, b * 0.42, soil);
    const veg = isW ? 0 : clamp(f.biomassPhoto[i]);
    if (veg > 0.01) {
      // Continuous in temperature and moisture so that biome borders do not show as hard bands.
      const tw = smoothstep(-6, 12, f.temperature[i]), th = smoothstep(14, 26, f.temperature[i]), wet = smoothstep(0.25, 0.6, hum);
      const vc: [number, number, number] = [
        lerp(lerp(lerp(V_COLD[0], V_TEMP[0], tw), V_TROP[0], th), V_DRY[0], 1 - wet), lerp(lerp(lerp(V_COLD[1], V_TEMP[1], tw), V_TROP[1], th), V_DRY[1], 1 - wet),
        lerp(lerp(lerp(V_COLD[2], V_TEMP[2], tw), V_TROP[2], th), V_DRY[2], 1 - wet),
      ];
      // Variety of hue from the dominant lineage, scaled by local richness (biodiversity row of the table).
      const hv = (hash4(f.domProducer[i], 7, 1, 0) - 0.5) * clamp(f.richness[i] * rich) * 0.22;
      const cover = smoothstep(0.02, 0.6, veg);
      r = lerp(r, vc[0] + hv, cover); gr = lerp(gr, vc[1] + hv * 0.4, cover); b = lerp(b, vc[2] - hv * 0.6, cover);
    }
    const dead = clamp(f.organicMatter[i] * stuck * 1.2);
    r = lerp(r, DARK_MATTER[0], dead * 0.75); gr = lerp(gr, DARK_MATTER[1], dead * 0.75); b = lerp(b, DARK_MATTER[2], dead * 0.75);
    B[o] = r; B[o + 1] = gr; B[o + 2] = b; B[o + 3] = veg;
    // --- data layer
    let lv = 0;
    if (layer) {
      const v = layer.value(f, i, frame);
      if (layer.kind === "categorical") { const cc = categoryColor(layer.id, v); B[o] = cc[0]; B[o + 1] = cc[1]; B[o + 2] = cc[2]; }
      else lv = clamp((v - layer.min) / span);
      if ((layer.domain === "water" && !isW) || (layer.domain === "land" && isW)) lv = -1; // not applicable here: drawn neutral
    }
    C[o] = lv; C[o + 1] = view.revealed ? view.revealed[i] : 1; C[o + 2] = f.bloom[i]; C[o + 3] = f.fire[i];
    D[o] = f.drought[i]; D[o + 1] = f.storm[i];
    D[o + 2] = clamp(Math.max(f.ash[i] * 0.7, f.crater[i], isW ? f.eutro[i] * 0.55 : 0));
    D[o + 3] = clamp(Math.max(f.bioMark[i], view.showHabitat && f.observed ? f.observed[i] * 1.4 : 0));
  }
  // Tangent gradient of land height, for shading the relief. Recomputed only when relief or sea level change.
  const key = `${frame.level}|${f.elevation.byteOffset}|${f.elevation[0]}|${f.elevation[n - 1]}|${Math.round(sea)}`;
  if (key !== out.gradKey) {
    out.gradKey = key;
    const c = mesh.centers, gradient = out.grad;
    for (let i = 0; i < n; i++) {
      const hi = Math.max(0, A[i * 4]), cx = c[i * 3], cy = c[i * 3 + 1], cz = c[i * 3 + 2];
      let gx = 0, gy = 0, gz = 0;
      const k = mesh.nNeighbors[i];
      for (let q = 0; q < k; q++) {
        const j = mesh.neighbors[i * 6 + q], dh = Math.max(0, A[j * 4]) - hi;
        const dx = c[j * 3] - cx, dy = c[j * 3 + 1] - cy, dz = c[j * 3 + 2] - cz, d2 = dx * dx + dy * dy + dz * dz;
        gx += (dh * dx) / d2; gy += (dh * dy) / d2; gz += (dh * dz) / d2;
      }
      gradient[i * 3] = (gx * 2) / k; gradient[i * 3 + 1] = (gy * 2) / k; gradient[i * 3 + 2] = (gz * 2) / k;
    }
  }
  out.uniforms = computeUniforms(frame, view);
  return out;
}
