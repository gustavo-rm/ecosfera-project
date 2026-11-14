"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { evidence } from "@/core/evidence/bus";
import { t } from "@/i18n";
import { useGameStore, type Notice } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { Button, Ped } from "@/ui/kit";
import { StudentSession } from "../session/StudentSession";
import { MenuDialog } from "../shell/Menu";
import { EraReportDialog, InterventionDialog, RegionDialog, TutorPanel, WhyDialog } from "./dialogs";
import { ActionsPanel, CameraButtons, ComparePanel, LayersPanel, MiniChart, Notices, Onboarding, RegionProbe, TimeBar, TopBar } from "./panels";
import { PlanetStage } from "./stage";

/** Main game screen: the planet in the center, indicators on top, actions left, layers right, time below (GDD §13). */
export function GameScreen() {
  const router = useRouter();
  const [intervention, setIntervention] = useState<string | null>(null);
  const [why, setWhy] = useState<{ open: boolean; eventId: string | null }>({ open: false, eventId: null });
  const [tutor, setTutor] = useState(false);
  const [menu, setMenu] = useState(false);
  const [region, setRegion] = useState<number | null>(null);
  const [report, setReport] = useState<number | null>(null);
  const [sheet, setSheet] = useState<"actions" | "layers" | null>(null);
  const frame = usePlanetStore((s) => s.frame);
  const reportEra = useGameStore((s) => s.reportEra);
  const collapsed = useGameStore((s) => s.collapsed);
  const textMode = useSettings((s) => s.textMode);
  const onNotice = (n: Notice) => {
    const a = n.action!;
    if (a.type === "focus" && typeof a.ref === "number") usePlanetStore.getState().focusOn(a.ref);
    else if (a.type === "species") router.push(`/jogo/codex?especie=${a.ref}`);
    else if (a.type === "report") setReport(reportEra);
    else if (a.type === "why") setWhy({ open: true, eventId: typeof a.ref === "string" ? a.ref : null });
    else if (a.type === "prediction") router.push("/jogo/missoes?aba=previsoes");
    else if (a.type === "tutor") setTutor(true);
    useGameStore.getState().dismiss(n.id);
  };
  const noLife = frame && frame.bio.richness === 0 && frame.globals.era >= 4;
  const eraEnd = frame && frame.tick >= frame.globals.eraEndTick - 1;
  return (
    <div className="fixed inset-0 overflow-hidden bg-[#04060d]" data-screen="game">
      <StudentSession />
      <main id="conteudo" className="absolute inset-0"><h1 className="ec-sr-only">{t("game.title")}</h1><PlanetStage /></main>
      <div className="pointer-events-none absolute inset-0 flex flex-col">
        <TopBar onMenu={() => setMenu(true)} />
        <div className="relative flex min-h-0 flex-1 gap-2 p-2">
          <div className={`${sheet === "actions" ? "flex" : "hidden"} w-[250px] max-w-[80vw] flex-col gap-2 md:flex`}><ActionsPanel onPick={setIntervention} /></div>
          <div className="flex min-w-0 flex-1 flex-col items-center justify-between gap-2">
            <div className="flex w-full flex-col items-center gap-2">
              <Notices onAction={onNotice} />
              {(noLife || collapsed) && <div className="ec-panel pointer-events-auto flex flex-wrap items-center gap-2 px-3 py-1.5" role="status" data-no-life><Icon name="info" /><Ped k={collapsed ? "ped.state.collapsed" : "ped.state.noLife"} /><Button onClick={() => setWhy({ open: true, eventId: null })}>{t("why.ask")}</Button></div>}
              {eraEnd && <div className="ec-panel pointer-events-auto flex flex-wrap items-center gap-2 px-3 py-1.5" role="status" data-era-end><Icon name="flag" /><span>{t("game.eraEnd")}</span><Button onClick={() => setReport(frame!.globals.era)}>{t("notice.action.report")}</Button></div>}
            </div>
            <div className="flex w-full items-end justify-between gap-2">
              <div className="flex flex-col gap-2" hidden={textMode}><ComparePanel /><div className="hidden md:block"><MiniChart /></div></div>
              <Onboarding />
              <div className="flex flex-col items-end gap-2" hidden={textMode}><RegionProbe onRegion={(c) => { evidence.emit({ type: "panel_opened", panel: "region", ticksSinceLastAction: (frame?.tick ?? 0) - useGameStore.getState().lastActionTick }); setRegion(c); }} /><CameraButtons /></div>
            </div>
          </div>
          <div className={`${sheet === "layers" ? "flex" : "hidden"} w-[236px] max-w-[80vw] flex-col gap-2 md:flex`}><LayersPanel /></div>
          {tutor && <div className="absolute bottom-2 right-2 top-2 z-10 flex"><TutorPanel open onClose={() => setTutor(false)} /></div>}
        </div>
        <div className="pointer-events-auto flex gap-1 px-2 pb-1 md:hidden" role="group" aria-label={t("hud.panels")}>
          <Button className="flex-1" icon="bolt" aria-pressed={sheet === "actions"} onClick={() => setSheet(sheet === "actions" ? null : "actions")}>{t("hud.actionsShort")}</Button>
          <Button className="flex-1" icon="layers" aria-pressed={sheet === "layers"} onClick={() => setSheet(sheet === "layers" ? null : "layers")}>{t("hud.layers")}</Button>
        </div>
        <TimeBar onTutor={() => { if (!tutor) evidence.emit({ type: "panel_opened", panel: "tutor", ticksSinceLastAction: (frame?.tick ?? 0) - useGameStore.getState().lastActionTick }); setTutor(!tutor); }} onMissions={() => router.push("/jogo/missoes")} />
      </div>
      <InterventionDialog key={intervention ?? "none"} id={intervention} onClose={() => setIntervention(null)} />
      <WhyDialog open={why.open} eventId={why.eventId} onClose={() => setWhy({ open: false, eventId: null })} />
      <RegionDialog cell={region} onClose={() => setRegion(null)} />
      <EraReportDialog era={report} onClose={() => { setReport(null); useGameStore.getState().patch({ reportEra: null }); }} />
      <MenuDialog open={menu} onClose={() => setMenu(false)} />
    </div>
  );
}
