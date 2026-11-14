"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { BiosphereFrame, CycleDiagram, SeriesHistory, SpeciesRecord } from "@/core/state/types";
import { fmt, t } from "@/i18n";
import { useGameStore } from "@/store/gameStore";
import { Icon } from "@/ui/icons";
import { ChartFrame, Chip, DataTable, Empty, Ped, Slider, Tabs } from "@/ui/kit";
import { useSeriesColors } from "./charts";

const year = (tick: number) => Math.floor(tick / 12);
const ROLE_SHAPE: Record<string, string> = { phototroph: "leaf", chemotroph: "volcanism", nitrogenFixer: "wind", decomposer: "cycle", detritivore: "bone", herbivore: "footprint", mixotroph: "spark", carnivore: "target" };

/** Food web: lineages by trophic level, energy flows as arrows, cyclic (rock-paper-scissors) relations dashed and named. */
export function FoodWebPanel({ bio }: { bio: BiosphereFrame }) {
  const colors = useSeriesColors();
  const [focus, setFocus] = useState<string | null>(null);
  const living = bio.species.filter((s) => s.alive);
  const layout = useMemo(() => {
    const levels = Math.max(1, bio.trophicLevels), W = 900, H = 90 + levels * 110, pos = new Map<string, { x: number; y: number }>();
    for (let l = 0; l < levels; l++) { const row = living.filter((s) => s.trophicLevel === l); row.forEach((s, i) => pos.set(s.id, { x: ((i + 1) / (row.length + 1)) * W, y: H - 60 - l * 110 })); }
    return { W, H, pos, levels };
  }, [bio.trophicLevels, living]);
  if (living.length === 0) return <Empty icon="web" title={t("data.noLife")} hint={t("data.noLifeHint")} />;
  const name = (id: string) => bio.species.find((s) => s.id === id)?.name ?? id;
  const cycles = bio.links.filter((l) => l.kind === "cycle"), trophic = bio.links.filter((l) => l.kind === "trophic");
  const maxFlux = Math.max(...trophic.map((l) => l.flux), 0.001);
  const summary = t("data.web.summary", { n: living.length, links: trophic.length, levels: bio.trophicLevels, connectance: fmt(bio.connectance, 2), cycles: cycles.length });
  return (
    <ChartFrame title={t("data.web.title")} summary={summary}
      table={<DataTable caption={t("data.web.title")} rows={bio.links} rowKey={(l, i) => `${l.from}-${l.to}-${i}`} columns={[{ key: "f", header: t("data.web.from"), render: (l) => name(l.from) }, { key: "t", header: t("data.web.to"), render: (l) => name(l.to) }, { key: "k", header: t("data.web.kind"), render: (l) => t(`data.web.kind.${l.kind}`) }, { key: "x", header: t("data.web.flux"), numeric: true, render: (l) => fmt(l.flux, 3) }]} />}>
      <ul className="mb-2 flex flex-wrap gap-4 text-[length:var(--ec-text-sm)]" aria-label={t("legend.title")}>
        <li className="flex items-center gap-1.5"><svg width="30" height="10" aria-hidden="true"><line x1="0" y1="5" x2="30" y2="5" stroke={colors[0]} strokeWidth="3" /></svg>{t("data.web.kind.trophic")}</li>
        <li className="flex items-center gap-1.5"><svg width="30" height="10" aria-hidden="true"><line x1="0" y1="5" x2="30" y2="5" stroke={colors[1]} strokeWidth="3" strokeDasharray="5 4" /></svg>{t("data.web.kind.cycle")}</li>
      </ul>
      <div className="ec-scroll"><div className="relative mx-auto" style={{ width: layout.W, height: layout.H }} data-foodweb>
        <svg width={layout.W} height={layout.H} className="absolute inset-0" aria-hidden="true">
          <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--ec-text-muted)" /></marker></defs>
          {Array.from({ length: layout.levels }, (_, l) => <g key={l}><line x1={0} x2={layout.W} y1={layout.H - 60 - l * 110 + 34} y2={layout.H - 60 - l * 110 + 34} stroke="var(--ec-chart-grid)" strokeOpacity={0.5} /><text x={4} y={layout.H - 60 - l * 110 + 30} fontSize={11} fill="var(--ec-text-muted)">{t(`data.pyramid.level.${Math.min(l, 3)}`)}</text></g>)}
          {bio.links.map((l, i) => { const a = layout.pos.get(l.from), b = layout.pos.get(l.to); if (!a || !b) return null; const on = !focus || l.from === focus || l.to === focus; const cyc = l.kind === "cycle";
            return <path key={i} d={cyc ? `M${a.x} ${a.y - 20}Q${(a.x + b.x) / 2} ${a.y - 70} ${b.x} ${b.y - 20}` : `M${a.x} ${a.y - 18}L${b.x} ${b.y + 20}`} fill="none" stroke={cyc ? colors[1] : colors[0]} strokeWidth={cyc ? 2.5 : 1 + (l.flux / maxFlux) * 4} strokeDasharray={cyc ? "6 5" : undefined} strokeOpacity={on ? 0.9 : 0.12} markerEnd="url(#arrow)" />; })}
        </svg>
        {living.map((s) => { const p = layout.pos.get(s.id)!; return (
          <button key={s.id} type="button" className="ec-btn absolute h-auto min-h-[36px] -translate-x-1/2 -translate-y-1/2 gap-1 px-2 py-0.5 text-[length:var(--ec-text-xs)]" style={{ left: p.x, top: p.y, maxWidth: 130 }} aria-pressed={focus === s.id} onClick={() => setFocus(focus === s.id ? null : s.id)} title={`${s.name} · ${t(`role.${s.role}`)}`}>
            <Icon name={ROLE_SHAPE[s.role]} size={14} /><span className="truncate">{s.name}</span>
          </button>); })}
      </div></div>
      {focus && <p className="mt-2 flex flex-wrap items-center gap-2" aria-live="polite"><strong>{name(focus)}</strong> · {t("codex.eats")}: {bio.species.find((s) => s.id === focus)!.preyIds.filter((id) => living.some((x) => x.id === id)).map(name).join(", ") || t("codex.nothing")} · {t("codex.eatenBy")}: {living.filter((x) => x.preyIds.includes(focus)).map((x) => x.name).join(", ") || t("codex.nothing")} <Link className="ec-link" href={`/jogo/codex?especie=${focus}`}>{t("data.web.openSheet")}</Link></p>}
      {cycles.length > 0 ? <div className="mt-3 flex items-start gap-2" data-cycles><Chip tone="info" icon="cycle">{t("data.web.cycleFound", { list: cycles.map((c) => `${name(c.from)} → ${name(c.to)}`).join(", ") })}</Chip></div> : null}
      <Ped as="p" k="ped.data.cycles" className="ec-muted mt-2 text-[length:var(--ec-text-sm)]" />
    </ChartFrame>
  );
}

