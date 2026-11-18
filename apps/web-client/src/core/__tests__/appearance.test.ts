/**
 * One test per row of the "variável do estado → efeito no planeta" table (mission section 8).
 * Each test changes ONE variable through the lab overrides or the parameters and checks the visual channel or uniform.
 */
import { describe, expect, it } from "vitest";
import { computeAppearance, createAppearance, type Appearance } from "../appearance/appearance";
import type { LayerId } from "../appearance/layers";
import { getMesh } from "../mesh/geodesic";
import { SyntheticEngine, type StateOverrides } from "../source/synthetic/engine";
import type { PlanetFrame, PlanetParams } from "../state/types";

const L = 3, mesh = getMesh(L), T = 12900;
function shot(o: { overrides?: StateOverrides; params?: Partial<PlanetParams>; scenario?: string; tick?: number; layer?: LayerId | null; observe?: string; mods?: (e: SyntheticEngine) => void } = {}): { f: PlanetFrame; a: Appearance } {
  const e = new SyntheticEngine({ scenarioId: o.scenario ?? "genesis", level: L, params: o.params });
  if (o.overrides) e.setOverrides(o.overrides);
  if (o.observe) e.observedLineage = o.observe;
  o.mods?.(e);
  const f = e.frameAt(o.tick ?? T);
  return { f, a: computeAppearance(f, mesh, { layer: o.layer ?? null, revealed: null, showHabitat: !!o.observe }, createAppearance(mesh.count)) };
}
const mean = (arr: Float32Array, ch: number, pick?: (i: number) => boolean) => { let s = 0, n = 0; for (let i = 0; i < mesh.count; i++) if (!pick || pick(i)) { s += arr[i * 4 + ch]; n++; } return n ? s / n : 0; };
const count = (arr: Float32Array, ch: number, test: (v: number) => boolean) => { let n = 0; for (let i = 0; i < mesh.count; i++) if (test(arr[i * 4 + ch])) n++; return n; };
const base = shot();

