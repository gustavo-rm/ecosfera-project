"use client";
import { useEffect, useMemo } from "react";
import type { PlanetFrame } from "@/core/state/types";
import { prefersReducedMotion, useSettings } from "@/store/settingsStore";
import { snapshots, usePlanetStore } from "@/store/planetStore";

export function useReducedMotion(): boolean {
  const motion = useSettings((s) => s.motion);
  return useMemo(() => prefersReducedMotion({ motion }), [motion]);
}
/** Keeps the dashboard history fresh while a consumer is mounted. */
export function useHistory(samples = 160) {
  const history = usePlanetStore((s) => s.history);
  const tick = usePlanetStore((s) => s.frame?.tick ?? -1);
  const historyTick = usePlanetStore((s) => s.historyTick);
  const status = usePlanetStore((s) => s.status);
  useEffect(() => {
    if (status === "ready" && tick >= 0 && (historyTick < 0 || Math.abs(tick - historyTick) >= 60)) void usePlanetStore.getState().refreshHistory(samples);
  }, [tick, historyTick, status, samples]);
  return history;
}
/** A stored snapshot about `ticksAgo` before the current frame, for trends and "before" values. */
export function usePastFrame(ticksAgo = 240): PlanetFrame | null {
  const tick = usePlanetStore((s) => s.frame?.tick ?? 0);
  const version = usePlanetStore((s) => s.bufferVersion);
  const bucket = Math.floor(tick / 30);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => snapshots.bracket(tick - ticksAgo).before ?? snapshots.bracket(tick - 1).before, [bucket, version, ticksAgo]);
}
export const yearsLabel = (ticks: number) => Math.floor(ticks / 12);
