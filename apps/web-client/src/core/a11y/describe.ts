/**
 * Text description of the planet state, generated from the state (RNF-018). Pure: used by aria-live regions,
 * by the text mode (alternative to the 3D view) and by unit tests.
 */
import { t, fmt } from "@/i18n";
import { BIOME_COUNT } from "../state/catalogs";
import type { PlanetFrame } from "../state/types";

export interface PlanetDescription { headline: string; sentences: string[]; biomes: { biome: number; share: number }[]; events: string[] }

export function biomeShares(frame: PlanetFrame): { biome: number; share: number }[] {
  const counts = new Array(BIOME_COUNT).fill(0), b = frame.fields.biome;
  for (let i = 0; i < frame.cellCount; i++) counts[b[i]]++;
  return counts.map((c, biome) => ({ biome, share: c / frame.cellCount })).filter((x) => x.share > 0.005).sort((a, b2) => b2.share - a.share);
}

export function describePlanet(frame: PlanetFrame): PlanetDescription {
  const g = frame.globals, bio = frame.bio;
  const biomes = biomeShares(frame);
  const headline = t("describe.headline", { era: t(`era.${g.era}.name`), year: fmt(g.year), archetype: t(`archetype.${g.archetype}`) });
  const s: string[] = [];
  s.push(t("describe.temperature", { value: fmt(Math.min(g.meanTempC, 9999), 0) }));
  s.push(g.pressureBar < 0.03 ? t("describe.noAtmosphere") : t("describe.atmosphere", { o2: fmt(g.o2Pct, 1), co2: fmt(g.co2Ppm, 0), pressure: fmt(g.pressureBar, 2) }));
  s.push(g.oceanFraction < 0.01 ? t("describe.noOcean") : t("describe.ocean", { ocean: fmt(g.oceanFraction * 100, 0), ice: fmt(g.iceFraction * 100, 0), ph: fmt(g.oceanPh, 1) }));
  if (biomes.length) s.push(t("describe.biomes", { list: biomes.slice(0, 4).map((b) => `${t(`biome.${b.biome}`)} (${fmt(b.share * 100, 0)}%)`).join(", ") }));
  if (bio.richness === 0) s.push(g.viability < 0.05 && frame.params.lifeSeed ? t("describe.lifeImpossible") : t("describe.noLife"));
  else s.push(t("describe.life", { richness: bio.richness, levels: bio.trophicLevels }));
  if (g.organicStuck > 0.3) s.push(t("describe.stuck"));
  if (bio.massExtinction) s.push(t("describe.massExtinction"));
  const events = frame.events.filter((e) => e.origin !== "background" || e.intensity > 0.3).map((e) =>
    t(e.phase === "telegraph" ? "describe.eventTelegraph" : e.phase === "active" ? "describe.eventActive" : "describe.eventAftermath", { name: t(`event.${e.type}.name`), lat: fmt(e.lat, 0), lon: fmt(e.lon, 0), instrument: t(`instrument.${e.instrument}`) }));
  s.push(events.length ? t("describe.events", { list: events.join("; ") }) : t("describe.noEvents"));
  if (frame.meta.mode === "fast") s.push(t("describe.fastMode"));
  return { headline, sentences: s, biomes, events };
}

/** Short announcement of what changed between two frames, for the polite live region. Empty when nothing notable changed. */
export function describeChange(prev: PlanetFrame | null, next: PlanetFrame): string {
  if (!prev) return "";
  const out: string[] = [];
  if (prev.globals.era !== next.globals.era) out.push(t("describe.newEra", { era: t(`era.${next.globals.era}.name`) }));
  const before = new Set(prev.events.map((e) => e.id + e.phase));
  for (const e of next.events) if (e.origin !== "background" && !before.has(e.id + e.phase) && e.phase !== "aftermath")
    out.push(t(e.phase === "telegraph" ? "describe.eventTelegraph" : "describe.eventActive", { name: t(`event.${e.type}.name`), lat: fmt(e.lat, 0), lon: fmt(e.lon, 0), instrument: t(`instrument.${e.instrument}`) }));
  if (!prev.bio.massExtinction && next.bio.massExtinction) out.push(t("describe.massExtinction"));
  if (prev.bio.richness > 0 && next.bio.richness === 0) out.push(t("describe.noLife"));
  return out.join(" ");
}
