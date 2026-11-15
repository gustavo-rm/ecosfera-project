/**
 * Locks the cell order of the geodesic mesh. The engine spec (§6.2, DEC-04) fixes the structure of the mesh but not
 * the order of the vertices, so this order is the frontend's convention until the data contract says otherwise
 * (docs/frontend/DECISOES.md, D-29). If this test fails, the order changed: that invalidates fixtures and saves.
 */
import { describe, expect, it } from "vitest";
import { buildOrderedIcosphere, cellCountForLevel } from "../mesh/cellOrder";
import { getMesh } from "../mesh/geodesic";

/** FNV-1a over the centers rounded to 1e-5, order-sensitive. */
function fingerprint(level: number): string {
  const c = buildOrderedIcosphere(level).centers;
  let h = 2166136261;
  for (let i = 0; i < c.length; i++) { h ^= Math.round(c[i] * 1e5) + 200000; h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16).padStart(8, "0");
}
const FINGERPRINTS: Record<number, string> = { 0: "d800a305", 1: "1d331d5d", 2: "3fe7a3e5", 3: "8cdb6bb9", 5: "8eb3ac53" };

describe("cell order (spec §6.2, DEC-04)", () => {
  it("matches the structure the spec describes: GeodesicGrid fields and sizes", () => {
    const m = getMesh(5);
    expect(m.count).toBe(10242);                               // GRID_SUBDIVISION = 5
    expect(m.centers.length).toBe(m.count * 3);                // centers (n_cells, 3), unit vectors
    expect(m.neighbors.length).toBe(m.count * 6);              // neighbors (n_cells, 6), -1 on pentagonal cells
    expect(m.nNeighbors.length).toBe(m.count); expect(m.areaKm2.length).toBe(m.count); expect(m.latitude.length).toBe(m.count); expect(m.parent.length).toBe(m.count);
    for (let i = 0; i < m.count; i += 53) expect(Math.hypot(m.centers[i * 3], m.centers[i * 3 + 1], m.centers[i * 3 + 2])).toBeCloseTo(1, 5);
    const mean = m.areaKm2.reduce((a, b) => a + b, 0) / m.count;
    expect(mean).toBeGreaterThan(49000); expect(mean).toBeLessThan(51000); // "about 50 000 km² each"
  });
  it("the 12 pentagonal cells are the first 12 indices, at every level", () => {
    for (const level of [1, 3, 5]) { const m = getMesh(level); for (let i = 0; i < m.count; i++) expect(m.nNeighbors[i]).toBe(i < 12 ? 5 : 6); }
  });
  it("level 0 starts with the documented icosahedron vertices", () => {
    const c = buildOrderedIcosphere(0).centers, t = (1 + Math.sqrt(5)) / 2, l = Math.hypot(1, t);
    expect([c[0], c[1], c[2]].map((v) => +v.toFixed(5))).toEqual([+(-1 / l).toFixed(5), +(t / l).toFixed(5), 0]);
    expect([c[33], c[34], c[35]].map((v) => +v.toFixed(5))).toEqual([+(-t / l).toFixed(5), 0, +(1 / l).toFixed(5)]);
  });
  it("the order is frozen (fingerprint per level)", () => {
    const got = Object.fromEntries(Object.keys(FINGERPRINTS).map((k) => [k, fingerprint(Number(k))]));
    console.log("\nimpressões digitais da ordem das células:", JSON.stringify(got));
    expect(got).toEqual(Object.fromEntries(Object.entries(FINGERPRINTS)));
  });
  it("cells keep their index when the mesh is subdivided, and new cells come after all old ones", () => {
    for (const level of [1, 2, 3, 4, 5]) {
      const a = buildOrderedIcosphere(level - 1), b = buildOrderedIcosphere(level);
      expect(Array.from(b.centers.subarray(0, a.count * 3))).toEqual(Array.from(a.centers));
      for (let i = a.count; i < b.count; i++) expect(b.birthLevel[i]).toBe(level);
      expect(b.count).toBe(cellCountForLevel(level));
    }
  });
  it("parent is an index in the previous level: itself for an old cell, an adjacent mother cell for a new one", () => {
    const m = getMesh(4), prev = cellCountForLevel(3);
    const children = new Array(prev).fill(0);
    for (let i = 0; i < m.count; i++) {
      const p = m.parent[i];
      expect(p).toBeLessThan(prev);
      if (i < prev) expect(p).toBe(i);
      else { expect(Array.from(m.neighbors.subarray(i * 6, i * 6 + 6))).toContain(p); expect(p).toBe(Math.min(m.edgeParents[i * 2], m.edgeParents[i * 2 + 1])); }
      children[p]++;
    }
    // Every cell of the finer level belongs to exactly one mother cell: aggregation is a reduction by index.
    expect(children.reduce((a, b) => a + b, 0)).toBe(m.count);
    expect(Math.max(...children)).toBeLessThanOrEqual(7);
  });
});
