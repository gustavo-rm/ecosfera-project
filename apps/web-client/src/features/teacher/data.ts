/**
 * Simulated data for the teacher, coordination and guardian panels. EVERYTHING HERE IS FICTITIOUS:
 * names are invented, students are pseudonymized by code, numbers come from a seeded generator.
 * The shape follows the Dossiê (pedagogical model §11, ERS §4.5); it is not a contract.
 */
import { create } from "zustand";
import { hash4, mulberry32 } from "@/core/math/rng";

export const COMPETENCIES = ["scientific", "causeEffect", "systemic", "decision", "consequences", "dataLiteracy", "evolution", "persistence", "creativity", "argumentation"] as const;
export type Competency = (typeof COMPETENCIES)[number];
export const BNCC_SKILLS = ["EF06CI11", "EF06CI14", "EF07CI07", "EF07CI08", "EF07CI13", "EF08CI14", "EF08CI15", "EF08CI16", "EF09CI11", "EF09CI14", "EF09CI16", "EM13CNT201", "EM13CNT203", "EM13CNT301", "EM13CNT302"] as const;
export type Track = "fundamental" | "medio" | "tecnico";
export type Consent = "granted" | "pending" | "denied";
export interface EvidenceItem { id: string; competency: Competency; kind: string; era: number; year: number; action: string; week: number }
export interface Student {
  id: string; code: string; nickname: string; classId: string; consent: Consent; restrictions: string[];
  scores: Record<Competency, number>; history: number[]; evidence: EvidenceItem[]; stuckTopic: string | null; engagement: number;
  planet: { scenarioId: string; seed: number; tick: number }; decisions: { year: number; action: string; hadPrediction: boolean }[];
}
export interface SchoolClass { id: string; name: string; track: Track; grade: string }
export interface Recommendation { id: string; classId: string; studentId: string | null; text: string; topic: string; status: "open" | "edited" | "dismissed" | "accepted" }
export interface Challenge { id: string; title: string; skill: string; scenarioId: string; orbitAU: number; waterFraction: number; maxActions: number; blocked: string[]; metric: string; threshold: number; classId: string; createdAt: number }
export interface Message { id: string; studentId: string; text: string; at: number }

const NAMES = ["Ana", "Beto", "Caio", "Duda", "Enzo", "Fabi", "Gil", "Helô", "Igor", "Jade", "Kauã", "Lia", "Malu", "Nico", "Olga", "Pedro", "Quésia", "Rui", "Sara", "Téo", "Uli", "Vitor", "Wanda", "Yuri"];
const TOPICS = ["feedbackClimatico", "efeitoEstufa", "cadeiasTroficas", "cicloDaAgua", "especiacao", "decomposicao"];
const ACTIONS = ["scan", "reforest", "irrigate", "fertilize", "cool", "trigger", "barrier", "introduce"];
const KINDS = ["prediction_compared", "chart_opened", "decision_time", "collapse_recovered", "reflection_answered", "param_explored", "mission_goal_met"];
export const CLASSES: SchoolClass[] = [
  { id: "c7b", name: "7º B", track: "fundamental", grade: "7º ano" }, { id: "c8a", name: "8º A", track: "fundamental", grade: "8º ano" },
  { id: "c1m", name: "1º EM A", track: "medio", grade: "1ª série" }, { id: "ct1", name: "Técnico em Meio Ambiente 1", track: "tecnico", grade: "Módulo 1" },
];
const SCENARIOS = ["genesis", "gradient", "archipelago", "catastrophe", "noDecomposers"];

