"use client";
import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { Group } from "three";
import type { PaletteSet } from "@/core/appearance/palettes";
import { usePlanetStore, type QualityLevel } from "@/store/planetStore";
import { CameraRig } from "./CameraRig";
import { EventFx } from "./EventFx";
import { Organisms } from "./Organisms";
import { PlanetBody } from "./PlanetBody";
import { perfStats, QUALITY, QUALITY_ORDER } from "./quality";
import { Sky } from "./Sky";

/** Measures frame time and lowers resolution, then quality, when the device cannot keep 30 FPS (RNF-001, RF-057). */
function PerfGovernor() {
  const s = useRef({ ema: 16.7, slow: 0, fast: 0 });
  useFrame((_, dt) => {
    const st = s.current, ms = dt * 1000;
    st.ema += (ms - st.ema) * 0.05;
    perfStats.frameMs = st.ema; perfStats.fps = 1000 / st.ema; perfStats.worstMs = Math.max(perfStats.worstMs * 0.995, ms); perfStats.frames++;
    const store = usePlanetStore.getState();
    if (!store.autoQuality || store.still) return;
    st.slow = st.ema > 36 ? st.slow + dt : 0; st.fast = st.ema < 19 ? st.fast + dt : 0;
    const scale = store.resolutionScale;
    if (st.slow > 2) {
      st.slow = 0;
      if (scale > 0.55) store.set({ resolutionScale: Math.max(0.5, scale * 0.8) });
      else { const i = QUALITY_ORDER.indexOf(store.quality); if (i > 0) store.set({ quality: QUALITY_ORDER[i - 1], resolutionScale: 1 }); }
    } else if (st.fast > 6 && scale < 1) { st.fast = 0; store.set({ resolutionScale: Math.min(1, scale * 1.15) }); }
  });
  return null;
}

function Scene({ quality, paletteSet, reducedMotion, interactive }: { quality: QualityLevel; paletteSet: PaletteSet; reducedMotion: boolean; interactive: boolean }) {
  const planet = useRef<Group>(null);
  const q = QUALITY[quality];
  return (
    <>
      <PerfGovernor />
      <CameraRig planet={planet} interactive={interactive} />
      <Sky stars={q.stars} />
      <PlanetBody planetRef={planet} renderOffset={q.renderOffset} octaves={q.octaves} paletteSet={paletteSet} reducedMotion={reducedMotion}>
        <Organisms budget={q.organisms} />
        <EventFx reducedMotion={reducedMotion} />
      </PlanetBody>
    </>
  );
}

export interface PlanetViewProps { paletteSet?: PaletteSet; reducedMotion?: boolean; interactive?: boolean; className?: string }
/** The 3D planet. It reads the store by subscription; React does not re-render per frame. */
export default function PlanetView({ paletteSet = "default", reducedMotion = false, interactive = true, className }: PlanetViewProps) {
  const quality = usePlanetStore((s) => s.quality);
  const scale = usePlanetStore((s) => s.resolutionScale);
  // The resolution goes through the Canvas `dpr` prop: R3F re-applies that prop on every render, so it is the one place to set it.
  const dpr = Math.min(typeof window === "undefined" ? 1 : window.devicePixelRatio, QUALITY[quality].dprMax) * scale;
  useEffect(() => { perfStats.dpr = dpr; }, [dpr]);
  return (
    <Canvas
      key={quality} className={className} flat dpr={dpr} camera={{ fov: 35, near: 0.1, far: 300, position: [0, 0, 5] }}
      gl={{ antialias: QUALITY[quality].antialias, powerPreference: "high-performance", alpha: false, preserveDrawingBuffer: false }}
      onCreated={({ gl }) => { gl.setClearColor("#04060d"); }} aria-hidden="true"
    >
      <Scene quality={quality} paletteSet={paletteSet} reducedMotion={reducedMotion} interactive={interactive} />
    </Canvas>
  );
}
