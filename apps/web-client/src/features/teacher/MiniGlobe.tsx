"use client";
import { useEffect, useRef, useState } from "react";
import { computeAppearance, createAppearance } from "@/core/appearance/appearance";
import { getMesh, nearestCell } from "@/core/mesh/geodesic";
import { SyntheticEngine } from "@/core/source/synthetic/engine";
import type { PlanetFrame } from "@/core/state/types";
import { fmt, t } from "@/i18n";

/**
 * Thumbnail of a planet: an orthographic view of the sphere drawn on a 2D canvas from the same state -> appearance
 * mapping the 3D renderer uses (level 3 mesh). It lets several planets sit side by side without one WebGL context each.
 */
export function MiniGlobe({ scenarioId, seed, tick, size = 180, label }: { scenarioId: string; seed: number; tick: number; size?: number; label: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [frame, setFrame] = useState<PlanetFrame | null>(null);
  useEffect(() => {
    const id = setTimeout(() => {
      const f = new SyntheticEngine({ scenarioId, level: 3, seed }).frameAt(tick), mesh = getMesh(3);
      const app = computeAppearance(f, mesh, { layer: null, revealed: null, showHabitat: false }, createAppearance(mesh.count)), u = app.uniforms;
      const cv = ref.current; if (!cv) return;
      const ctx = cv.getContext("2d")!, img = ctx.createImageData(size, size), R = size / 2 - 3, sun = [0.55, 0.35, 0.76];
      for (let py = 0; py < size; py++) for (let px = 0; px < size; px++) {
        const x = (px - size / 2) / R, y = -(py - size / 2) / R, r2 = x * x + y * y, o = (py * size + px) * 4;
        if (r2 > 1) { img.data[o + 3] = 0; continue; }
        const z = Math.sqrt(1 - r2), c = nearestCell(mesh, x, y, z) * 4, land = app.A[c] > 0, ice = app.A[c + 1] > 0.5, cloud = app.A[c + 3];
        let col = land ? [app.B[c], app.B[c + 1], app.B[c + 2]] : u.oceanShallow.map((v, i) => v * 0.6 + u.oceanDeep[i] * 0.4);
        if (ice) col = [0.93, 0.96, 1]; if (u.surfaceHeat > 0.3) col = [0.9, 0.35, 0.08];
        const lit = Math.max(0.12, x * sun[0] + y * sun[1] + z * sun[2]), k = Math.min(1, cloud * u.cloudOpacity * 0.8), rim = Math.pow(1 - z, 2.5) * u.atmoDensity;
        for (let i = 0; i < 3; i++) { let v = (col[i] * (1 - k) + u.cloudColor[i] * k) * lit * 1.25; v = v * (1 - rim) + u.skyColor[i] * rim; img.data[o + i] = Math.min(255, v * 255); }
        img.data[o + 3] = 255;
      }
      ctx.putImageData(img, 0, 0); setFrame(f);
    }, 0);
    return () => clearTimeout(id);
  }, [scenarioId, seed, tick, size]);
  const g = frame?.globals;
  return (
    <figure className="flex flex-col items-center gap-1">
      <canvas ref={ref} width={size} height={size} role="img" aria-label={g ? t("teacher.compare.globeAlt", { label, archetype: t(`archetype.${g.archetype}`), temp: fmt(Math.min(g.meanTempC, 9999), 0), richness: frame!.bio.richness }) : label} className="rounded-full bg-[#04060d]" />
      {g && <figcaption className="ec-num text-center text-[length:var(--ec-text-xs)]">{t(`era.${g.era}.name`)} · {fmt(Math.min(g.meanTempC, 9999), 0)} °C · {frame!.bio.richness} {t("teacher.compare.lineages")}</figcaption>}
    </figure>
  );
}
