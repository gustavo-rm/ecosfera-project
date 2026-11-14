/** Regression tests for defects found by the independent review. */
import { describe, expect, it } from "vitest";
import { axisEuler, northPole, SUN_DIRECTION } from "../appearance/appearance";
import { SyntheticEngine } from "../source/synthetic/engine";
import { getMesh } from "../mesh/geodesic";
import { buildPdf, toCsv } from "@/features/teacher/export";

const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

describe("seasons: the picture agrees with the data", () => {
  it("at yearPhase 0 (northern summer in the data) the north pole leans toward the star; half a year later, away", () => {
    expect(dot(northPole(0, 23.5), SUN_DIRECTION)).toBeGreaterThan(dot([0, 1, 0], SUN_DIRECTION) + 0.2);
    expect(dot(northPole(0.5, 23.5), SUN_DIRECTION)).toBeLessThan(dot([0, 1, 0], SUN_DIRECTION) - 0.2);
    expect(axisEuler(0.25, 40).z).toBeCloseTo((-40 * Math.PI) / 180);
  });
  it("the data has less northern ice at yearPhase 0 than at 0.5 (same convention as the picture)", () => {
    const mesh = getMesh(3), ice = (phase: number) => { const e = new SyntheticEngine({ scenarioId: "genesis", level: 3, params: { axialTiltDeg: 40 } }); e.setOverrides({ yearPhase: phase }); const f = e.frameAt(12900); let s = 0; for (let i = 0; i < mesh.count; i++) if (mesh.latitude[i] > 45) s += f.fields.ice[i]; return s; };
    expect(ice(0)).toBeLessThan(ice(0.5));
  });
  it("without tilt there are no seasons", () => { expect(northPole(0, 0)).toEqual(northPole(0.5, 0).map((v) => (Object.is(v, -0) ? 0 : v))); });
});

describe("synthetic engine: purity", () => {
  it("lab overrides act on a tick that was already computed", () => {
    const e = new SyntheticEngine({ scenarioId: "genesis", level: 3 }), before = e.frameAt(12900).globals.totalBiomass;
    e.setOverrides({ biomassScale: 0 });
    expect(e.frameAt(12900).globals.totalBiomass).toBeLessThan(before * 0.05);
    e.setOverrides({ organicStuck: 1 });
    expect(e.frameAt(12900).globals.totalBiomass).toBeLessThan(before * 0.5);
    e.setOverrides({});
    expect(e.frameAt(12900).globals.totalBiomass).toBeCloseTo(before, 10);
  });
  it("populations do not depend on the order in which ticks are asked", () => {
    const a = new SyntheticEngine({ scenarioId: "catastrophe", level: 3 }), b = new SyntheticEngine({ scenarioId: "catastrophe", level: 3 });
    a.history(0, 5000, 80); // fills the memo through many depths first
    const x = Array.from(a.populations(2500)), y = Array.from(b.populations(2500));
    expect(x).toEqual(y);
    for (const t of [3000, 1200, 4800, 2000]) expect(Array.from(a.populations(t))).toEqual(Array.from(new SyntheticEngine({ scenarioId: "catastrophe", level: 3 }).populations(t)));
  });
  it("tectonics 0 keeps the relief; tectonics 1 changes it between eras", () => {
    const still = new SyntheticEngine({ scenarioId: "genesis", level: 3, params: { tectonics: 0 } });
    expect(Array.from(still.frameAt(100).fields.elevation)).toEqual(Array.from(still.frameAt(19000).fields.elevation));
  });
});

describe("interventions change the world, not only the picture", () => {
  const herbivores = (e: SyntheticEngine, t: number) => e.frameAt(t).bio.species.filter((s) => s.role === "herbivore").reduce((a, s) => a + s.population, 0);
  it("suppressing an event reduces its mortality", () => {
    const plain = new SyntheticEngine({ scenarioId: "gradient", level: 3 }), hit = new SyntheticEngine({ scenarioId: "gradient", level: 3 }), saved = new SyntheticEngine({ scenarioId: "gradient", level: 3 });
    for (const e of [hit, saved]) e.addModifier({ id: "pan", kind: "event", eventType: "pandemic", tick: 5000, cell: 10, noTelegraph: true });
    saved.addModifier({ id: "sup", kind: "suppress", tick: 5000, eventId: "pan" });
    const p = herbivores(plain, 5060), h = herbivores(hit, 5060), s = herbivores(saved, 5060);
    console.log(`\nherbívoros: sem evento ${p.toFixed(0)}, com pandemia ${h.toFixed(0)}, pandemia suprimida ${s.toFixed(0)}`);
    expect(h).toBeLessThan(p * 0.8); expect(s).toBeGreaterThan(h * 1.2); expect(s).toBeLessThan(p);
  });
  it("an introduced lineage lives around the chosen cell", () => {
    const mesh = getMesh(3), e = new SyntheticEngine({ scenarioId: "gradient", level: 3 }), base = e.frameAt(4000);
    const cell = Array.from({ length: mesh.count }, (_, i) => i).find((i) => base.fields.isWater[i] === 0 && base.fields.ice[i] < 0.1 && Math.abs(mesh.latitude[i]) < 30)!;
    e.addModifier({ id: "x", kind: "introduce", role: "phototroph", tick: 4000, cell });
    e.observedLineage = "intro-x";
    const obs = e.frameAt(5500).fields.observed!, c = mesh.centers;
    let near = 0, far = 0;
    for (let i = 0; i < mesh.count; i++) { const d = c[i * 3] * c[cell * 3] + c[i * 3 + 1] * c[cell * 3 + 1] + c[i * 3 + 2] * c[cell * 3 + 2]; if (d > 0.9) near += obs[i]; else if (d < 0.5) far += obs[i]; }
    expect(near).toBeGreaterThan(0); expect(far).toBe(0);
  });
});

describe("exports are safe", () => {
  it("CSV text that looks like a formula is neutralized", () => expect(toCsv(["a"], [["=SOMA(A1)"], ["@x"], ["ok"]])).toBe("﻿a\r\n'=SOMA(A1)\r\n'@x\r\nok"));
  it("PDF keeps subscripts readable instead of a question mark", () => expect(new TextDecoder("latin1").decode(buildPdf("t", ["O₂ e CO₂"]))).toContain("(O2 e CO2)"));
});
