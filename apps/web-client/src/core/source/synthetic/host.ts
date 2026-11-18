/**
 * Host of the synthetic engine: owns the clock and answers requests. Runs inside a Web Worker when one is
 * available, or inline (tests, fallback). The protocol below is private to the SyntheticSource; it is not a contract.
 */
import type { PlanetFrame, SeriesHistory, UpdateMode } from "../../state/types";
import type { SourceCommand, SourceConfig, SourceInfo } from "../port";
import { SyntheticEngine } from "./engine";

export type HostRequest =
  | { op: "start"; config: SourceConfig }
  | { op: "frame"; tick: number; mode: UpdateMode; annualMean: boolean; seq: number }
  | { op: "command"; command: SourceCommand; tick: number }
  | { op: "history"; from: number; to: number; samples: number; id: number };
export type HostResponse =
  | { op: "started"; info: SourceInfo }
  | { op: "frame"; frame: PlanetFrame; seq: number; versions: { terrain: number; water: number }; stripped: string[] }
  | { op: "history"; id: number; history: SeriesHistory }
  | { op: "error"; detail: string };

export class SyntheticHost {
  private engine: SyntheticEngine | null = null;
  private sent = { terrain: -1, water: -1 };
  constructor(private post: (r: HostResponse, transfer?: Transferable[]) => void, private stripStatic: boolean) {}

  handle(req: HostRequest) {
    try {
      if (req.op === "start") {
        this.engine = new SyntheticEngine(req.config);
        this.sent = { terrain: -1, water: -1 };
        const s = this.engine.scenario;
        this.post({ op: "started", info: { kind: "synthetic", synthetic: true, scenarioId: s.id, level: req.config.level, startTick: s.eras[0].start, endTick: s.endTick, eras: s.eras } });
        return;
      }
      const e = this.engine;
      if (!e) return;
      if (req.op === "frame") {
        const frame = e.frameAt(req.tick, req.mode, req.annualMean);
        const stripped: string[] = [];
        const versions = { ...e.versions };
        if (this.stripStatic) {
          // Arrays that did not change since the last message are not copied again; the main thread keeps them.
          const f = frame.fields as unknown as Record<string, unknown>;
          if (versions.terrain === this.sent.terrain) { f.elevation = null; stripped.push("elevation"); }
          if (versions.water === this.sent.water && versions.terrain === this.sent.terrain) { f.isWater = null; stripped.push("isWater"); }
          this.sent = versions;
        }
        this.post({ op: "frame", frame, seq: req.seq, versions, stripped });
      } else if (req.op === "command") {
        const c = req.command;
        if (c.type === "intervene") e.addModifier({ id: c.id, kind: c.kind, tick: req.tick, cell: c.cell, eventType: c.eventType, eventId: c.eventId, role: c.role, noTelegraph: c.noTelegraph });
        else if (c.type === "setParams") e.setParams(c.params);
        else if (c.type === "setOverrides") e.setOverrides(c.overrides);
        else if (c.type === "observeLineage") e.observedLineage = c.id;
      } else if (req.op === "history") {
        this.post({ op: "history", id: req.id, history: e.history(req.from, req.to, req.samples) });
      }
    } catch (err) {
      this.post({ op: "error", detail: err instanceof Error ? err.message : String(err) });
    }
  }
}
