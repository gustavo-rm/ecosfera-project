"use client";
import dynamic from "next/dynamic";
import { useEffect } from "react";
import type { LayerId } from "@/core/appearance/layers";
import type { PaletteSet } from "@/core/appearance/palettes";
import { ARCHETYPE_PRESETS } from "@/core/source/synthetic/scenarios";
import { cameraApi } from "@/render/CameraRig";
import { usePlanetStore, type QualityLevel } from "@/store/planetStore";

const PlanetView = dynamic(() => import("@/render/PlanetView"), { ssr: false });

/**
 * Bare test bench for the planet, driven by URL parameters. Used by the screenshot and performance scripts.
 * Example: /lab/planeta?preset=terra&camada=temperature&still=1
 */
export default function PlanetBench() {
  const status = usePlanetStore((s) => s.status);
  const tick = usePlanetStore((s) => s.frame?.tick);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const preset = q.get("preset") ? ARCHETYPE_PRESETS[q.get("preset")!] : null;
    const store = usePlanetStore.getState();
    store.set({
      still: q.get("still") === "1", layer: (q.get("camada") as LayerId) || null, quality: (q.get("qualidade") as QualityLevel) || "medium",
      autoQuality: q.get("auto") === "1", autoRotate: false, showClouds: q.get("nuvens") !== "0", exaggeration: q.get("exagero") ? Number(q.get("exagero")) : 0.07,
    });
    void store.init({
      scenarioId: preset?.scenarioId ?? q.get("cenario") ?? "genesis", level: Number(q.get("nivel") ?? 5), seed: q.get("semente") ? Number(q.get("semente")) : undefined,
      params: preset?.params, startTick: q.get("tick") ? Number(q.get("tick")) : preset?.tick,
    }).then(() => {
      if (q.get("zoom")) cameraApi.zoom(Number(q.get("zoom")));
      if (q.get("girar")) cameraApi.rotate(Number(q.get("girar")), Number(q.get("inclinar") ?? 0));
      if (q.get("tocar") === "1") usePlanetStore.getState().setClock(true, Number(q.get("velocidade") ?? 12));
    });
  }, []);
  const palette = (typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("paleta") : null) as PaletteSet | null;
  return (
    <main style={{ position: "fixed", inset: 0, background: "#04060d" }} data-status={status} data-tick={tick ?? ""}>
      <PlanetView paletteSet={palette ?? "default"} />
    </main>
  );
}
