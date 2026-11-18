import { describe, expect, it } from "vitest";
import { cellCountForLevel } from "../mesh/cellOrder";
import { expandToRenderLevel, getMesh, nearestCell } from "../mesh/geodesic";

describe("geodesic mesh (spec §6.2, DEC-04)", () => {
  it("has 10·4^L+2 cells; level 5 has 10 242, 12 of them pentagonal", () => {
    expect([3, 4, 5].map(cellCountForLevel)).toEqual([642, 2562, 10242]);
    const m = getMesh(5);
    let pent = 0;
    for (let i = 0; i < m.count; i++) { if (m.nNeighbors[i] === 5) { pent++; expect(m.neighbors[i * 6 + 5]).toBe(-1); } else expect(m.nNeighbors[i]).toBe(6); }
    expect(pent).toBe(12);
    const area = m.areaKm2.reduce((s, a) => s + a, 0);
    expect(area / 5.1e8).toBeCloseTo(1, 2);
    expect(area / m.count).toBeGreaterThan(45000); // about 50 000 km² per cell
  });
  it("keeps cell indices across levels (prefix property) and gives a valid parent", () => {
    const m4 = getMesh(4), m5 = getMesh(5);
    for (let i = 0; i < m4.count * 3; i += 97) expect(m5.centers[i]).toBe(m4.centers[i]);
    for (let i = 0; i < m5.count; i++) { const p = m5.parent[i]; expect(p).toBeLessThan(m4.count); if (i < m4.count) expect(p).toBe(i); }
  });
  it("finds the cell under a direction and expands data to a finer render level", () => {
    const m = getMesh(4), i = 1234;
    expect(nearestCell(m, m.centers[i * 3], m.centers[i * 3 + 1], m.centers[i * 3 + 2])).toBe(i);
    const r = getMesh(5), src = new Float32Array(m.count).fill(2), dst = new Float32Array(r.count);
    expandToRenderLevel(src, m, r, 1, dst);
    expect(dst[r.count - 1]).toBe(2);
  });
});
