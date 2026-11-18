// Generates the bundled fixture: `pnpm fixture`. Kept small (mesh level 3) because it ships with the app shell.
import fs from "node:fs";
import path from "node:path";
import { it } from "vitest";
import { exportFixture } from "../src/core/source/FixtureSource";
import { SyntheticEngine } from "../src/core/source/synthetic/engine";

it("writes public/fixtures/terra-nivel3.json", () => {
  const e = new SyntheticEngine({ scenarioId: "genesis", level: 3 });
  const frames = [150, 12900, 15100].map((t) => e.frameAt(t));
  const out = path.resolve(__dirname, "../public/fixtures/terra-nivel3.json");
  fs.writeFileSync(out, exportFixture(frames, "Gênese, nível 3, três instantâneos. Dados sintéticos, apenas para desenvolvimento."));
  console.log(`${out}: ${(fs.statSync(out).size / 1024).toFixed(0)} KiB`);
});
