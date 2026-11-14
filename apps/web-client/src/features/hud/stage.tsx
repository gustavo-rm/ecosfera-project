"use client";
import dynamic from "next/dynamic";
import { useId, useMemo } from "react";
import { LAYER_BY_ID } from "@/core/appearance/layers";
import { DIVERGING, SEQUENTIAL, samplePalette, toHex } from "@/core/appearance/palettes";
import { describePlanet } from "@/core/a11y/describe";
import { getMesh } from "@/core/mesh/geodesic";
import { BIOME_COLORS } from "@/core/state/catalogs";
import { fmt, t } from "@/i18n";
import { cameraApi } from "@/render/CameraRig";
import { usePlanetStore } from "@/store/planetStore";
import { useSettings } from "@/store/settingsStore";
import { DataTable, ErrorState, Loading } from "@/ui/kit";
import { useReducedMotion } from "../session/hooks";

const PlanetView = dynamic(() => import("@/render/PlanetView"), { ssr: false, loading: () => <Loading /> });

/** Text alternative to the 3D view: the same information as lists and a table (RNF-018). */
export function TextMode() {
  const frame = usePlanetStore((s) => s.frame);
  const d = useMemo(() => (frame ? describePlanet(frame) : null), [frame]);
  if (!frame || !d) return <Loading />;
  const mesh = getMesh(frame.level), f = frame.fields;
  // Regional summary by latitude band, so that a table can stand in for the globe.
  const bands = [[60, 90], [30, 60], [0, 30], [-30, 0], [-60, -30], [-90, -60]].map(([lo, hi]) => {
    let n = 0, temp = 0, rain = 0, veg = 0, ice = 0, water = 0;
    for (let i = 0; i < frame.cellCount; i++) { const la = mesh.latitude[i]; if (la >= lo && la < hi) { n++; temp += f.temperature[i]; rain += f.precipitation[i]; veg += f.biomassPhoto[i]; ice += f.ice[i]; water += f.isWater[i]; } }
    return { label: t("textMode.band", { lo, hi }), temp: temp / n, rain: rain / n, veg: veg / n, ice: ice / n, water: water / n };
  });
  return (
    <div className="ec-scroll h-full p-4 pt-20 sm:px-[280px]" data-text-mode tabIndex={0} role="region" aria-label={t("textMode.title")}>
      <h2>{t("textMode.title")}</h2>
      <p className="mt-2 font-semibold">{d.headline}</p>
      <ul className="mt-2 list-disc space-y-1 pl-6">{d.sentences.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3 className="mt-4">{t("textMode.regions")}</h3>
      <DataTable caption={t("textMode.regions")} rows={bands} rowKey={(r) => r.label} columns={[
        { key: "band", header: t("textMode.latitude"), render: (r) => r.label },
        { key: "temp", header: t("layer.temperature.name") + " (°C)", numeric: true, render: (r) => fmt(r.temp, 0) },
        { key: "rain", header: t("layer.precipitation.name") + " (mm/mês)", numeric: true, render: (r) => fmt(r.rain, 0) },
        { key: "water", header: t("textMode.ocean") + " (%)", numeric: true, render: (r) => fmt(r.water * 100, 0) },
        { key: "ice", header: t("textMode.ice") + " (%)", numeric: true, render: (r) => fmt(r.ice * 100, 0) },
        { key: "veg", header: t("layer.biomass.name"), numeric: true, render: (r) => fmt(r.veg, 2) },
      ]} />
      <h3 className="mt-4">{t("textMode.species")}</h3>
      <DataTable caption={t("textMode.species")} rows={frame.bio.species.filter((s) => s.alive)} rowKey={(r) => r.id} columns={[
        { key: "name", header: t("codex.name"), render: (r) => r.name },
        { key: "role", header: t("codex.role"), render: (r) => t(`role.${r.role}`) },
        { key: "level", header: t("codex.trophicLevel"), numeric: true, render: (r) => r.trophicLevel + 1 },
        { key: "pop", header: t("codex.population"), numeric: true, render: (r) => fmt(r.population, 0) },
      ]} />
    </div>
  );
}

/** The planet with keyboard control, a generated description for screen readers and the loading/error states. */
export function PlanetStage({ interactive = true }: { interactive?: boolean }) {
  const status = usePlanetStore((s) => s.status);
  const errorDetail = usePlanetStore((s) => s.errorDetail);
  const frame = usePlanetStore((s) => s.frame);
  const textMode = useSettings((s) => s.textMode);
  const palette = useSettings((s) => s.palette);
  const reduced = useReducedMotion();
  const descId = useId();
  // The description follows the state but changes at most once per simulated year, to keep screen readers calm.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const desc = useMemo(() => (frame ? describePlanet(frame) : null), [frame && Math.floor(frame.tick / 12), frame?.globals.era, frame?.events.length]);
  const onKey = (e: React.KeyboardEvent) => {
    const st = usePlanetStore.getState(), step = e.shiftKey ? 0.35 : 0.12;
    switch (e.key) {
      case "ArrowLeft": cameraApi.rotate(-step, 0); break; case "ArrowRight": cameraApi.rotate(step, 0); break;
      case "ArrowUp": cameraApi.rotate(0, -step); break; case "ArrowDown": cameraApi.rotate(0, step); break;
      case "+": case "=": cameraApi.zoom(0.85); break; case "-": case "_": cameraApi.zoom(1.18); break;
      case "Home": case "0": cameraApi.reset(); break;
      case "Enter": cameraApi.pickCenter(); break;
      case "f": case "F": if (st.selectedCell !== null) st.focusOn(st.selectedCell); break;
      case "Escape": st.selectCell(null); break;
      case " ": st.setClock(!st.playing); break;
      default: return;
    }
    e.preventDefault();
  };
  return (
    <div className="absolute inset-0" data-status={status} data-tick={frame?.tick ?? ""}>
      {status === "error" ? <div className="flex h-full items-center justify-center"><ErrorState detail={errorDetail} onRetry={() => { const c = usePlanetStore.getState().config; if (c) void usePlanetStore.getState().init(c); }} /></div>
        : !frame ? <div className="flex h-full items-center justify-center"><Loading label={t("planet.loading")} /></div>
        : textMode ? <TextMode />
        : (
          <div tabIndex={interactive ? 0 : -1} role="application" aria-roledescription={t("planet.roleDescription")} aria-label={t("planet.label")} aria-describedby={descId} onKeyDown={interactive ? onKey : undefined} className="h-full w-full" data-planet-stage>
            <PlanetView paletteSet={palette} reducedMotion={reduced} interactive={interactive} />
          </div>
        )}
      <div id={descId} className="ec-sr-only" data-planet-description>
        {desc && <><p>{desc.headline}</p>{desc.sentences.map((s, i) => <p key={i}>{s}</p>)}<p>{t("planet.keyboardHelp")}</p></>}
      </div>
    </div>
  );
}

/** Legend of the active data layer: palette, unit, range, and the line that separates data from stylized picture. */
export function LayerLegend() {
  const layer = usePlanetStore((s) => s.layer);
  const palette = useSettings((s) => s.palette);
  const exaggeration = usePlanetStore((s) => s.exaggeration);
  if (!layer) return <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("legend.stylized", { factor: fmt((exaggeration * 6371) / 8, 0) })}</p>;
  const def = LAYER_BY_ID[layer];
  if (def.kind === "categorical") return (
    <ul className="grid grid-cols-2 gap-x-2 gap-y-1 text-[length:var(--ec-text-xs)]" aria-label={t("legend.title")}>
      {BIOME_COLORS.map((c, i) => <li key={i} className="flex items-center gap-1"><span aria-hidden="true" className="inline-block h-3 w-3 flex-none rounded-sm border border-ec-border" style={{ background: toHex(c) }} />{t(`biome.${i}`)}</li>)}
    </ul>
  );
  const name = (def.kind === "diverging" ? DIVERGING : SEQUENTIAL)[palette];
  const stops = Array.from({ length: 9 }, (_, i) => toHex(samplePalette(name, i / 8))).join(",");
  return (
    <div className="text-[length:var(--ec-text-xs)]" aria-label={t("legend.title")}>
      <div className="h-3 rounded-sm border border-ec-border" style={{ background: `linear-gradient(90deg, ${stops})` }} aria-hidden="true" />
      <div className="ec-num mt-1 flex justify-between"><span>{fmt(def.min)}</span><span>{def.unit || t("legend.relative")}</span><span>{fmt(def.max)}</span></div>
      <p className="ec-muted mt-1">{t("legend.literal")}</p>
    </div>
  );
}