describe("state → appearance (section 8 table)", () => {
  it("elevation, is_water: relief displacement and ocean mask", () => {
    for (let i = 0; i < mesh.count; i++) expect(base.a.A[i * 4] < 0).toBe(base.f.fields.isWater[i] === 1);
    expect(Math.max(...Array.from({ length: mesh.count }, (_, i) => Math.hypot(base.a.grad[i * 3], base.a.grad[i * 3 + 1], base.a.grad[i * 3 + 2])))).toBeGreaterThan(0);
  });
  it("volcanism and tectonics: hot spots are emissive and the relief changes between eras", () => {
    expect(count(shot({ params: { volcanism: 1 } }).a.A, 2, (v) => v > 0.3)).toBeGreaterThan(count(shot({ params: { volcanism: 0 } }).a.A, 2, (v) => v > 0.3));
    const e = new SyntheticEngine({ scenarioId: "genesis", level: L, params: { tectonics: 1 } });
    expect(Array.from(e.frameAt(100).fields.elevation)).not.toEqual(Array.from(e.frameAt(19000).fields.elevation));
  });
  it("crust composition: rock and soil palette", () => {
    const dry = (crust: PlanetParams["crust"]) => shot({ params: { crust, waterFraction: 0, lifeSeed: false } }).a;
    expect(mean(dry("ferrous").B, 0) - mean(dry("ferrous").B, 2)).toBeGreaterThan(mean(dry("basaltic").B, 0) - mean(dry("basaltic").B, 2) + 0.1);
  });
  it("total water and temperature: ocean extent, sea ice and ice caps", () => {
    expect(count(shot({ overrides: { waterFraction: 0.9 } }).a.A, 0, (v) => v < 0)).toBeGreaterThan(count(shot({ overrides: { waterFraction: 0.3 } }).a.A, 0, (v) => v < 0));
    expect(mean(shot({ overrides: { tempOffset: -25 } }).a.A, 1)).toBeGreaterThan(mean(base.a.A, 1) + 0.2);
    expect(mean(shot({ overrides: { tempOffset: 25 } }).a.A, 1)).toBeLessThan(mean(base.a.A, 1));
  });
  it("salinity and pH: data layers and a subtle water tone", () => {
    expect(shot({ overrides: { oceanPh: 4.5 } }).a.uniforms.oceanShallow).not.toEqual(base.a.uniforms.oceanShallow);
    expect(shot({ overrides: { salinityPpt: 45 } }).a.uniforms.oceanShallow).not.toEqual(base.a.uniforms.oceanShallow);
    const water = (i: number) => base.f.fields.isWater[i] === 1;
    expect(mean(shot({ layer: "ph", overrides: { oceanPh: 4.5 } }).a.C, 0, water)).toBeLessThan(mean(shot({ layer: "ph" }).a.C, 0, water));
    expect(mean(shot({ layer: "salinity", overrides: { salinityPpt: 44 } }).a.C, 0, water)).toBeGreaterThan(mean(shot({ layer: "salinity" }).a.C, 0, water));
  });
  it("pressure: limb thickness; without atmosphere there is no limb, no clouds and a hard terminator", () => {
    const none = shot({ overrides: { pressureBar: 0 } }).a.uniforms, thick = shot({ overrides: { pressureBar: 5 } }).a.uniforms;
    expect(none.atmoDensity).toBe(0); expect(none.cloudOpacity).toBe(0); expect(none.aurora).toBe(0);
    expect(thick.atmoDensity).toBeGreaterThan(base.a.uniforms.atmoDensity);
    expect(none.terminatorSoftness).toBeLessThan(base.a.uniforms.terminatorSoftness);
  });
  it("O2, CO2, CH4, aerosols: sky color and turbidity", () => {
    const b = base.a.uniforms, prim = shot({ overrides: { o2Pct: 0, co2Ppm: 20000, ch4Ppm: 500 } }).a.uniforms, dust = shot({ overrides: { aerosols: 0.9 } }).a.uniforms;
    expect(b.skyColor[2]).toBeGreaterThan(b.skyColor[0]);          // oxygenated: bluish
    expect(prim.skyColor[0]).toBeGreaterThan(prim.skyColor[2]);    // primitive: orange and turbid
    expect(prim.haze).toBeGreaterThan(b.haze);
    expect(dust.sunDim).toBeLessThan(b.sunDim); expect(dust.haze).toBeGreaterThan(b.haze);
  });
  it("humidity and precipitation: cloud cover and storms", () => {
    expect(mean(shot({ overrides: { humidityScale: 1.8 } }).a.A, 3)).toBeGreaterThan(mean(shot({ overrides: { humidityScale: 0.2 } }).a.A, 3) + 0.2);
    const storm = shot({ mods: (e) => e.addModifier({ id: "s", kind: "event", eventType: "storm", tick: T - 10, cell: 40, noTelegraph: true }) });
    expect(storm.a.D[40 * 4 + 1]).toBeGreaterThan(0.5); expect(storm.a.A[40 * 4 + 3]).toBeGreaterThan(0.8);
  });
  it("magnetic field and star activity: auroras, and erosion when the field is weak", () => {
    expect(shot({ overrides: { magneticField: 1, starActivity: 1 } }).a.uniforms.aurora).toBeGreaterThan(shot({ overrides: { magneticField: 1, starActivity: 0 } }).a.uniforms.aurora);
    expect(shot({ overrides: { magneticField: 0, starActivity: 1 } }).a.uniforms.aurora).toBe(0);
    expect(shot({ overrides: { magneticField: 0.02, starActivity: 1 } }).a.uniforms.erosion).toBeGreaterThan(0.5);
    expect(base.a.uniforms.erosion).toBe(0);
  });
  it("temperature: heat layer and snow versus savanna", () => {
    expect(mean(shot({ layer: "temperature", overrides: { tempOffset: 15 } }).a.C, 0)).toBeGreaterThan(mean(shot({ layer: "temperature" }).a.C, 0));
    expect(shot({ layer: "temperature" }).a.uniforms.layerMode).toBe(1); expect(shot({ layer: "biome" }).a.uniforms.layerMode).toBe(2);
  });
  it("solar flux, tilt, eccentricity, day length: seasons move the ice", () => {
    const north = (i: number) => mesh.latitude[i] > 45;
    const winter = shot({ overrides: { yearPhase: 0.5 }, params: { axialTiltDeg: 40 } }), summer = shot({ overrides: { yearPhase: 0 }, params: { axialTiltDeg: 40 } });
    expect(mean(winter.a.A, 1, north)).toBeGreaterThan(mean(summer.a.A, 1, north));
    const u = shot({ params: { axialTiltDeg: 40, eccentricity: 0.3, dayHours: 10 } }).a.uniforms;
    expect([u.axialTiltDeg, u.eccentricity, u.dayHours]).toEqual([40, 0.3, 10]);
  });
  it("star type and age: color, intensity and apparent size", () => {
    const m = shot({ params: { starType: "M", orbitAU: 0.3 } }).a.uniforms, a = shot({ params: { starType: "A", orbitAU: 2.8 } }).a.uniforms;
    expect(m.starColor[0] - m.starColor[2]).toBeGreaterThan(a.starColor[0] - a.starColor[2]);
    expect(shot({ params: { orbitAU: 0.7 } }).a.uniforms.starSize).toBeGreaterThan(base.a.uniforms.starSize);
    expect(shot({ params: { orbitAU: 0.7 } }).a.uniforms.starIntensity).toBeGreaterThan(base.a.uniforms.starIntensity);
  });
  it("number of moons", () => { expect(shot({ params: { moons: 3 } }).a.uniforms.moons).toBe(3); });
  it("soil fertility: darker, more saturated soil", () => {
    const land = (f: PlanetFrame) => (i: number) => f.fields.isWater[i] === 0 && f.fields.ice[i] < 0.1;
    const rich = shot({ params: { soilFertility: 1, lifeSeed: false } }), poor = shot({ params: { soilFertility: 0, lifeSeed: false } });
    expect(mean(rich.a.B, 0, land(rich.f)) + mean(rich.a.B, 1, land(rich.f)) + mean(rich.a.B, 2, land(rich.f))).toBeLessThan(mean(poor.a.B, 0, land(poor.f)) + mean(poor.a.B, 1, land(poor.f)) + mean(poor.a.B, 2, land(poor.f)));
  });
  it("phototrophic biomass: greenness and vegetation cover; mats and blooms in the ocean", () => {
    const lush = shot({ overrides: { biomassScale: 2 } }), bare = shot({ overrides: { biomassScale: 0 } });
    expect(mean(lush.a.B, 3)).toBeGreaterThan(mean(bare.a.B, 3) + 0.05);
    const land = (i: number) => lush.f.fields.isWater[i] === 0 && lush.f.fields.ice[i] < 0.1;
    expect(mean(lush.a.B, 1, land) - mean(lush.a.B, 0, land)).toBeGreaterThan(mean(bare.a.B, 1, land) - mean(bare.a.B, 0, land));
    expect(mean(shot({ tick: 5600 }).a.C, 2)).toBeGreaterThan(mean(shot({ tick: 3000 }).a.C, 2));
  });
  it("biodiversity and richness: hue variety follows the dominant lineage", () => {
    // Same cells, with and without local richness: only the lineage-driven hue shift differs.
    const rich = shot({ overrides: { richnessScale: 3 } }), flat = shot({ overrides: { richnessScale: 0 } });
    let diff = 0, n = 0;
    for (let i = 0; i < mesh.count; i++) if (rich.a.B[i * 4 + 3] > 0.5) { diff += Math.abs(rich.a.B[i * 4] - flat.a.B[i * 4]); n++; }
    expect(n).toBeGreaterThan(20); expect(diff / n).toBeGreaterThan(0.01);
  });
  it("cohorts per lineage: dominant lineage per group and the habitat of an observed lineage", () => {
    expect(Array.from(base.f.fields.domProducer).some((v) => v >= 0)).toBe(true);
    expect(Array.from(base.f.fields.domCarn).some((v) => v >= 0)).toBe(true);
    const obs = shot({ observe: "pla1" });
    expect(obs.f.fields.observed).not.toBeNull(); expect(mean(obs.a.D, 3)).toBeGreaterThan(0);
  });
  it("accumulated organic matter without decomposers: dark patches and lower productivity", () => {
    const stuck = shot({ overrides: { organicStuck: 1 } });
    const land = (i: number) => base.f.fields.isWater[i] === 0 && base.f.fields.ice[i] < 0.1;
    expect(mean(stuck.a.B, 1, land)).toBeLessThan(mean(base.a.B, 1, land));
    expect(stuck.f.globals.totalBiomass).toBeLessThan(base.f.globals.totalBiomass * 0.5);
  });
  it("mass extinction: transient desaturation, then variety returns", () => {
    const e = new SyntheticEngine({ scenarioId: "catastrophe", level: L }), ap = (t: number) => computeAppearance(e.frameAt(t), mesh, { layer: null, revealed: null, showHabitat: false }, createAppearance(mesh.count)).uniforms.desaturate;
    expect(ap(1700)).toBe(0); expect(ap(1900)).toBeGreaterThan(0.5); expect(ap(5800)).toBeLessThan(0.01);
    expect(shot({ overrides: { extinctionPulse: 1 } }).a.uniforms.desaturate).toBeGreaterThan(0.7);
  });
  it("disturbances: localized effects per event type", () => {
    const ev = (type: "fire" | "drought" | "volcanism" | "impact" | "eutrophication" | "pandemic", cell: number, dt = 30) => shot({ mods: (e) => e.addModifier({ id: "x", kind: "event", eventType: type, tick: T - dt, cell, noTelegraph: true }) });
    const landCell = Array.from({ length: mesh.count }, (_, i) => i).find((i) => base.f.fields.isWater[i] === 0 && base.f.fields.ice[i] < 0.1 && base.f.fields.biomassPhoto[i] > 0.3)!;
    const waterCell = Array.from({ length: mesh.count }, (_, i) => i).find((i) => base.f.fields.isWater[i] === 1 && base.f.fields.ice[i] < 0.1)!;
    expect(ev("fire", landCell).a.C[landCell * 4 + 3]).toBeGreaterThan(0.2);
    expect(ev("drought", landCell, 100).a.D[landCell * 4]).toBeGreaterThan(0.5);
    const volc = ev("volcanism", landCell); expect(volc.a.A[landCell * 4 + 2]).toBeGreaterThan(0.5); expect(volc.a.uniforms.sunDim).toBeLessThan(base.a.uniforms.sunDim);
    const imp = ev("impact", landCell); expect(imp.a.D[landCell * 4 + 2]).toBeGreaterThan(0.5); expect(imp.a.uniforms.haze).toBeGreaterThan(base.a.uniforms.haze + 0.3);
    const eu = ev("eutrophication", waterCell, 100); expect(eu.a.C[waterCell * 4 + 2]).toBeGreaterThan(base.a.C[waterCell * 4 + 2]); expect(eu.a.D[waterCell * 4 + 2]).toBeGreaterThan(0.2);
    expect(ev("pandemic", landCell).a.D[landCell * 4 + 3]).toBeGreaterThan(0.3);
    const ice = shot({ mods: (e) => e.addModifier({ id: "g", kind: "event", eventType: "glaciation", tick: T - 600, cell: 0, noTelegraph: true }) });
    expect(mean(ice.a.A, 1)).toBeGreaterThan(mean(base.a.A, 1) + 0.15); expect(ice.f.globals.seaLevelM).toBeLessThan(base.f.globals.seaLevelM);
  });
  it("very high surface temperature, Era 1: incandescent surface or cloud-covered world", () => {
    const molten = shot({ tick: 100 }); expect(molten.a.uniforms.surfaceHeat).toBeGreaterThan(0.9); expect(count(molten.a.A, 0, (v) => v < 0)).toBe(0);
    const green = shot({ params: { orbitAU: 0.72, co2Ppm: 60000, pressureBar: 6 } });
    expect(mean(green.a.A, 3)).toBeGreaterThan(0.95); expect(green.a.uniforms.cloudOpacity).toBeGreaterThan(0.9); expect(count(green.a.A, 0, (v) => v < 0)).toBe(0);
  });
  it("is deterministic: same state and seed, same channels (principle 8)", () => {
    const again = shot();
    expect(Array.from(again.a.A)).toEqual(Array.from(base.a.A)); expect(Array.from(again.a.B)).toEqual(Array.from(base.a.B)); expect(again.a.uniforms).toEqual(base.a.uniforms);
  });
});
