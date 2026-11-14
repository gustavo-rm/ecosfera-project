"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { evidence } from "@/core/evidence/bus";
import { t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";
import { ErrorState, Loading, Tabs } from "@/ui/kit";
import { ProgressPanel } from "../missions/MissionsScreen";
import { useHistory } from "../session/hooks";
import { StudentSession } from "../session/StudentSession";
import { StudentShell } from "../shell/Menu";
import { PyramidPanel, SeriesPanel, StructurePanel } from "./charts";
import { CyclesPanel, FoodWebPanel, PhylogenyPanel } from "./graphs";

const TABS = [["series", "chart"], ["energy", "pyramid"], ["web", "web"], ["phylogeny", "tree"], ["structure", "dna"], ["cycles", "cycle"], ["progress", "user"]] as const;
/** Scientific dashboards of the student (section 10). Every chart has axes with units, a table view and a text summary. */
export function DataScreen() {
  const q = useSearchParams();
  const [tab, setTab] = useState<string>(q.get("aba") ?? "series");
  const frame = usePlanetStore((s) => s.frame), status = usePlanetStore((s) => s.status), errorDetail = usePlanetStore((s) => s.errorDetail);
  const history = useHistory(200);
  useEffect(() => {
    const g = useGameStore.getState(), tick = usePlanetStore.getState().frame?.tick ?? 0;
    evidence.emit({ type: "chart_opened", chart: tab, ticksSinceLastAction: tick - g.lastActionTick });
    g.patch({ stats: { ...g.stats, chartsOpened: g.stats.chartsOpened + 1, cyclesSeen: g.stats.cyclesSeen || (tab === "web" && !!usePlanetStore.getState().frame?.bio.links.some((l) => l.kind === "cycle")) } });
  }, [tab]);
  return (
    <StudentShell titleKey="data.title" wide>
      <StudentSession />
      <Tabs label={t("data.title")} value={tab} onChange={setTab} className="mb-3" tabs={TABS.map(([id, icon]) => ({ id, label: t(`data.tab.${id}`), icon }))} />
      <div role="tabpanel" aria-label={t(`data.tab.${tab}`)} data-screen="data" data-tab={tab}>
        {status === "error" ? <ErrorState detail={errorDetail} /> : !frame || !history ? <Loading /> : (
          <>
            {tab === "series" && <SeriesPanel h={history} species={frame.bio.species} />}
            {tab === "energy" && <PyramidPanel bio={frame.bio} />}
            {tab === "web" && <FoodWebPanel bio={frame.bio} />}
            {tab === "phylogeny" && <PhylogenyPanel bio={frame.bio} h={history} tick={frame.tick} />}
            {tab === "structure" && <StructurePanel h={history} bio={frame.bio} species={frame.bio.species} />}
            {tab === "cycles" && <CyclesPanel cycles={frame.bio.cycles} />}
            {tab === "progress" && <ProgressPanel />}
          </>
        )}
      </div>
    </StudentShell>
  );
}
