import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { describeChange, describePlanet } from "../a11y/describe";
import { contrastRatio, deltaE, luminance, samplePalette, SERIES_COLORS, SERIES_COLORS_DARK, simulateCvd, type CvdType } from "../appearance/palettes";
import { exportFixture, importFixture } from "../source/FixtureSource";
import { SyntheticEngine } from "../source/synthetic/engine";
import { classifyRegime, regimeMetrics } from "../state/metrics";
import { GENES } from "../state/catalogs";
import { INTERVENTIONS } from "@/game/catalog";
import { answerQuestion } from "@/game/tutor";
import { buildPdf, toCsv } from "@/features/teacher/export";
import { allKeys, hasKey, t } from "@/i18n";
import { SnapshotBuffer } from "@/store/snapshotBuffer";

const engine = () => new SyntheticEngine({ scenarioId: "genesis", level: 3 });

describe("design tokens: WCAG contrast (RNF-020)", () => {
  const css = fs.readFileSync(path.resolve(__dirname, "../../styles/tokens.css"), "utf8");
  const themes: Record<string, Record<string, string>> = {};
  for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const vars = Object.fromEntries([...m[2].matchAll(/--ec-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)].map((x) => [x[1], x[2]]));
    if (Object.keys(vars).length > 8) themes[m[1].trim().split(",").pop()!.trim()] = vars;
  }
  it("finds the four themes", () => expect(Object.keys(themes).sort()).toEqual([".ec-contrast-high.ec-theme-dark", ".ec-contrast-high.ec-theme-light", ".ec-theme-dark", ".ec-theme-light"]));
  it("text is at least 4.5:1 and interface elements at least 3:1, in every theme", () => {
    const rows: string[] = [];
    for (const [name, v] of Object.entries(themes)) {
      const text: [string, string][] = [["text", "bg"], ["text", "surface"], ["text", "surface-2"], ["text", "surface-3"], ["text-muted", "bg"], ["text-muted", "surface"], ["text-muted", "surface-2"], ["on-primary", "primary"], ["on-primary", "primary-hover"], ["on-accent", "accent"], ["on-danger", "danger"],
        ["info", "surface"], ["success", "surface"], ["warning", "surface"], ["danger", "surface"], ["synthetic", "surface"], ["primary", "surface"], ["warning", "surface-2"], ["danger", "surface-2"]];
      const ui: [string, string][] = [["border", "bg"], ["border", "surface"], ["border", "surface-2"], ["focus", "bg"], ["focus", "surface"], ["focus", "surface-2"], ["primary", "bg"], ["primary", "surface-3"]];
      for (const [a, b] of text) { const r = contrastRatio(v[a], v[b]); rows.push(`${name} ${a}/${b} ${r.toFixed(2)}`); expect(r, `${name}: ${a} on ${b}`).toBeGreaterThanOrEqual(4.5); }
      for (const [a, b] of ui) { const r = contrastRatio(v[a], v[b]); rows.push(`${name} ${a}/${b} ${r.toFixed(2)}`); expect(r, `${name}: ${a} on ${b}`).toBeGreaterThanOrEqual(3); }
      if (name.includes("high")) expect(contrastRatio(v.text, v.bg)).toBeGreaterThanOrEqual(15);
    }
    fs.mkdirSync(path.resolve(__dirname, "../../../.reports"), { recursive: true });
    fs.writeFileSync(path.resolve(__dirname, "../../../.reports/contrast.txt"), rows.join("\n"));
  });
});

describe("palettes are safe for color blindness (RNF-015)", () => {
  const types: CvdType[] = ["protan", "deutan", "tritan"];
  it("sequential ramps keep lightness monotonic, with and without color blindness", () => {
    for (const name of ["viridis", "cividis", "gray"]) for (const type of [null, ...types]) {
      let prev = -1;
      for (let i = 0; i <= 16; i++) { const c = samplePalette(name, i / 16), l = luminance(type ? simulateCvd(c, type) : c); expect(l, `${name} ${type}`).toBeGreaterThan(prev - 1e-6); prev = l; }
    }
  });
  it("diverging ramps keep both ends apart from the middle and from each other", () => {
    for (const name of ["blueOrange", "blueYellow"]) for (const type of types) {
      const a = simulateCvd(samplePalette(name, 0), type), m = simulateCvd(samplePalette(name, 0.5), type), b = simulateCvd(samplePalette(name, 1), type);
      expect(deltaE(a, b)).toBeGreaterThan(25); expect(deltaE(a, m)).toBeGreaterThan(20); expect(deltaE(b, m)).toBeGreaterThan(20);
    }
  });
  it("chart series stay distinguishable under simulation (and each one also has a dash pattern and a label)", () => {
    for (const set of [SERIES_COLORS.slice(0, 6), SERIES_COLORS_DARK.slice(0, 6)]) for (const type of types)
      // Adjacent slots (the order in which series are assigned) must be clearly apart; any other pair must still differ.
      // The palettes were also validated with the dataviz validator (OKLab, adjacent pairs). Color is never the only cue.
      for (let i = 0; i < set.length; i++) for (let j = i + 1; j < set.length; j++) expect(deltaE(simulateCvd(set[i], type), simulateCvd(set[j], type)), `${set[i]} ${set[j]} ${type}`).toBeGreaterThan(j === i + 1 ? 9 : 4);
  });
});

