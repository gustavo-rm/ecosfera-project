"use client";
import { useState } from "react";
import { LAYERS } from "@/core/appearance/layers";
import { INTERVENTIONS, RESEARCH, type ResearchNode } from "@/game/catalog";
import { fmt, t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { Icon } from "@/ui/icons";
import { announce, Button, Chip, Meter, Ped, Tabs } from "@/ui/kit";
import { StudentSession } from "../session/StudentSession";
import { StudentShell } from "../shell/Menu";

function NodeCard({ node }: { node: ResearchNode }) {
  const unlocked = useGameStore((s) => s.unlocked), stats = useGameStore((s) => s.stats), points = useGameStore((s) => s.resources.research);
  const has = unlocked.includes(node.id), missing = node.requires.filter((r) => !unlocked.includes(r)), mastery = node.mastery(stats);
  const ready = !has && missing.length === 0 && mastery >= 1, enough = points >= node.cost;
  const enables = [...RESEARCH.filter((r) => r.requires.includes(node.id)).map((r) => t(`research.${r.id}.name`)), ...INTERVENTIONS.filter((i) => i.requires === node.id).map((i) => t(`intervention.${i.id}.name`)), ...LAYERS.filter((l) => l.requires === node.id).map((l) => t(`layer.${l.id}.name`))];
  return (
    <li className="ec-card flex flex-col gap-2" style={{ gridColumn: node.column + 1, gridRow: node.row + 1, borderColor: has ? "var(--ec-success)" : ready ? "var(--ec-accent)" : undefined }} data-node={node.id} data-state={has ? "unlocked" : ready ? "ready" : "locked"}>
      <div className="flex items-start justify-between gap-2"><h3 className="!text-[length:var(--ec-text-md)]">{t(`research.${node.id}.name`)}</h3><Chip tone={has ? "success" : ready ? "warning" : undefined} icon={has ? "check" : ready ? "spark" : "lock"}>{has ? t("research.unlocked") : ready ? t("research.ready") : t("research.locked")}</Chip></div>
      <Ped as="p" k={`ped.research.${node.id}.desc`} className="text-[length:var(--ec-text-sm)]" />
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("research.era", { n: node.era })}{enables.length > 0 && ` · ${t("research.enables", { list: enables.join(", ") })}`}</p>
      {!has && <>
        {missing.length > 0 && <p className="text-[length:var(--ec-text-sm)]"><Icon name="lock" size={14} className="mr-1 inline" />{t("research.needs", { list: missing.map((m) => t(`research.${m}.name`)).join(", ") })}</p>}
        <div><p className="text-[length:var(--ec-text-xs)]">{t("research.mastery")}: <span className="ec-num">{fmt(mastery * 100)}%</span></p><Meter value={mastery} label={t("research.mastery")} /></div>
        <Button variant={ready && enough ? "primary" : "default"} icon="flask" disabled={!ready || !enough} onClick={() => { if (useGameStore.getState().unlock(node.id)) announce(`${t("research.unlocked")}: ${t(`research.${node.id}.name`)}`); }} data-unlock={node.id}>
          {t("research.unlock")} · <span className="ec-num">{node.cost}</span>{ready && !enough && <span className="ec-sr-only">, {t("research.noPoints")}</span>}
        </Button>
      </>}
    </li>
  );
}

/** Scientific tree (understanding) and technological tree (capabilities). Unlocking needs mastery shown in play. */
export function ResearchScreen() {
  const [tree, setTree] = useState<"science" | "tech">("science");
  const points = useGameStore((s) => s.resources.research);
  const nodes = RESEARCH.filter((r) => r.tree === tree);
  return (
    <StudentShell titleKey="research.title" wide>
      <StudentSession />
      <div className="mb-3 flex flex-wrap items-center gap-3" data-screen="research">
        <Tabs label={t("research.title")} value={tree} onChange={(v) => setTree(v as "science")} tabs={[{ id: "science", label: t("research.tree.science"), icon: "microscope" }, { id: "tech", label: t("research.tree.tech"), icon: "settings" }]} />
        <Chip icon="flask">{t("research.points", { n: fmt(points) })}</Chip>
      </div>
      <p className="ec-muted mb-3 text-[length:var(--ec-text-sm)]">{t("research.masteryHint")}</p>
      <div className="ec-scroll pb-2"><ul className="grid items-start gap-2 max-lg:!flex max-lg:flex-col" role="tabpanel" aria-label={t(`research.tree.${tree}`)} style={{ gridTemplateColumns: `repeat(${Math.max(...nodes.map((n) => n.column)) + 1}, minmax(210px, 1fr))` }}>{nodes.map((n) => <NodeCard key={n.id} node={n} />)}</ul></div>
    </StudentShell>
  );
}
