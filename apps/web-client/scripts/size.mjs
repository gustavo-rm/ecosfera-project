// Bundle size check with a documented budget. Usage: BASE_URL=http://localhost:3100 node scripts/size.mjs (against `next start`).
// Measures the compressed bytes actually transferred for JS and CSS on first load of each route.
import { BASE, launch } from "./browser.mjs";
/** Budgets in KiB (compressed transfer), first load. See docs/frontend/relatorios/desempenho.md. */
const BUDGET = { "/": 640, "/jogo": 520, "/jogo/dados": 620, "/professor": 330 }; // "/" prefetches the game, so it carries the game chunks
const browser = await launch();
let fail = 0;
for (const [route, budget] of Object.entries(BUDGET)) {
  const page = await browser.newPage(), sizes = { js: 0, css: 0, font: 0, other: 0 };
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  const types = new Map();
  cdp.on("Network.responseReceived", (e) => types.set(e.requestId, e.type));
  cdp.on("Network.loadingFinished", (e) => { const t = types.get(e.requestId); sizes[t === "Script" ? "js" : t === "Stylesheet" ? "css" : t === "Font" ? "font" : "other"] += e.encodedDataLength; });
  await page.goto(`${BASE}${route}?dev=0`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const kib = (v) => (v / 1024).toFixed(0), total = (sizes.js + sizes.css) / 1024, ok = total <= budget;
  if (!ok) fail++;
  console.log(`${ok ? "ok  " : "FAIL"} ${route.padEnd(14)} JS ${kib(sizes.js)} KiB · CSS ${kib(sizes.css)} KiB · fontes ${kib(sizes.font)} KiB · outros ${kib(sizes.other)} KiB · JS+CSS ${total.toFixed(0)} / limite ${budget} KiB`);
  await page.close();
}
await browser.close();
process.exit(fail ? 1 : 0);
