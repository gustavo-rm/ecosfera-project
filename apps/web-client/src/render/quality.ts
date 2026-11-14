import type { QualityLevel } from "@/store/planetStore";

export interface QualitySettings { renderOffset: -1 | 0 | 1; dprMax: number; octaves: number; stars: number; organisms: number; antialias: boolean; frameRate: number }
/** Quality tiers (ADR 0003). "low" is the target for a weak Chromebook. */
export const QUALITY: Record<QualityLevel, QualitySettings> = {
  low: { renderOffset: -1, dprMax: 1, octaves: 2, stars: 400, organisms: 0, antialias: false, frameRate: 3 },
  medium: { renderOffset: 0, dprMax: 1.25, octaves: 3, stars: 1200, organisms: 500, antialias: true, frameRate: 5 },
  high: { renderOffset: 1, dprMax: 2, octaves: 5, stars: 2500, organisms: 1400, antialias: true, frameRate: 8 },
};
export const QUALITY_ORDER: QualityLevel[] = ["low", "medium", "high"];

/** Live numbers for the lab performance panel. Mutated in place by the render loop (no React state per frame). */
export const perfStats = { frameMs: 16.7, fps: 60, worstMs: 0, drawCalls: 0, triangles: 0, geometries: 0, textures: 0, programs: 0, dpr: 1, attributeBytes: 0, uploadsPerSecond: 0, frames: 0 };
/** Shared per-frame values in planet-local space, written by PlanetBody and read by other render components. */
export const runtime = { time: 0, zoom: 0, sunWorld: [0.93, 0.12, 0.34] as [number, number, number], cameraDistance: 3.9, lastInput: 0 };
