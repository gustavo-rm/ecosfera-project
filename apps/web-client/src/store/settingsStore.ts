"use client";
import { create } from "zustand";
import type { PaletteSet } from "@/core/appearance/palettes";

export type Role = "student" | "teacher" | "coordinator" | "guardian" | "developer";
export interface Settings {
  theme: "dark" | "light"; contrast: "normal" | "high"; fontScale: 1 | 1.15 | 1.3; palette: PaletteSet;
  motion: "system" | "reduced" | "full"; textMode: boolean; sound: boolean;
  /** Simulated session. There is no real authentication in this task; the route guard is a placeholder. */
  role: Role; devMode: boolean; hydrated: boolean;
  update(p: Partial<Settings>): void;
}
const KEY = "ecosfera.settings.v1";
const defaults = { theme: "dark", contrast: "normal", fontScale: 1, palette: "default", motion: "system", textMode: false, sound: false, role: "student", devMode: process.env.NODE_ENV === "development" } as const;

export const useSettings = create<Settings>((set, get) => ({
  ...defaults, hydrated: false,
  update(p) {
    set(p);
    const { update: _u, hydrated: _h, ...rest } = get();
    try { localStorage.setItem(KEY, JSON.stringify(rest)); } catch { /* storage may be blocked */ }
  },
}));
export function hydrateSettings() {
  if (useSettings.getState().hydrated) return;
  let saved: Partial<Settings> = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) ?? "{}"); } catch { /* ignore */ }
  const q = new URLSearchParams(window.location.search);
  if (q.get("dev") === "1") saved.devMode = true;
  if (q.get("dev") === "0") saved.devMode = false;
  if (q.get("tema")) saved.theme = q.get("tema") as Settings["theme"];
  if (q.get("contraste")) saved.contrast = q.get("contraste") as Settings["contrast"];
  if (q.get("papel")) saved.role = q.get("papel") as Role;
  if (q.get("paleta")) saved.palette = q.get("paleta") as PaletteSet;
  if (q.get("movimento")) saved.motion = q.get("movimento") as Settings["motion"];
  if (q.get("texto")) saved.textMode = q.get("texto") === "1";
  useSettings.setState({ ...saved, hydrated: true });
}
export function prefersReducedMotion(s: Pick<Settings, "motion">): boolean {
  if (s.motion === "reduced") return true;
  if (s.motion === "full") return false;
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
