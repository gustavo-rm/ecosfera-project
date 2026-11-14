"use client";
import { useEffect, useRef } from "react";
import { describeChange } from "@/core/a11y/describe";
import { useGameStore, syncReveal } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { useSettings } from "@/store/settingsStore";
import { announce } from "@/ui/kit";
import { QUALITY } from "@/render/quality";
import { getSource } from "@/store/planetStore";
import { SyntheticSource } from "@/core/source/SyntheticSource";

/**
 * Boots the student's session: restores the local game, starts the default planet on first use, connects the game
 * rules and the screen-reader announcements to the stream of frames. Renders nothing.
 */
export function StudentSession({ autoStart = true, passive = false }: { autoStart?: boolean; passive?: boolean }) {
  const hydrated = useGameStore((s) => s.hydrated);
  const started = useGameStore((s) => s.started);
  const settingsReady = useSettings((s) => s.hydrated);
  const booted = useRef(false);
  useEffect(() => { void useGameStore.getState().resume(); }, []);
  useEffect(() => {
    if (!hydrated || !settingsReady || booted.current) return;
    booted.current = true;
    const q = new URLSearchParams(window.location.search);
    if (q.get("still") === "1") usePlanetStore.getState().set({ still: true, autoRotate: false, autoQuality: false });
    const scenario = q.get("cenario"), g = useGameStore.getState(), planet = usePlanetStore.getState();
    if (scenario || (!started && autoStart)) {
      void g.start(scenario ?? "genesis", {}, q.get("semente") ? Number(q.get("semente")) : undefined).then(() => {
        if (q.get("tick")) { usePlanetStore.getState().seek(Number(q.get("tick"))); useGameStore.getState().patch({ onboarding: -1 }); }
        if (q.get("camada")) usePlanetStore.getState().setLayer(q.get("camada") as never);
      });
    } else if (started && (planet.status === "idle" || planet.config?.scenarioId !== g.scenarioId || planet.config?.level !== 5)) {
      // Continue the planet saved in this browser: same scenario and seed, the same interventions replayed, same moment.
      void planet.init({ scenarioId: g.scenarioId, level: 5, seed: g.seed, params: g.params }).then(() => {
        const st = usePlanetStore.getState();
        for (const c of g.commands) { st.seek(c.tick); st.command(c.command); }
        st.seek(g.savedTick);
      });
    }
  }, [hydrated, settingsReady, started, autoStart]);
  useEffect(() => {
    let last = 0;
    return usePlanetStore.subscribe((s, p) => {
      if (s.quality !== p.quality) { const src = getSource(); if (src instanceof SyntheticSource) src.frameRate = QUALITY[s.quality].frameRate; }
      if (s.layer !== p.layer) syncReveal();
      if (s.frame === p.frame || !s.frame) return;
      if (!passive) useGameStore.getState().onFrame(s.frame, p.frame);
      const msg = describeChange(p.frame, s.frame);
      if (msg && performance.now() - last > 1500) { last = performance.now(); announce(msg); }
    });
  }, [passive]);
  return null;
}
