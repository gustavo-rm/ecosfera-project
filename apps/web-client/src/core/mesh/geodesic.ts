import { buildOrderedIcosphere, type OrderedIcosphere } from "./cellOrder";

export const EARTH_RADIUS_KM = 6371;

/** Geodesic mesh as the engine describes it (spec §6.2): centers, neighbors, n_neighbors, area_km2, latitude, parent. */
export interface GeodesicMesh extends OrderedIcosphere {
  /** (n, 6), -1 in the sixth slot of the 12 pentagonal cells. */
  neighbors: Int32Array;
  nNeighbors: Uint8Array;
  /** Index of the nearest cell in the previous level (itself if the cell already existed there). */
  parent: Int32Array;
  /** Degrees. */
  latitude: Float32Array;
  longitude: Float32Array;
  areaKm2: Float32Array;
}

const cache = new Map<number, GeodesicMesh>();

export function getMesh(level: number): GeodesicMesh {
  let m = cache.get(level);
  if (!m) { m = buildMesh(level); cache.set(level, m); }
  return m;
}

function buildMesh(level: number): GeodesicMesh {
  const ico = buildOrderedIcosphere(level);
  const { count, centers, indices, edgeParents } = ico;
  const neighbors = new Int32Array(count * 6).fill(-1);
  const nNeighbors = new Uint8Array(count);
  const areaKm2 = new Float32Array(count);
  const add = (a: number, b: number) => {
    const base = a * 6;
    for (let k = 0; k < nNeighbors[a]; k++) if (neighbors[base + k] === b) return;
    neighbors[base + nNeighbors[a]++] = b;
  };
  for (let f = 0; f < indices.length; f += 3) {
    const a = indices[f], b = indices[f + 1], c = indices[f + 2];
    add(a, b); add(a, c); add(b, a); add(b, c); add(c, a); add(c, b);
    // Flat triangle area on the unit sphere; one third goes to each corner cell.
    const ax = centers[a * 3], ay = centers[a * 3 + 1], az = centers[a * 3 + 2];
    const ux = centers[b * 3] - ax, uy = centers[b * 3 + 1] - ay, uz = centers[b * 3 + 2] - az;
    const vx = centers[c * 3] - ax, vy = centers[c * 3 + 1] - ay, vz = centers[c * 3 + 2] - az;
    const area = 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 3;
    areaKm2[a] += area; areaKm2[b] += area; areaKm2[c] += area;
  }
  let total = 0;
  for (let i = 0; i < count; i++) total += areaKm2[i];
  const scale = (4 * Math.PI * EARTH_RADIUS_KM ** 2) / total;
  const latitude = new Float32Array(count), longitude = new Float32Array(count), parent = new Int32Array(count);
  for (let i = 0; i < count; i++) {
    areaKm2[i] *= scale;
    latitude[i] = (Math.asin(centers[i * 3 + 1]) * 180) / Math.PI;
    longitude[i] = (Math.atan2(centers[i * 3 + 2], centers[i * 3]) * 180) / Math.PI;
    parent[i] = ico.birthLevel[i] === level && level > 0 ? edgeParents[i * 2] : i; // itself for old cells, lower-index edge endpoint for new ones
  }
  return { ...ico, neighbors, nNeighbors, parent, latitude, longitude, areaKm2 };
}

/** Nearest cell to a unit direction. Brute force is about 20 µs at level 5, so no index structure is needed. */
export function nearestCell(mesh: GeodesicMesh, x: number, y: number, z: number): number {
  const c = mesh.centers;
  let best = 0, bestDot = -2;
  for (let i = 0, n = mesh.count; i < n; i++) {
    const d = c[i * 3] * x + c[i * 3 + 1] * y + c[i * 3 + 2] * z;
    if (d > bestDot) { bestDot = d; best = i; }
  }
  return best;
}

export function latLonToDir(latDeg: number, lonDeg: number): [number, number, number] {
  const la = (latDeg * Math.PI) / 180, lo = (lonDeg * Math.PI) / 180;
  return [Math.cos(la) * Math.cos(lo), Math.sin(la), Math.cos(la) * Math.sin(lo)];
}

/**
 * Expands per-cell data (stride floats per cell) from the data level to a render level.
 * Coarser render levels read a prefix (cells keep their index). Finer levels average the two edge parents.
 */
export function expandToRenderLevel(src: Float32Array, dataMesh: GeodesicMesh, renderMesh: GeodesicMesh, stride: number, dst: Float32Array): void {
  const nData = dataMesh.count, nRender = renderMesh.count;
  if (nRender <= nData) { dst.set(src.subarray(0, nRender * stride)); return; }
  dst.set(src);
  const ep = renderMesh.edgeParents;
  for (let i = nData; i < nRender; i++) {
    const a = ep[i * 2] * stride, b = ep[i * 2 + 1] * stride, o = i * stride;
    for (let k = 0; k < stride; k++) dst[o + k] = 0.5 * (dst[a + k] + dst[b + k]);
  }
}