describe("text description of the planet (RNF-018)", () => {
  it("covers temperature, atmosphere, oceans, biomes, life and events", () => {
    const d = describePlanet(engine().frameAt(12900));
    console.log("\n" + [d.headline, ...d.sentences].join("\n"));
    expect(d.headline).toContain("Colonização Terrestre");
    expect(d.sentences.join(" ")).toMatch(/Temperatura média de 16 °C.*oxigênio.*Oceanos cobrem 68%.*Biomas principais.*linhagens vivas/s);
    expect(d.sentences.join(" ")).not.toContain("⟦");
  });
  it("explains worlds without air, without ocean, without life, and running events", () => {
    const airless = describePlanet(new SyntheticEngine({ scenarioId: "genesis", level: 3, params: { pressureBar: 0, waterFraction: 0, lifeSeed: false } }).frameAt(12900)).sentences.join(" ");
    expect(airless).toContain("Não há atmosfera"); expect(airless).toContain("Não há oceano"); expect(airless).toContain("Não há vida");
    expect(describePlanet(engine().frameAt(15010)).sentences.join(" ")).toContain("Impacto de meteoro em curso");
    expect(describePlanet(engine().frameAt(14980)).sentences.join(" ")).toContain("detectado pelo telescópio");
  });
  it("announces only notable changes", () => {
    const e = engine();
    expect(describeChange(e.frameAt(12000), e.frameAt(12012))).toBe("");
    expect(describeChange(e.frameAt(13190), e.frameAt(13210))).toContain("Grandes Extinções");
  });
});

describe("regime metrics (spec §24.4)", () => {
  it("the healthy synthetic regime is homeochaos and respects the viability test", () => {
    const e = new SyntheticEngine({ scenarioId: "gradient", level: 3 }), m = regimeMetrics(e.history(0, 7000, 400), 4000);
    console.log("\nregime (gradiente):", JSON.stringify(m));
    expect(m.dominance).toBeLessThan(0.8); expect(m.dominance).toBeGreaterThan(0.1);
    expect(m.populationCV).toBeGreaterThan(0.05); expect(m.populationCV).toBeLessThan(1);
    expect(m.coexisting).toBeGreaterThan(6); expect(m.autocorrelation).toBeGreaterThan(0.3);
    expect(classifyRegime(m)).toBe("homeochaos");
  });
  it("predator and prey oscillate out of phase", () => {
    const e = new SyntheticEngine({ scenarioId: "gradient", level: 3 }), h = e.history(4000, 7000, 600), prey = h.populations.grazer, pred = h.populations.hunter;
    const corr = (lag: number) => { let s = 0, n = 0; const mp = prey.reduce((a, b) => a + b) / prey.length, mq = pred.reduce((a, b) => a + b) / pred.length; for (let i = 0; i + lag < prey.length; i++) { s += (prey[i] - mp) * (pred[i + lag] - mq); n++; } return s / n; };
    const best = Array.from({ length: 30 }, (_, lag) => corr(lag)).reduce((bi, v, i, a) => (v > a[bi] ? i : bi), 0);
    expect(best).toBeGreaterThan(0);
  });
  it("no life gives the class 'none'", () => expect(classifyRegime(regimeMetrics(engine().history(0, 3000, 100)))).toBe("none"));
});

describe("snapshot buffer (RF-059)", () => {
  it("keeps order, capacity and brackets a tick", () => {
    const e = engine(), b = new SnapshotBuffer(6, 60);
    for (let t = 0; t <= 2400; t += 120) b.push(e.frameAt(t));
    expect(b.size).toBe(6); expect(b.ticks()).toEqual([...b.ticks()].sort((x, y) => x - y)); expect(b.ticks()[0]).toBe(0); expect(b.ticks()[5]).toBe(2400);
    const br = b.bracket(1000); expect(br.before!.tick).toBeLessThanOrEqual(1000); expect(br.after!.tick).toBeGreaterThan(1000);
    expect(b.nearest(2390)!.tick).toBe(2400);
  });
});

describe("fixtures", () => {
  it("round-trips a frame with its typed arrays", () => {
    const f = engine().frameAt(9000), back = importFixture(exportFixture([f]))[0];
    expect(back.fields.temperature).toBeInstanceOf(Float32Array); expect(back.fields.isWater).toBeInstanceOf(Uint8Array); expect(back.fields.domProducer).toBeInstanceOf(Int16Array);
    expect(Array.from(back.fields.temperature)).toEqual(Array.from(f.fields.temperature)); expect(back.globals).toEqual(f.globals);
    expect(() => importFixture("{}")).toThrow();
  });
});

