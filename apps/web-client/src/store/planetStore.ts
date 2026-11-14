"use client";
import { create } from "zustand";
import type { LayerId } from "@/core/appearance/layers";
import type { PlanetStateSource, SourceCommand, SourceConfig, SourceInfo } from "@/core/source/port";
import { SyntheticSource } from "@/core/source/SyntheticSource";
import type { PlanetFrame, SeriesHistory, UpdateMode } from "@/core/state/types";
import { SnapshotBuffer } from "./snapshotBuffer";

export type QualityLevel = "low" | "medium" | "high";
export const SPEEDS = [{ id: "month", ticksPerSecond: 1 }, { id: "year", ticksPerSecond: 12 }, { id: "decade", ticksPerSecond: 120 }] as const;

export interface PlanetStore {
  status: "idle" | "loading" | "ready" | "error";
  errorDetail: string | null;
  info: SourceInfo | null;
  config: SourceConfig | null;
  /** The frame on screen. Changes a few times per second at most; the render layer reads it through subscribe. */
  frame: PlanetFrame | null;
  playing: boolean; speed: number; mode: UpdateMode;
  layer: LayerId | null; compareTick: number | null;
  showClouds: boolean; exaggeration: number; quality: QualityLevel; autoQuality: boolean; autoRotate: boolean;
  selectedCell: number | null; hoveredCell: number | null; focusCell: number | null; focusSeq: number;
  selectedSpecies: string | null;
  revealed: Uint8Array | null;
  history: SeriesHistory | null; historyTick: number;
  bufferVersion: number;
  /** Latest moment reached in this session: the timeline only scrubs through what already happened. */
  maxTick: number;
  /** Still mode: no time-based animation, for tests, screenshots and reduced motion (principle 8). */
  still: boolean;
  init(config: SourceConfig): Promise<void>;
  setClock(playing: boolean, speed?: number): void;
  seek(tick: number): void;
  runToEraEnd(): void;
  command(c: SourceCommand): void;
  setLayer(l: LayerId | null): void;
  set(partial: Partial<PlanetStore>): void;
  selectCell(cell: number | null): void;
  focusOn(cell: number): void;
  selectSpecies(id: string | null): void;
  refreshHistory(samples?: number): Promise<void>;
}

let source: PlanetStateSource | null = null;
let unsubscribe: (() => void) | null = null;
export const snapshots = new SnapshotBuffer();
export function getSource(): PlanetStateSource {
  if (!source) source = new SyntheticSource();
  return source;
}
/** Replaces the data source (fixtures, and the backend in the future). */
export function setSource(next: PlanetStateSource) {
  unsubscribe?.(); unsubscribe = null; source?.dispose(); source = next;
}

export const usePlanetStore = create<PlanetStore>((set, get) => ({
  status: "idle", errorDetail: null, info: null, config: null, frame: null, playing: false, speed: 12, mode: "normal",
  layer: null, compareTick: null, showClouds: true, exaggeration: 0.07, quality: "medium", autoQuality: true, autoRotate: true,
  selectedCell: null, hoveredCell: null, focusCell: null, focusSeq: 0, selectedSpecies: null, revealed: null,
  history: null, historyTick: -1, bufferVersion: 0, maxTick: 0, still: false,

  async init(config) {
    const src = getSource();
    set({ status: "loading", errorDetail: null, config, frame: null, maxTick: 0, history: null, historyTick: -1, selectedCell: null, selectedSpecies: null, compareTick: null });
    snapshots.clear();
    unsubscribe?.();
    unsubscribe = src.subscribe((m) => {
      if (m.type === "frame") {
        if (snapshots.push(m.frame)) set({ bufferVersion: get().bufferVersion + 1 });
        set({ frame: m.frame, status: "ready", maxTick: Math.max(get().maxTick, m.frame.tick) });
      } else if (m.type === "clock") set({ playing: m.playing, speed: m.speed, mode: m.mode });
      else if (m.type === "error") set({ status: "error", errorDetail: m.detail ?? null });
    });
    try {
      const info = await src.start(config);
      set({ info });
    } catch (e) {
      set({ status: "error", errorDetail: e instanceof Error ? e.message : String(e) });
    }
  },
  setClock(playing, speed) { getSource().setClock(playing, speed ?? get().speed, "normal"); },
  seek(tick) {
    const near = snapshots.nearest(tick);
    if (near && get().playing === false) set({ frame: near }); // instant feedback from the buffer; the exact frame follows
    getSource().seek(tick);
  },
  runToEraEnd() { const f = get().frame; if (f) getSource().runUntil(f.globals.eraEndTick); },
  command(c) { getSource().dispatch(c); },
  setLayer(layer) { set({ layer }); },
  set(partial) { set(partial); },
  selectCell(cell) { set({ selectedCell: cell }); },
  focusOn(cell) { set({ focusCell: cell, focusSeq: get().focusSeq + 1, selectedCell: cell }); },
  selectSpecies(id) { set({ selectedSpecies: id }); getSource().dispatch({ type: "observeLineage", id }); },
  async refreshHistory(samples = 160) {
    const { frame, info } = get();
    if (!frame || !info) return;
    const h = await getSource().getHistory(info.startTick, Math.max(info.startTick + 1, frame.tick), samples);
    set({ history: h, historyTick: frame.tick });
  },
}));
