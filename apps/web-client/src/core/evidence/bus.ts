/**
 * Local bus of typed evidence events (section 9.7). NOTHING IS SENT ANYWHERE: there is no transport and no contract yet.
 * Events carry no personal data: no name, no account id, no free text typed by the student (only its length).
 * The list of events and fields is mirrored in docs/frontend/NECESSIDADES_DE_DADOS.md, section H.
 */
export type EvidenceEvent =
  | { type: "prediction_declared"; interventionId: string; variable: string; direction: "up" | "down" | "same" }
  | { type: "prediction_compared"; interventionId: string; variable: string; predicted: "up" | "down" | "same"; observed: "up" | "down" | "same"; match: boolean }
  | { type: "panel_opened"; panel: string; ticksSinceLastAction: number }
  | { type: "chart_opened"; chart: string; ticksSinceLastAction: number }
  | { type: "layer_viewed"; layer: string }
  | { type: "decision_time"; interventionId: string; seconds: number; consulted: string[] }
  | { type: "intervention_applied"; interventionId: string; hadPrediction: boolean }
  | { type: "param_explored"; param: string; changes: number }
  | { type: "collapse_recovered"; scenarioId: string; attempts: number }
  | { type: "reflection_answered"; questionId: string; length: number }
  | { type: "mission_goal_met"; missionId: string }
  | { type: "species_inspected"; lineageId: string }
  | { type: "tutor_question"; questionId: string }
  | { type: "timeline_scrubbed"; fromTick: number; toTick: number }
  | { type: "scan_done"; cells: number };
export type EvidenceRecord = EvidenceEvent & { seq: number; tick: number; era: number };

type Listener = (r: EvidenceRecord) => void;
const listeners = new Set<Listener>();
const log: EvidenceRecord[] = [];
let seq = 0;
let context = { tick: 0, era: 1 };
export const evidence = {
  setContext(tick: number, era: number) { context = { tick, era }; },
  emit(e: EvidenceEvent) {
    const r = { ...e, seq: ++seq, tick: context.tick, era: context.era } as EvidenceRecord;
    log.push(r);
    if (log.length > 500) log.shift();
    listeners.forEach((l) => l(r));
  },
  subscribe(l: Listener) { listeners.add(l); return () => { listeners.delete(l); }; },
  all: () => log.slice(),
  clear() { log.length = 0; },
};
