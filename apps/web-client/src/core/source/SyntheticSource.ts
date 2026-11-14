import type { PlanetFrame, SeriesHistory, UpdateMode } from "../state/types";
import type { PlanetStateSource, SourceCommand, SourceConfig, SourceInfo, SourceMessage } from "./port";
import { SyntheticHost, type HostRequest, type HostResponse } from "./synthetic/host";

/** Above this speed (ticks per second) seasons would strobe, so the source reports annual means ("reduced" detail, §22.5). */
const SEASON_SPEED_LIMIT = 2;

/**
 * Deterministic synthetic data source. DEVELOPMENT ONLY: it is not the engine.
 * The clock lives here (main thread); frames are computed by the host in a worker.
 */
export class SyntheticSource implements PlanetStateSource {
  readonly kind = "synthetic" as const;
  private listeners = new Set<(m: SourceMessage) => void>();
  private worker: Worker | null = null;
  private inline: SyntheticHost | null = null;
  private info: SourceInfo | null = null;
  private tick = 0; private playing = false; private speed = 12; private mode: UpdateMode = "normal";
  private until: number | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private busy = false; private dirty = false; private seq = 0; private lastWall = 0;
  private cache: { elevation: Float32Array | null; isWater: Uint8Array | null } = { elevation: null, isWater: null };
  private pendingHistory = new Map<number, (h: SeriesHistory) => void>();
  private startResolve: ((i: SourceInfo) => void) | null = null;
  private historyId = 0;
  /** Frames per second requested while playing. */
  frameRate = 5;

  constructor(private useWorker = true) {}

  private send(req: HostRequest) {
    if (this.worker) this.worker.postMessage(req);
    else this.inline?.handle(req);
  }
  private onResponse = (r: HostResponse) => {
    if (r.op === "started") { this.info = r.info; this.startResolve?.(r.info); this.emit({ type: "ready", info: r.info }); }
    else if (r.op === "frame") {
      const f = r.frame.fields as unknown as Record<string, unknown>;
      if (f.elevation) this.cache.elevation = f.elevation as Float32Array; else f.elevation = this.cache.elevation;
      if (f.isWater) this.cache.isWater = f.isWater as Uint8Array; else f.isWater = this.cache.isWater;
      this.busy = false;
      if (r.seq === this.seq) this.emit({ type: "frame", frame: r.frame as PlanetFrame });
      if (this.dirty) { this.dirty = false; this.requestFrame(); }
    } else if (r.op === "history") { this.pendingHistory.get(r.id)?.(r.history); this.pendingHistory.delete(r.id); }
    else if (r.op === "error") { this.busy = false; this.emit({ type: "error", messageKey: "error.source", detail: r.detail }); }
  };
  private emit(m: SourceMessage) { this.listeners.forEach((l) => l(m)); }

  start(config: SourceConfig): Promise<SourceInfo> {
    if (!this.worker && !this.inline) {
      if (this.useWorker && typeof Worker !== "undefined") {
        try {
          this.worker = new Worker(new URL("./synthetic/synthetic.worker.ts", import.meta.url), { type: "module" });
          this.worker.onmessage = (ev: MessageEvent<HostResponse>) => this.onResponse(ev.data);
          this.worker.onerror = (ev) => this.emit({ type: "error", messageKey: "error.source", detail: ev.message });
        } catch { this.worker = null; }
      }
      if (!this.worker) this.inline = new SyntheticHost((r) => queueMicrotask(() => this.onResponse(r)), false);
    }
    this.cache = { elevation: null, isWater: null };
    this.busy = false; this.playing = false; this.until = null;
    return new Promise((resolve) => {
      this.startResolve = (info) => { this.tick = config.startTick ?? info.startTick; this.requestFrame(); resolve(info); };
      this.send({ op: "start", config });
    });
  }

  subscribe(listener: (m: SourceMessage) => void) { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; }

  private requestFrame() {
    if (this.busy) { this.dirty = true; return; }
    this.busy = true;
    const annual = this.playing && this.speed > SEASON_SPEED_LIMIT;
    this.send({ op: "frame", tick: Math.round(this.tick), mode: this.mode, annualMean: annual, seq: ++this.seq });
  }

  private step = () => {
    const now = performance.now(), dt = Math.min(0.5, (now - this.lastWall) / 1000);
    this.lastWall = now;
    if (!this.playing || !this.info) return;
    this.tick += dt * this.speed;
    const limit = this.until ?? this.info.endTick;
    if (this.tick >= limit) {
      this.tick = limit;
      this.setClock(false, this.until !== null ? 12 : this.speed, "normal");
      this.until = null;
    }
    this.requestFrame();
  };

  setClock(playing: boolean, speed: number, mode: UpdateMode) {
    this.playing = playing; this.speed = speed; this.mode = mode;
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (playing) { this.lastWall = performance.now(); this.timer = setInterval(this.step, 1000 / (mode === "fast" ? Math.max(2, this.frameRate / 2) : this.frameRate)); }
    this.emit({ type: "clock", playing, speed, mode });
    this.requestFrame();
  }
  seek(tick: number) { if (!this.info) return; this.tick = Math.max(this.info.startTick, Math.min(this.info.endTick, tick)); this.requestFrame(); }
  runUntil(tick: number) { this.until = tick; this.setClock(true, 480, "fast"); }
  dispatch(command: SourceCommand) { this.send({ op: "command", command, tick: Math.round(this.tick) }); this.requestFrame(); }
  getHistory(from: number, to: number, samples: number) {
    return new Promise<SeriesHistory>((resolve) => { const id = ++this.historyId; this.pendingHistory.set(id, resolve); this.send({ op: "history", from, to, samples, id }); });
  }
  dispose() { if (this.timer) clearInterval(this.timer); this.worker?.terminate(); this.worker = null; this.inline = null; this.listeners.clear(); }
}