describe("rules of the game that protect the science", () => {
  it("no intervention edits genomes, fitness or survivors (spec §20.5)", () => {
    const kinds = new Set(INTERVENTIONS.map((i) => i.kind));
    for (const k of kinds) expect(["scan", "study", "event", "suppress", "reforest", "fertilize", "irrigate", "cool", "warm", "barrier", "introduce"]).toContain(k);
    expect(INTERVENTIONS.every((i) => (i.cost.actionPoints ?? 0) >= 1)).toBe(true); // never a free choice
  });
  it("has the 57 loci of Appendix A with their labels", () => {
    expect(GENES.length).toBe(57);
    expect(GENES.find((g) => g.id === "mobility")!.labelPt).toBe("Mobilidade (0 = séssil)");
    expect(GENES.filter((g) => g.block === "MET").length).toBe(11); expect(GENES.filter((g) => g.block === "BEH").length).toBe(11);
  });
  it("the tutor cites a concrete datum, asks first and gives a chain and a next step", () => {
    const e = engine(), f = e.frameAt(15100), a = answerQuestion("species", f, e.frameAt(14500));
    expect(t(a.dataKey, a.dataParams)).toMatch(/\d+ linhagens vivas/); expect(t(a.promptKey)).toMatch(/\?$/); expect(a.chain.length).toBeGreaterThanOrEqual(3); expect(hasKey(a.nextKey)).toBe(true);
    for (const q of ["o2", "temperature", "species", "next"] as const) for (const tick of [100, 3000, 5000, 12900, 14500, 15100]) { const x = answerQuestion(q, e.frameAt(tick), null); for (const k of [x.dataKey, x.promptKey, x.nextKey, ...x.chain]) expect(hasKey(k), k).toBe(true); }
  });
});

describe("exports (RF-066)", () => {
  it("writes CSV for pt-BR spreadsheets and a structurally valid PDF", () => {
    expect(toCsv(["a", "b"], [["x;y", 1.5]])).toBe('﻿a;b\r\n"x;y";1,5');
    const pdf = new TextDecoder("latin1").decode(buildPdf("Relatório", ["# Seção", "Linha com acentuação: ção", ...Array.from({ length: 90 }, (_, i) => `linha ${i}`)]));
    expect(pdf.startsWith("%PDF-1.4")).toBe(true); expect(pdf.trimEnd().endsWith("%%EOF")).toBe(true); expect((pdf.match(/\/Type \/Page /g) ?? []).length).toBe(2);
    const xref = Number(pdf.match(/startxref\n(\d+)/)![1]); expect(pdf.slice(xref, xref + 4)).toBe("xref");
  });
});

describe("i18n (RNF-026)", () => {
  const src = path.resolve(__dirname, "../..");
  const files: string[] = [];
  (function walk(d: string) { for (const f of fs.readdirSync(d)) { const p = path.join(d, f); if (fs.statSync(p).isDirectory()) walk(p); else if (/\.(ts|tsx)$/.test(f) && !p.includes("/messages/") && !p.includes("__tests__")) files.push(p); } })(src);
  const code = files.map((f) => fs.readFileSync(f, "utf8")).join("\n");
  it("every literal key used in the code exists in pt-BR", () => {
    const used = new Set<string>();
    for (const m of code.matchAll(/(?:\bt\(|\bk=|titleKey=|Key: |labelKey: |key: )"([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)"/g)) used.add(m[1]);
    for (const m of code.matchAll(/"((?:ped|diary|notice)\.[a-zA-Z0-9_.]+)"/g)) used.add(m[1]);
    const missing = [...used].filter((k) => !hasKey(k));
    expect(missing, `missing keys: ${missing.join(", ")}`).toEqual([]);
    expect(used.size).toBeGreaterThan(400);
  });
  it("dynamic key families are complete", () => {
    const families: [string, string[]][] = [["era", "123456789".split("").map((n) => `${n}.name`)], ["event", ["fire", "drought", "storm", "glaciation", "volcanism", "impact", "eutrophication", "pandemic", "invasive"].map((e) => `${e}.name`)],
      ["biome", Array.from({ length: 13 }, (_, i) => String(i))], ["archetype", ["molten", "airless", "greenhouse", "snowball", "desert", "ocean", "archipelago", "temperate", "postExtinction", "primordial"]],
      ["intervention", INTERVENTIONS.map((i) => `${i.id}.name`)], ["ped.intervention", INTERVENTIONS.flatMap((i) => [`${i.id}.gain`, `${i.id}.side`])], ["cause", ["STARVATION", "SENESCENCE", "PREDATION", "ENVIRONMENTAL"]], ["stage", ["PROPAGULE", "JUVENILE", "ADULT", "SENESCENT", "DEAD"]]];
    for (const [prefix, keys] of families) for (const k of keys) expect(hasKey(`${prefix}.${k}`), `${prefix}.${k}`).toBe(true);
  });
  it("no user-facing Portuguese sentence is hard-coded in components", () => {
    const offenders: string[] = [];
    for (const f of files.filter((x) => x.endsWith(".tsx"))) for (const m of fs.readFileSync(f, "utf8").matchAll(/>\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?: [a-záéíóúâêôãõçA-Z]+){2,})\s*</g)) offenders.push(`${path.basename(f)}: ${m[1]}`);
    expect(offenders).toEqual([]);
    expect(allKeys().length).toBeGreaterThan(700);
  });
});