function makeStudents(): Student[] {
  const out: Student[] = [];
  CLASSES.forEach((c, ci) => {
    const rng = mulberry32(100 + ci * 17), n = 10 + Math.floor(rng() * 4);
    for (let i = 0; i < n; i++) {
      const base = 0.35 + rng() * 0.45, scores = {} as Record<Competency, number>;
      COMPETENCIES.forEach((k, ki) => { scores[k] = Math.min(1, Math.max(0.05, base + (rng() - 0.5) * 0.4 + (k === "systemic" ? -0.12 : 0) + (ki === 0 ? 0.08 : 0))); });
      const consent: Consent = rng() < 0.78 ? "granted" : rng() < 0.6 ? "pending" : "denied";
      const stuck = scores.systemic < 0.38 ? TOPICS[0] : scores.causeEffect < 0.4 ? TOPICS[1] : rng() < 0.12 ? TOPICS[2 + Math.floor(rng() * 4)] : null;
      const evidence: EvidenceItem[] = Array.from({ length: 5 + Math.floor(rng() * 5) }, (_, e) => ({ id: `${c.id}-${i}-${e}`, competency: COMPETENCIES[Math.floor(rng() * COMPETENCIES.length)], kind: KINDS[Math.floor(rng() * KINDS.length)], era: 1 + Math.floor(rng() * 7), year: Math.floor(rng() * 1500), action: ACTIONS[Math.floor(rng() * ACTIONS.length)], week: Math.floor(rng() * 8) }));
      out.push({
        id: `${c.id}-s${i}`, code: `${c.id.toUpperCase()}-${String(i + 1).padStart(2, "0")}`, nickname: `${NAMES[(ci * 7 + i) % NAMES.length]} ${String.fromCharCode(65 + ((i * 5 + ci) % 20))}.`, classId: c.id, consent,
        restrictions: consent === "granted" ? (rng() < 0.15 ? ["noFreeText"] : []) : ["noCollection"], scores,
        history: Array.from({ length: 8 }, (_, w) => Math.min(1, Math.max(0, base - 0.14 + w * 0.02 + (hash4(ci, i, w, 3) - 0.5) * 0.08))), evidence, stuckTopic: stuck, engagement: 0.3 + rng() * 0.7,
        planet: { scenarioId: SCENARIOS[Math.floor(rng() * SCENARIOS.length)], seed: 1 + Math.floor(rng() * 90), tick: 2000 + Math.floor(rng() * 3600) },
        decisions: Array.from({ length: 4 + Math.floor(rng() * 5) }, () => ({ year: Math.floor(rng() * 450), action: ACTIONS[Math.floor(rng() * ACTIONS.length)], hadPrediction: rng() < 0.5 })).sort((a, b) => a.year - b.year),
      });
    }
  });
  return out;
}
export const STUDENTS = makeStudents();
/** Students without consent have no learning data collected (RNF-009): their analytics never enter any aggregate. */
export const visible = (s: Student) => s.consent === "granted";
export const studentsOf = (classId: string) => STUDENTS.filter((s) => s.classId === classId);
export const meanScore = (s: Student) => COMPETENCIES.reduce((a, k) => a + s.scores[k], 0) / COMPETENCIES.length;
export function classMeans(classId: string): Record<Competency, number> {
  const list = studentsOf(classId).filter(visible), out = {} as Record<Competency, number>;
  for (const k of COMPETENCIES) out[k] = list.length ? list.reduce((a, s) => a + s.scores[k], 0) / list.length : 0;
  return out;
}
export function classHistory(classId: string): number[] {
  const list = studentsOf(classId).filter(visible);
  return Array.from({ length: 8 }, (_, w) => (list.length ? list.reduce((a, s) => a + s.history[w], 0) / list.length : 0));
}
/** Evidence -> BNCC skill coverage (RF-076). PLACEHOLDER mapping. */
export function bnccCoverage(classId: string): { skill: string; coverage: number; evidences: number }[] {
  const list = studentsOf(classId).filter(visible);
  return BNCC_SKILLS.map((skill, i) => {
    const with_ = list.filter((s, si) => hash4(si, i, classId.length, 7) < 0.25 + meanScore(s) * 0.8).length;
    return { skill, coverage: list.length ? with_ / list.length : 0, evidences: with_ * (1 + (i % 3)) };
  });
}
export function alerts(classId: string, threshold: number) {
  return studentsOf(classId).filter(visible).filter((s) => s.stuckTopic && meanScore(s) < threshold + 0.25 || Math.min(...COMPETENCIES.map((k) => s.scores[k])) < threshold)
    .map((s) => { const worst = COMPETENCIES.reduce((a, k) => (s.scores[k] < s.scores[a] ? k : a), COMPETENCIES[0]); return { student: s, competency: worst, topic: s.stuckTopic ?? TOPICS[2] }; });
}
const seedRecs = (): Recommendation[] => CLASSES.flatMap((c) => {
  const al = alerts(c.id, 0.4);
  return [{ id: `r-${c.id}-0`, classId: c.id, studentId: null, text: "", topic: "efeitoEstufa", status: "open" as const }, ...al.slice(0, 3).map((a, i) => ({ id: `r-${c.id}-${i + 1}`, classId: c.id, studentId: a.student.id, text: "", topic: a.topic, status: "open" as const }))];
});

interface TeacherStore {
  classId: string; threshold: number; recommendations: Recommendation[]; challenges: Challenge[]; messages: Message[]; extraClasses: SchoolClass[]; tracks: Record<string, Track>; consentOverride: Record<string, Consent>;
  set(p: Partial<TeacherStore>): void; updateRec(id: string, p: Partial<Recommendation>): void;
}
export const useTeacher = create<TeacherStore>((set, get) => ({
  classId: "c7b", threshold: 0.4, recommendations: seedRecs(), challenges: [], messages: [], extraClasses: [], tracks: {}, consentOverride: {},
  set: (p) => set(p),
  updateRec: (id, p) => set({ recommendations: get().recommendations.map((r) => (r.id === id ? { ...r, ...p } : r)) }),
}));
