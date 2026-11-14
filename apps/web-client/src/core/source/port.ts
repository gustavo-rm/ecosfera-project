/**
 * Data source port. THE ONLY BOUNDARY through which planet data enters the frontend.
 *
 * TODO(contract): when the backend exists, only an implementation of this port changes (BackendSource).
 * The port speaks the frontend's internal visual state (PlanetFrame). A future BackendSource must TRANSLATE
 * whatever transport and message formats are agreed (not defined here) into PlanetFrame and SourceMessage:
 *   - "Canal A" (continuous world fields, floating point)  -> PlanetFrame.fields / globals
 *   - "Canal B" (discrete domain events)                    -> PlanetFrame.events, bio.flags, timeline marks
 *   - observer (M7) read-only outputs                       -> PlanetFrame.bio and SeriesHistory
 *   - student commands                                      -> whatever the engine accepts for §20.5 actions
 * See docs/frontend/NECESSIDADES_DE_DADOS.md. Nothing in this file is a wire format.
 */
import type { EventType, PlanetFrame, PlanetParams, SeriesHistory, TrophicRole, UpdateMode } from "../state/types";
import type { ModifierKind, StateOverrides } from "./synthetic/engine";

export interface SourceInfo { kind: "synthetic" | "fixture" | "backend"; synthetic: boolean; scenarioId: string; level: number; startTick: number; endTick: number; eras: { era: number; start: number }[] }

export type SourceMessage =
  | { type: "ready"; info: SourceInfo }
  | { type: "frame"; frame: PlanetFrame }
  | { type: "clock"; playing: boolean; speed: number; mode: UpdateMode }
  | { type: "error"; messageKey: string; detail?: string };

/** Things the student (or the lab) can do. Only environment-level actions exist (spec §20.5): no genome editing. */
export type SourceCommand =
  | { type: "intervene"; id: string; kind: ModifierKind; cell?: number; eventType?: EventType; eventId?: string; role?: TrophicRole; noTelegraph?: boolean }
  | { type: "setParams"; params: Partial<PlanetParams> }
  | { type: "setOverrides"; overrides: StateOverrides }
  | { type: "observeLineage"; id: string | null };

export interface SourceConfig { scenarioId: string; level: number; seed?: number; params?: Partial<PlanetParams>; startTick?: number }

export interface PlanetStateSource {
  readonly kind: SourceInfo["kind"];
  start(config: SourceConfig): Promise<SourceInfo>;
  subscribe(listener: (msg: SourceMessage) => void): () => void;
  /** speed is in ticks (simulated months) per second. */
  setClock(playing: boolean, speed: number, mode: UpdateMode): void;
  seek(tick: number): void;
  /** Play in fast mode until the tick, then pause. */
  runUntil(tick: number): void;
  dispatch(command: SourceCommand): void;
  getHistory(fromTick: number, toTick: number, samples: number): Promise<SeriesHistory>;
  dispose(): void;
}
