import type { SeriesHistory } from "../state/types";
import type { PlanetStateSource, SourceInfo, SourceMessage } from "./port";

/**
 * TODO(contract): SKETCH ONLY, intentionally not implemented. There is no backend and no contract yet.
 *
 * When the contracts exist, this class will:
 *  1. open whatever connection the platform decides (not chosen here) and authenticate with the real session;
 *  2. map the engine's cell order to core/mesh/cellOrder.ts (identity if the orders match, a permutation otherwise);
 *  3. translate continuous fields ("Canal A") into PlanetFrame.fields/globals, reusing unchanged arrays by reference;
 *  4. translate domain events ("Canal B") into PlanetFrame.events, bio.flags and timeline marks;
 *  5. translate observer (M7) outputs into PlanetFrame.bio and SeriesHistory;
 *  6. run derive steps that are purely visual (biome class, ice, cloud) in a worker if the engine does not send them;
 *  7. send student commands (environment-level only, spec §20.5) and reconcile optimistic visual feedback.
 * The list of what the interface needs is in docs/frontend/NECESSIDADES_DE_DADOS.md.
 */
export class BackendSource implements PlanetStateSource {
  readonly kind = "backend" as const;
  start(): Promise<SourceInfo> { return Promise.reject(new Error("BackendSource is not implemented: there is no data contract yet.")); }
  subscribe(_listener: (m: SourceMessage) => void) { return () => {}; }
  setClock() {} seek() {} runUntil() {} dispatch() {} dispose() {}
  getHistory(): Promise<SeriesHistory> { return Promise.reject(new Error("not implemented")); }
}
