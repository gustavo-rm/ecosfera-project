import type { PlanetFrame, SeriesHistory, UpdateMode } from "../state/types";
import type { PlanetStateSource, SourceInfo, SourceMessage } from "./port";

/** Recorded snapshots as a data source: replays exported frames. Used for fixtures, demos and regression images. */
export interface FixtureFile { format: "ecosfera-fixture"; version: 1; note: string; frames: unknown[] }
const TYPED: Record<string, new (b: ArrayBuffer) => ArrayLike<number>> = { Float32Array, Uint8Array, Int16Array };

function encode(value: unknown): unknown {
  if (ArrayBuffer.isView(value)) {
    const v = value as Float32Array | Uint8Array | Int16Array, bytes = new Uint8Array(v.buffer, v.byteOffset, v.byteLength);
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return { $typed: v.constructor.name, data: btoa(bin) };
  }
  if (Array.isArray(value)) return value.map(encode);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, x]) => [k, encode(x)]));
  return value;
}
function decode(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(decode);
  if (value && typeof value === "object") {
    const o = value as Record<string, unknown>;
    if (typeof o.$typed === "string" && typeof o.data === "string" && TYPED[o.$typed]) {
      const bin = atob(o.data), bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return new TYPED[o.$typed](bytes.buffer);
    }
    return Object.fromEntries(Object.entries(o).map(([k, x]) => [k, decode(x)]));
  }
  return value;
}
export function exportFixture(frames: PlanetFrame[], note = ""): string {
  return JSON.stringify({ format: "ecosfera-fixture", version: 1, note, frames: frames.map(encode) } satisfies FixtureFile);
}
export function importFixture(json: string): PlanetFrame[] {
  const file = JSON.parse(json) as FixtureFile;
  if (file.format !== "ecosfera-fixture" || !Array.isArray(file.frames) || file.frames.length === 0) throw new Error("not an ECOSFERA fixture");
  return (file.frames.map(decode) as PlanetFrame[]).sort((a, b) => a.tick - b.tick);
}

export class FixtureSource implements PlanetStateSource {
  readonly kind = "fixture" as const;
  private listeners = new Set<(m: SourceMessage) => void>();
  private index = 0;
  private timer: ReturnType<typeof setInterval> | null = null;
  constructor(private frames: PlanetFrame[]) {}
  private emit(m: SourceMessage) { this.listeners.forEach((l) => l(m)); }
  private show() { this.emit({ type: "frame", frame: this.frames[this.index] }); }
  start(): Promise<SourceInfo> {
    const f = this.frames, first = f[0], last = f[f.length - 1];
    const eras = f.reduce<{ era: number; start: number }[]>((a, x) => (a.some((e) => e.era === x.globals.era) ? a : [...a, { era: x.globals.era, start: x.globals.eraStartTick }]), []);
    const info: SourceInfo = { kind: "fixture", synthetic: first.meta.synthetic, scenarioId: first.meta.scenarioId, level: first.level, startTick: first.tick, endTick: Math.max(last.tick, first.tick + 1), eras };
    this.index = 0;
    queueMicrotask(() => { this.emit({ type: "ready", info }); this.show(); });
    return Promise.resolve(info);
  }
  subscribe(l: (m: SourceMessage) => void) { this.listeners.add(l); return () => { this.listeners.delete(l); }; }
  setClock(playing: boolean, speed: number, mode: UpdateMode) {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (playing) this.timer = setInterval(() => { if (this.index >= this.frames.length - 1) { this.setClock(false, speed, "normal"); return; } this.index++; this.show(); }, 900);
    this.emit({ type: "clock", playing, speed, mode });
  }
  seek(tick: number) { let best = 0; this.frames.forEach((f, i) => { if (Math.abs(f.tick - tick) < Math.abs(this.frames[best].tick - tick)) best = i; }); this.index = best; this.show(); }
  runUntil(tick: number) { this.seek(tick); }
  /** Recorded data cannot react to commands: they are ignored on purpose. */
  dispatch() {}
  getHistory(): Promise<SeriesHistory> {
    const f = this.frames, pops: Record<string, number[]> = {};
    for (const s of f[f.length - 1].bio.species) pops[s.id] = f.map((x) => x.bio.species.find((y) => y.id === s.id)?.population ?? 0);
    return Promise.resolve({ ticks: f.map((x) => x.tick), o2: f.map((x) => x.globals.o2Pct), co2: f.map((x) => x.globals.co2Ppm), temp: f.map((x) => x.globals.meanTempC), biomass: f.map((x) => x.globals.totalBiomass), shannon: f.map((x) => x.bio.shannon), richness: f.map((x) => x.bio.richness),
      geneticDistance: f.map((x) => x.bio.geneticDistance), strategies: f.map((x) => x.bio.metabolicStrategies), webComplexity: f.map((x) => x.bio.trophicLevels + x.bio.connectance * 10), originations: f.map((x) => x.bio.originationRate), extinctions: f.map((x) => x.bio.extinctionRate), populations: pops, marks: [] });
  }
  dispose() { if (this.timer) clearInterval(this.timer); this.listeners.clear(); }
}
