/** Game rules, session resume and the data source: the area where the independent reviews found defects. */
import fs from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { SyntheticSource } from "../source/SyntheticSource";
import { SyntheticEngine } from "../source/synthetic/engine";
import { GENES } from "../state/catalogs";
import type { PlanetFrame } from "../state/types";
import { directionOf, isViewingPast, readVariable, resetGameRules, useGameStore } from "@/store/gameStore";
import { usePlanetStore } from "@/store/planetStore";

const engine = new SyntheticEngine({ scenarioId: "genesis", level: 3 });
const at = (tick: number): PlanetFrame => engine.frameAt(tick);
const fresh = () => {
  resetGameRules();
  useGameStore.setState({ started: true, hydrated: true, resources: { actionPoints: 1, energy: 5, budget: 5, research: 0, influence: 0, naturalResources: 100 }, notices: [], diary: [], known: [], missionsDone: [], achievements: [], predictions: [], collapsed: false, cooldowns: {}, scans: [], commands: [] });
};
const show = (f: PlanetFrame) => { usePlanetStore.setState({ frame: f, maxTick: Math.max(usePlanetStore.getState().maxTick, f.tick), status: "ready" }); useGameStore.getState().onFrame(f); };

describe("game rules only move forward in time", () => {
  beforeEach(() => { usePlanetStore.setState({ maxTick: 0, frame: null }); fresh(); });
  it("a new era refills action points once; scrubbing across the boundary again gives nothing", () => {
    show(at(5900)); show(at(5990)); show(at(6010));
    const once = { ...useGameStore.getState().resources }, diary = useGameStore.getState().diary.length;
    expect(once.actionPoints).toBe(5);
    useGameStore.setState({ resources: { ...once, actionPoints: 0 } });
    for (let i = 0; i < 3; i++) { show(at(5900)); show(at(6010)); }
    expect(useGameStore.getState().resources.actionPoints).toBe(0);
    expect(useGameStore.getState().resources.research).toBe(once.research);
    expect(useGameStore.getState().diary.length).toBe(diary);
  });
  it("the student cannot act while looking at the past", () => {
    show(at(12600)); show(at(12000));
    expect(isViewingPast()).toBe(true);
    useGameStore.setState({ resources: { ...useGameStore.getState().resources, actionPoints: 5 } });
    expect(useGameStore.getState().apply("scan", { cell: 10 })).toBe(false);
    show(at(12600));
    expect(isViewingPast()).toBe(false);
    expect(useGameStore.getState().apply("scan", { cell: 10 })).toBe(true);
  });
  it("resuming a saved game (first frame at the saved moment) does not refill resources, even early in the game", () => {
    show(at(1000)); // what a reload does now: the source starts at the saved tick
    const r = useGameStore.getState().resources;
    expect(r.energy).toBe(5); expect(r.budget).toBe(5); expect(r.actionPoints).toBe(1);
    show(at(0)); show(at(1000)); // replaying saved commands seeks back and forth: still nothing
    expect(useGameStore.getState().resources.energy).toBe(5);
  });
  it("a long jump catches the state up without era rewards or a backlog of notices", () => {
    show(at(100)); show(at(12600));
    const g = useGameStore.getState();
    expect(g.resources.actionPoints).toBe(1); expect(g.known.length).toBeGreaterThan(10); expect(g.notices.filter((n) => n.key === "notice.newLineage").length).toBe(0);
  });
  it("time played regenerates energy a little", () => { show(at(12000)); show(at(12240)); expect(useGameStore.getState().resources.energy).toBeGreaterThan(5); expect(useGameStore.getState().resources.energy).toBeLessThan(60); });
});

describe("predictions", () => {
  it("temperature uses an absolute threshold: a 2 °C drop is a drop", () => {
    expect(directionOf("temperature", 288.15, 286.0)).toBe("down"); expect(directionOf("temperature", 288.15, 288.4)).toBe("same"); expect(directionOf("temperature", 288.15, 289.0)).toBe("up");
    expect(directionOf("co2", 400, 405)).toBe("same"); expect(directionOf("co2", 400, 420)).toBe("up");
  });
  it("cooling and warming the climate are observable 20 years later, in an early and in a late era", () => {
    for (const tick of [2500, 7000, 12600]) for (const [kind, want] of [["cool", "down"], ["warm", "up"]] as const) {
      const e = new SyntheticEngine({ scenarioId: "genesis", level: 3 }), before = readVariable(e.frameAt(tick), "temperature", null);
      e.addModifier({ id: "m", kind, tick });
      expect(directionOf("temperature", before, readVariable(e.frameAt(tick + 240), "temperature", null)), `${kind} at ${tick}`).toBe(want);
    }
  });
});

describe("synthetic source: start() while a frame is in flight", () => {
  it("drops the frame of the previous planet and shows the new planet at its own start", async () => {
    const src = new SyntheticSource(false), ticks: number[] = [], clock: boolean[] = [];
    src.subscribe((m) => { if (m.type === "frame") ticks.push(m.frame.tick); if (m.type === "clock") clock.push(m.playing); });
    await src.start({ scenarioId: "genesis", level: 3, startTick: 17000 });
    await new Promise((r) => setTimeout(r, 20));
    src.setClock(true, 12, "normal");
    src.seek(16000);                                                    // a frame of the old planet is now in flight
    const info = await src.start({ scenarioId: "genesis", level: 3 }); // the game starts
    await new Promise((r) => setTimeout(r, 60));
    expect(info.startTick).toBe(0);
    expect(ticks[ticks.length - 1]).toBe(0);
    expect(ticks.filter((t, i) => i > ticks.lastIndexOf(17000) && t !== 16000 && t !== 0)).toEqual([]);
    expect(clock[clock.length - 1]).toBe(false);                       // the interface was told the clock stopped
    src.dispose();
  });
  it("two start() calls in a row both resolve, in order", async () => {
    const src = new SyntheticSource(false);
    const [a, b] = await Promise.all([src.start({ scenarioId: "gradient", level: 3 }), src.start({ scenarioId: "catastrophe", level: 3 })]);
    expect([a.scenarioId, b.scenarioId]).toEqual(["gradient", "catastrophe"]);
    src.dispose();
  });
});

describe("gene catalog against the briefing (Appendix A)", () => {
  it("every one of the 57 genes has exactly the label of docs/frontend/BRIEFING.md section 4", () => {
    const md = fs.readFileSync(path.resolve(__dirname, "../../../../../docs/frontend/BRIEFING.md"), "utf8");
    const section = md.slice(md.indexOf("## 4. Catálogo de genes"), md.indexOf("## 5. Eventos"));
    const fromBriefing = new Map<string, string>();
    for (const m of section.matchAll(/^\| `([a-z_0-9]+)` \|(.+)\|\s*$/gm)) { const cells = m[2].split("|").map((c) => c.trim()); fromBriefing.set(m[1], cells[cells.length - 1]); }
    expect(fromBriefing.size).toBe(57);
    expect(Object.fromEntries(GENES.map((g) => [g.id, g.labelPt]))).toEqual(Object.fromEntries(fromBriefing));
  });
});