const MODE_LETTER: Record<string, string> = { ancestral: "•", allopatric: "A", parapatric: "P", sympatric: "S", introduced: "I" };
/** Phylogenetic tree over time: extinct lineages marked, speciation events dated with their mode, mass extinction bands. */
export function PhylogenyPanel({ bio, h, tick }: { bio: BiosphereFrame; h: SeriesHistory; tick: number }) {
  const colors = useSeriesColors();
  const codex = useGameStore((s) => s.codex);
  const [zoom, setZoom] = useState(1);
  const tree = useMemo(() => {
    const kids = new Map<string | null, SpeciesRecord[]>();
    for (const s of bio.species) { const k = s.parentId && bio.species.some((x) => x.id === s.parentId) ? s.parentId : null; kids.set(k, [...(kids.get(k) ?? []), s]); }
    const order: SpeciesRecord[] = [];
    const walk = (id: string | null) => { for (const s of (kids.get(id) ?? []).sort((a, b) => a.originTick - b.originTick)) { order.push(s); walk(s.id); } };
    walk(null);
    return order;
  }, [bio.species]);
  if (tree.length === 0) return <Empty icon="tree" title={t("data.noLife")} hint={t("data.noLifeHint")} />;
  const t0 = Math.min(...tree.map((s) => s.originTick), h.ticks[0] ?? 0), t1 = Math.max(tick, t0 + 1), W = 860 * zoom, row = 26, L = 150, H = tree.length * row + 46;
  const x = (tk: number) => L + ((tk - t0) / (t1 - t0)) * (W - L - 20), y = (i: number) => 30 + i * row, idx = new Map(tree.map((s, i) => [s.id, i]));
  const impacts = h.marks.filter((m) => m.kind === "event" && m.labelKey.includes("impact"));
  const asexual = tree.filter((s) => s.asexual).length, extinct = tree.filter((s) => s.extinctTick !== null).length;
  const summary = t("data.phylo.summary", { n: tree.length, extinct, alive: tree.length - extinct, modes: (["allopatric", "parapatric", "sympatric"] as const).map((m) => `${t(`speciation.${m}`)}: ${tree.filter((s) => s.speciationMode === m).length}`).join("; ") });
  return (
    <ChartFrame title={t("data.phylo.title")} summary={summary} actions={<div className="w-[200px]"><Slider label={t("data.phylo.zoom")} value={zoom} min={1} max={4} step={0.5} onChange={setZoom} format={(v) => `${fmt(v, 1)}×`} /></div>}
      table={<DataTable caption={t("data.phylo.title")} rows={tree} rowKey={(s) => s.id} columns={[{ key: "n", header: t("codex.name"), render: (s) => <Link className="ec-link" href={`/jogo/codex?especie=${s.id}`}>{s.name}</Link> }, { key: "p", header: t("data.phylo.parent"), render: (s) => (s.parentId ? bio.species.find((x) => x.id === s.parentId)?.name ?? "—" : "—") }, { key: "m", header: t("data.phylo.mode"), render: (s) => t(`speciation.${s.speciationMode}`) }, { key: "o", header: t("codex.origin"), numeric: true, render: (s) => fmt(year(s.originTick)) }, { key: "e", header: t("codex.extinction"), numeric: true, render: (s) => (s.extinctTick !== null ? fmt(year(s.extinctTick)) : "—") }]} />}>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[length:var(--ec-text-sm)]" aria-label={t("legend.title")}>
        {(["allopatric", "parapatric", "sympatric"] as const).map((m) => <li key={m}><span className="ec-kbd">{MODE_LETTER[m]}</span> {t(`speciation.${m}`)}</li>)}
        <li className="flex items-center gap-1"><Icon name="close" size={14} style={{ color: "var(--ec-danger)" }} />{t("codex.extinct")}</li>
        <li className="flex items-center gap-1"><span aria-hidden="true" className="inline-block h-3 w-5 border border-ec-border" style={{ background: "var(--ec-danger)", opacity: 0.25 }} />{t("data.phylo.massBand")}</li>
        <li className="flex items-center gap-1"><span aria-hidden="true" className="inline-block h-3 w-5 border border-ec-border" style={{ background: "var(--ec-success)", opacity: 0.25 }} />{t("data.phylo.radiationBand")}</li>
      </ul>
      <div className="ec-scroll" tabIndex={0} role="region" aria-label={t("data.phylo.title")}>
        <svg width={W} height={H} data-phylogeny>
          {impacts.map((m, i) => <g key={i}><rect x={x(m.tick)} y={12} width={Math.max(6, x(m.tick + 300) - x(m.tick))} height={H - 28} fill="var(--ec-danger)" opacity={0.16} /><rect x={x(m.tick + 300)} y={12} width={Math.max(6, x(Math.min(t1, m.tick + 2400)) - x(m.tick + 300))} height={H - 28} fill="var(--ec-success)" opacity={0.12} /></g>)}
          {Array.from({ length: 6 }, (_, i) => { const tk = t0 + ((t1 - t0) * i) / 5; return <g key={i}><line x1={x(tk)} x2={x(tk)} y1={14} y2={H - 16} stroke="var(--ec-chart-grid)" strokeOpacity={0.5} /><text x={x(tk)} y={H - 3} fontSize={10} textAnchor="middle" fill="var(--ec-text-muted)">{t("hud.year", { year: fmt(year(tk)) })}</text></g>; })}
          {tree.map((s, i) => { const end = s.extinctTick ?? t1, pi = s.parentId ? idx.get(s.parentId) : undefined, seen = codex.includes(s.id);
            return (
              <g key={s.id}>
                {pi !== undefined && <line x1={x(s.originTick)} x2={x(s.originTick)} y1={y(pi)} y2={y(i)} stroke="var(--ec-text-muted)" strokeDasharray="2 3" />}
                <line x1={x(s.originTick)} x2={x(end)} y1={y(i)} y2={y(i)} stroke={s.extinctTick !== null ? "var(--ec-text-muted)" : colors[0]} strokeWidth={s.extinctTick !== null ? 2 : 3.5} strokeLinecap="round" />
                {s.extinctTick !== null && <path d={`M${x(end) - 5} ${y(i) - 5}L${x(end) + 5} ${y(i) + 5}M${x(end) + 5} ${y(i) - 5}L${x(end) - 5} ${y(i) + 5}`} stroke="var(--ec-danger)" strokeWidth={2} />}
                {s.parentId && <g><circle cx={x(s.originTick)} cy={y(i)} r={8} fill="var(--ec-surface)" stroke="var(--ec-text)" /><text x={x(s.originTick)} y={y(i) + 3.5} fontSize={9.5} fontWeight={700} textAnchor="middle" fill="var(--ec-text)">{MODE_LETTER[s.speciationMode]}</text></g>}
                <a href={`/jogo/codex?especie=${s.id}`}><text x={Math.max(4, x(s.originTick) - 14)} y={y(i) + 4} fontSize={11} textAnchor="end" fill="var(--ec-text)" textDecoration="underline">{seen ? s.name : `${t("codex.undiscovered")} (${t(`role.${s.role}`)})`}{s.founderEffect ? " ⚑" : ""}</text></a>
              </g>); })}
        </svg>
      </div>
      {asexual > 0 && <div className="ec-card mt-3 flex items-start gap-2" role="note" data-asexual-note><Icon name="info" style={{ color: "var(--ec-info)" }} /><Ped k="ped.data.asexual" params={{ n: asexual }} /></div>}
    </ChartFrame>
  );
}

