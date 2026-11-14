import type { PlanetFrame } from "@/core/state/types";

/** Circular buffer of planet snapshots for timeline scrubbing and before/after comparison (RF-059). */
export class SnapshotBuffer {
  private items: PlanetFrame[] = [];
  constructor(public capacity = 24, public minSpacing = 60) {}
  get size() { return this.items.length; }
  clear() { this.items = []; }
  /** Keeps frames ordered by tick. Frames closer than minSpacing to a stored one replace it. Returns true if stored. */
  push(frame: PlanetFrame): boolean {
    const it = this.items;
    let i = it.findIndex((f) => f.tick >= frame.tick - this.minSpacing * 0.5);
    if (i < 0) i = it.length;
    if (it[i] && Math.abs(it[i].tick - frame.tick) < this.minSpacing) { if (it[i].tick === frame.tick) return false; it[i] = frame; return true; }
    it.splice(i, 0, frame);
    if (it.length > this.capacity) {
      // Drop the frame whose neighbors are closest together, so coverage of the timeline stays even.
      let drop = 1, best = Infinity;
      for (let k = 1; k < it.length - 1; k++) { const gap = it[k + 1].tick - it[k - 1].tick; if (gap < best) { best = gap; drop = k; } }
      it.splice(drop, 1);
    }
    return true;
  }
  nearest(tick: number): PlanetFrame | null {
    let best: PlanetFrame | null = null, d = Infinity;
    for (const f of this.items) { const x = Math.abs(f.tick - tick); if (x < d) { d = x; best = f; } }
    return best;
  }
  bracket(tick: number): { before: PlanetFrame | null; after: PlanetFrame | null } {
    let before: PlanetFrame | null = null, after: PlanetFrame | null = null;
    for (const f of this.items) { if (f.tick <= tick) before = f; else if (!after) after = f; }
    return { before, after };
  }
  ticks(): number[] { return this.items.map((f) => f.tick); }
}
