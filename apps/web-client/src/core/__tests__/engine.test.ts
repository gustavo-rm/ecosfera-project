import { describe, expect, it } from "vitest";
import { SyntheticEngine } from "../source/synthetic/engine";
import { ARCHETYPE_PRESETS, SCENARIO_IDS } from "../source/synthetic/scenarios";

const row = (o: Record<string, unknown>) => Object.entries(o).map(([k, v]) => `${k}=${typeof v === "number" ? +v.toFixed(2) : v}`).join(" ");

describe("synthetic engine", () => {
  it("is deterministic: same seed and tick give the same frame", () => {
    const a = new SyntheticEngine({ scenarioId: "genesis", level: 3 }).frameAt(12000);
    const b = new SyntheticEngine({ scenarioId: "genesis", level: 3 }).frameAt(12000);
    expect(Array.from(a.fields.temperature)).toEqual(Array.from(b.fields.temperature));
    expect(a.bio.species.map((s) => s.population)).toEqual(b.bio.species.map((s) => s.population));
    const c = new SyntheticEngine({ scenarioId: "genesis", level: 3, seed: 99 }).frameAt(12000);
    expect(Array.from(c.fields.elevation)).not.toEqual(Array.from(a.fields.elevation));
  });

  it("Gênese: ancestral phototroph, then herbivores, then carnivores, at least 3 trophic levels", () => {
    const e = new SyntheticEngine({ scenarioId: "genesis", level: 3 });
    console.log("\nGênese por era:");
    for (const t of [100, 1800, 3000, 5000, 8500, 12500, 14500, 15200, 19000]) {
      const f = e.frameAt(t);
      console.log(" ", row({ tick: t, era: f.globals.era, arch: f.globals.archetype, T: f.globals.meanTempC, O2: f.globals.o2Pct, CO2: f.globals.co2Ppm, oceano: f.globals.oceanFraction, gelo: f.globals.iceFraction, nuvem: f.globals.cloudCover, spp: f.bio.richness, niveis: f.bio.trophicLevels, H: f.bio.shannon, pulso: f.globals.extinctionPulse }));
    }
    expect(e.frameAt(100).globals.archetype).toBe("molten");
    expect(e.frameAt(3000).bio.richness).toBe(0);
    expect(e.frameAt(5000).bio.species.filter((s) => s.alive).map((s) => s.role)).toContain("phototroph");
    expect(e.frameAt(5000).bio.trophicLevels).toBe(1);
    expect(e.frameAt(12500).bio.trophicLevels).toBeGreaterThanOrEqual(3);
    expect(e.frameAt(19000).bio.richness).toBeGreaterThan(e.frameAt(15400).bio.richness);
  });

  it("canonical scenarios have the expected shape", () => {
    console.log("\nCenários canônicos (fim):");
    for (const id of SCENARIO_IDS) {
      const e = new SyntheticEngine({ scenarioId: id, level: 3 });
      const f = e.frameAt(e.scenario.endTick - 10);
      console.log(" ", row({ id, spp: f.bio.richness, niveis: f.bio.trophicLevels, H: f.bio.shannon, dist: f.bio.geneticDistance, estrategias: f.bio.metabolicStrategies, biomassa: f.globals.totalBiomass, preso: f.globals.organicStuck, modos: [...new Set(f.bio.species.map((s) => s.speciationMode))].join("/") }));
    }
    const g = new SyntheticEngine({ scenarioId: "gradient", level: 3 }).frameAt(6000);
    expect(g.bio.species.filter((s) => s.speciationMode === "parapatric" && s.alive).length).toBeGreaterThanOrEqual(2);
    const ar = new SyntheticEngine({ scenarioId: "archipelago", level: 3 }).frameAt(6000);
    expect(ar.bio.species.filter((s) => s.speciationMode === "allopatric" && s.alive).length).toBeGreaterThanOrEqual(4);
    expect(ar.bio.flags.some((x) => x.type === "founder")).toBe(true);
    const cat = new SyntheticEngine({ scenarioId: "catastrophe", level: 3 });
    const before = cat.frameAt(1700).bio.richness, vac = cat.frameAt(2300).bio.richness, after = cat.frameAt(5800).bio.richness;
    expect(vac).toBeLessThan(before); expect(after).toBeGreaterThan(vac);
    expect(cat.frameAt(1900).bio.massExtinction || cat.frameAt(2100).bio.massExtinction).toBe(true);
    const nd = new SyntheticEngine({ scenarioId: "noDecomposers", level: 3 });
    expect(nd.frameAt(5000).globals.totalBiomass).toBeLessThan(nd.frameAt(300).globals.totalBiomass * 0.35);
    expect(nd.frameAt(5000).globals.organicStuck).toBeGreaterThan(0.9);
  });

  it("archetypes come from the same parametric pipeline", () => {
    console.log("\nArquétipos:");
    const got: Record<string, string> = {};
    for (const [name, p] of Object.entries(ARCHETYPE_PRESETS)) {
      const f = new SyntheticEngine({ scenarioId: p.scenarioId, level: 3, params: p.params }).frameAt(p.tick);
      got[name] = f.globals.archetype;
      console.log(" ", row({ name, arch: f.globals.archetype, T: f.globals.meanTempC, oceano: f.globals.oceanFraction, gelo: f.globals.iceFraction, nuvem: f.globals.cloudCover, P: f.globals.pressureBar, viab: f.globals.viability, spp: f.bio.richness }));
    }
    expect(got).toMatchObject({ molten: "molten", airless: "airless", greenhouse: "greenhouse", snowball: "snowball", desert: "desert", ocean: "ocean", terra: "temperate", archipelago: "archipelago", postExtinction: "postExtinction" });
  });

  it("history is cheap and marks eras, events and extinctions", () => {
    const e = new SyntheticEngine({ scenarioId: "genesis", level: 3 });
    const t0 = performance.now();
    const h = e.history(0, 20000, 200);
    console.log(`\nhistory(200 amostras): ${(performance.now() - t0).toFixed(0)} ms; marcas: ${h.marks.length}`);
    expect(h.ticks.length).toBe(200);
    expect(new Set(h.marks.map((m) => m.kind))).toEqual(new Set(["era", "event", "extinction", "speciation"]));
    const t1 = performance.now();
    new SyntheticEngine({ scenarioId: "genesis", level: 5 }).frameAt(12500);
    console.log(`frameAt nível 5 (com terreno): ${(performance.now() - t1).toFixed(0)} ms`);
  });
});