const LAYOUT: Record<string, [number, number]> = { atmosphere: [330, 50], biomass: [600, 180], biomassO: [600, 180], organic: [470, 320], ocean: [70, 180], rock: [200, 320], soil: [200, 320], ice: [200, 320], land: [600, 180] };
/** Biogeochemical cycles as stocks and flows, fed by the same state that draws the planet. */
export function CyclesPanel({ cycles }: { cycles: CycleDiagram[] }) {
  const colors = useSeriesColors();
  const [el, setEl] = useState<CycleDiagram["element"]>("carbon");
  const c = cycles.find((x) => x.element === el) ?? cycles[0];
  if (!c) return <Empty title={t("state.empty")} />;
  const ids = [...new Set([...c.stocks.map((s) => s.id), ...c.fluxes.flatMap((f) => [f.from, f.to])])];
  const maxFlux = Math.max(...c.fluxes.map((f) => f.value), 0.001);
  const summary = t("data.cycles.summary", { element: t(`data.cycles.element.${el}`), list: c.fluxes.filter((f) => f.value > 0.01).sort((a, b) => b.value - a.value).slice(0, 3).map((f) => `${t(`data.cycles.flux.${f.id}`)} (${fmt(f.value, 1)})`).join(", ") });
  return (
    <div className="flex flex-col gap-3">
      <Tabs label={t("data.cycles.title")} value={el} onChange={(v) => setEl(v as CycleDiagram["element"])} tabs={cycles.map((x) => ({ id: x.element, label: t(`data.cycles.element.${x.element}`) }))} />
      <ChartFrame title={t("data.cycles.titleOf", { element: t(`data.cycles.element.${el}`) })} summary={summary}
        table={<DataTable caption={t("data.cycles.title")} rows={c.fluxes} rowKey={(f) => f.id} columns={[{ key: "n", header: t("data.cycles.fluxName"), render: (f) => t(`data.cycles.flux.${f.id}`) }, { key: "f", header: t("data.web.from"), render: (f) => t(`data.cycles.stock.${f.from}`) }, { key: "t", header: t("data.web.to"), render: (f) => t(`data.cycles.stock.${f.to}`) }, { key: "v", header: t("data.web.flux"), numeric: true, render: (f) => fmt(f.value, 2) }]} />}>
        <svg viewBox="0 0 700 380" className="mx-auto block w-full max-w-3xl" data-cycle={el}>
          <defs><marker id="carrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill={colors[0]} /></marker></defs>
          {c.fluxes.map((f, i) => { const a = LAYOUT[f.from], b = LAYOUT[f.to]; if (!a || !b) return null; const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1, off = 16 * (i % 2 ? 1 : -1), mx = (a[0] + b[0]) / 2 - (dy / len) * (28 + off), my = (a[1] + b[1]) / 2 + (dx / len) * (28 + off);
            return <g key={f.id} opacity={f.value > 0.01 ? 1 : 0.3}><path d={`M${a[0] + (dx / len) * 62} ${a[1] + (dy / len) * 30}Q${mx} ${my} ${b[0] - (dx / len) * 66} ${b[1] - (dy / len) * 32}`} fill="none" stroke={colors[0]} strokeWidth={1.5 + (f.value / maxFlux) * 5} className={f.value > 0.01 ? "ec-flow" : undefined} markerEnd="url(#carrow)" /><text x={mx} y={my} fontSize={11} textAnchor="middle" fill="var(--ec-text)" stroke="var(--ec-surface)" strokeWidth={3} paintOrder="stroke">{t(`data.cycles.flux.${f.id}`)} {fmt(f.value, 1)}</text></g>; })}
          {ids.map((id) => { const p = LAYOUT[id]; if (!p) return null; const stock = c.stocks.find((s) => s.id === id); return <g key={id}><rect x={p[0] - 60} y={p[1] - 28} width={120} height={56} rx={10} fill="var(--ec-surface-2)" stroke="var(--ec-border)" /><text x={p[0]} y={p[1] - 4} fontSize={13} fontWeight={600} textAnchor="middle" fill="var(--ec-text)">{t(`data.cycles.stock.${id}`)}</text><text x={p[0]} y={p[1] + 14} fontSize={12} textAnchor="middle" fill="var(--ec-text-muted)" fontFamily="var(--ec-font-mono)">{stock ? fmt(stock.value, 0) : "—"}</text></g>; })}
        </svg>
        <p className="ec-muted mt-1 text-center text-[length:var(--ec-text-xs)]">{t("data.cycles.unit")}</p>
        <Ped as="p" k={`ped.data.cycle.${el}`} className="mt-2" />
      </ChartFrame>
    </div>
  );
}
