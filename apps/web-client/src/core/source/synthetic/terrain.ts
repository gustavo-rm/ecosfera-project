import { fbm3, noise3, ridged3 } from "../../math/noise";
import { mulberry32 } from "../../math/rng";
import type { GeodesicMesh } from "../../mesh/geodesic";
import type { PlanetParams } from "../../state/types";

export interface Terrain {
  /** Meters around the elevation datum (0). Sea level is a separate global. */
  elevation: Float32Array;
  sorted: Float32Array;
  ridge: Float32Array;
  noiseA: Float32Array; noiseB: Float32Array;
  hotspots: number[];
}

function rawElevation(mesh: GeodesicMesh, p: PlanetParams, seed: number, ridgeOut: Float32Array | null): Float32Array {
  const n = mesh.count, c = mesh.centers, out = new Float32Array(n);
  const f = 1.05 + 2.6 * p.landDistribution;
  const amp = 6000 * (0.35 + 1.2 * p.relief);
  for (let i = 0; i < n; i++) {
    const x = c[i * 3], y = c[i * 3 + 1], z = c[i * 3 + 2];
    const wx = fbm3(x * 1.7 + 11, y * 1.7, z * 1.7, seed + 900, 3) - 0.5;
    const wy = fbm3(x * 1.7, y * 1.7 + 7, z * 1.7, seed + 901, 3) - 0.5;
    const cont = fbm3(x * f + wx, y * f + wy, z * f - wx, seed, 5) * 2 - 1;
    const shaped = Math.sign(cont) * Math.abs(cont) ** 0.85;
    const r = ridged3(x * f * 2.2, y * f * 2.2, z * f * 2.2, seed + 300, 4);
    const belt = Math.exp(-((cont - 0.12) ** 2) / 0.03); // ranges near continental margins
    const mountain = r * r * (0.25 + 1.4 * p.tectonics) * (0.35 + belt);
    const detail = fbm3(x * 9, y * 9, z * 9, seed + 500, 3) - 0.5;
    out[i] = amp * (shaped * 1.25 + mountain * 0.55 * (cont > -0.2 ? 1 : 0.3) + detail * 0.12);
    if (ridgeOut) ridgeOut[i] = r * belt;
  }
  return out;
}

export function buildTerrain(mesh: GeodesicMesh, p: PlanetParams, driftPhase: number): Terrain {
  const n = mesh.count, c = mesh.centers;
  const ridge = new Float32Array(n);
  const a = rawElevation(mesh, p, p.seed, ridge);
  if (driftPhase > 0) {
    const b = rawElevation(mesh, p, p.seed + 7919, null);
    for (let i = 0; i < n; i++) a[i] += (b[i] - a[i]) * driftPhase;
  }
  const sorted = Float32Array.from(a).sort();
  const noiseA = new Float32Array(n), noiseB = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    noiseA[i] = noise3(c[i * 3] * 5 + 3, c[i * 3 + 1] * 5, c[i * 3 + 2] * 5, p.seed + 41);
    noiseB[i] = fbm3(c[i * 3] * 3, c[i * 3 + 1] * 3 + 9, c[i * 3 + 2] * 3, p.seed + 43, 3);
  }
  const rng = mulberry32(p.seed * 31 + 5);
  const hotspots: number[] = [];
  const want = Math.round(p.volcanism * 10);
  for (let tries = 0; hotspots.length < want && tries < 4000; tries++) {
    const i = Math.floor(rng() * n);
    if (ridge[i] > 0.45 || tries > 3000) hotspots.push(i);
  }
  return { elevation: a, sorted, ridge, noiseA, noiseB, hotspots };
}

/** Sea level (m) such that `fraction` of the cells lie below it. */
export function seaLevelFor(t: Terrain, fraction: number): number {
  if (fraction <= 0.002) return -1e5;
  const n = t.sorted.length;
  return t.sorted[Math.min(n - 1, Math.floor(fraction * (n - 1)))];
}

/** Moisture reach from the ocean: 1 at the coast, decaying inland (breadth-first search over neighbors). */
export function oceanMoisture(mesh: GeodesicMesh, isWater: Uint8Array): Float32Array {
  const n = mesh.count, dist = new Int16Array(n).fill(-1), out = new Float32Array(n);
  let queue: number[] = [];
  for (let i = 0; i < n; i++) if (isWater[i]) { dist[i] = 0; queue.push(i); }
  if (queue.length === 0) return out;
  while (queue.length) {
    const next: number[] = [];
    for (const i of queue) {
      for (let k = 0; k < 6; k++) {
        const j = mesh.neighbors[i * 6 + k];
        if (j >= 0 && dist[j] < 0) { dist[j] = dist[i] + 1; next.push(j); }
      }
    }
    queue = next;
  }
  const reach = 1.1 * 2 ** (mesh.level - 3); // same angular reach at every mesh level
  for (let i = 0; i < n; i++) out[i] = dist[i] < 0 ? 0 : Math.exp(-dist[i] / reach);
  return out;
}
