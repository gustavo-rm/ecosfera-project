// Frame-time measurement under CPU throttling (CDP) on software WebGL (SwiftShader).
// Software WebGL is a PESSIMISTIC FLOOR, not a Chromebook. Writes docs/frontend/relatorios/desempenho-medidas.md.
// Usage: BASE_URL=http://localhost:3100 node scripts/perf.mjs
import fs from "node:fs";
import path from "node:path";
import { BASE, launch } from "./browser.mjs";
const out = path.resolve(import.meta.dirname, "../../../docs/frontend/relatorios");
fs.mkdirSync(out, { recursive: true });
const CASES = (process.env.CASES ?? "low,medium,high").split(","), THROTTLE = (process.env.THROTTLE ?? "1,4").split(",").map(Number);
const VIEWS = [["planeta inteiro", ""], ["zoom com organismos", "&zoom=0.42"], ["camada de temperatura", "&camada=temperature"]];
const SIZES = (process.env.SIZES ?? "1366x768,683x384").split(",");
const browser = await launch();
const rows = [];
for (const size of SIZES) for (const quality of CASES) for (const rate of THROTTLE) for (const [view, q] of VIEWS) {
  if (size !== SIZES[0] && (rate !== THROTTLE[0] || view !== VIEWS[0][0])) continue;
  const [w, h] = size.split("x").map(Number);
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const cdp = await page.context().newCDPSession(page);
  await page.goto(`${BASE}/lab/planeta?preset=terra&qualidade=${quality}&tocar=1&velocidade=12${q}`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-status="ready"]', { timeout: 90000 }); await page.waitForSelector("canvas");
  await page.waitForTimeout(2500);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate });
  const r = await page.evaluate(() => new Promise((resolve) => {
    const times = []; let last = performance.now(); const start = last;
    const tick = (now) => { times.push(now - last); last = now; if (now - start < 6000 && times.length < 600) requestAnimationFrame(tick); else { times.shift(); times.sort((a, b) => a - b); resolve({ n: times.length, mean: times.reduce((a, b) => a + b, 0) / times.length, median: times[Math.floor(times.length / 2)], p95: times[Math.min(times.length - 1, Math.floor(times.length * 0.95))] }); } };
    requestAnimationFrame(tick);
  }));
  const gl = await page.evaluate(() => { const c = document.createElement("canvas").getContext("webgl2"); const e = c?.getExtension("WEBGL_debug_renderer_info"); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : "?"; });
  rows.push({ size, quality, rate, view, ...r, gl });
  console.log(`${size} ${quality.padEnd(6)} CPU ${rate}× ${view.padEnd(24)} média ${r.mean.toFixed(1)} ms (${(1000 / r.mean).toFixed(1)} FPS) mediana ${r.median.toFixed(1)} p95 ${r.p95.toFixed(1)} n=${r.n}`);
  await page.close();
}
// Automatic governor: start at medium, let it adapt for 25 s, then measure what the student would actually get.
for (const rate of THROTTLE) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1 });
  const cdp = await page.context().newCDPSession(page);
  await page.goto(`${BASE}/lab/planeta?preset=terra&qualidade=medium&auto=1&tocar=1&velocidade=12`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-status="ready"]', { timeout: 90000 }); await page.waitForSelector("canvas");
  await cdp.send("Emulation.setCPUThrottlingRate", { rate });
  await page.waitForTimeout(25000);
  const r = await page.evaluate(() => new Promise((resolve) => {
    const times = []; let last = performance.now(); const start = last;
    const tick = (now) => { times.push(now - last); last = now; if (now - start < 6000) requestAnimationFrame(tick); else { times.shift(); times.sort((a, b) => a - b); const c = document.querySelector("canvas"); resolve({ n: times.length, mean: times.reduce((a, b) => a + b, 0) / times.length, median: times[Math.floor(times.length / 2)], p95: times[Math.floor(times.length * 0.95)], quality: document.querySelector("[data-quality]").getAttribute("data-quality"), buffer: `${c.width}×${c.height}` }); } };
    requestAnimationFrame(tick);
  }));
  rows.push({ size: "1366x768", quality: `automática → ${r.quality}, buffer ${r.buffer}`, rate, view: "planeta inteiro, após 25 s", ...r, gl: rows[0]?.gl });
  console.log(`auto CPU ${rate}×: chegou a ${r.quality}, buffer ${r.buffer}, média ${r.mean.toFixed(1)} ms (${(1000 / r.mean).toFixed(1)} FPS) p95 ${r.p95.toFixed(1)}`);
  await page.close();
}
await browser.close();
const md = ["# Medidas de tempo de quadro", "", `Geradas por \`scripts/perf.mjs\` em ${new Date().toISOString().slice(0, 10)}. Renderizador: ${rows[0]?.gl}. Máquina: ${(await import("node:os")).cpus().length} núcleos, sem GPU.`, "",
  "| Janela | Qualidade | Limitação de CPU | Vista | Quadro médio (ms) | FPS médio | Mediana (ms) | p95 (ms) |", "|---|---|---|---|---|---|---|---|",
  ...rows.map((r) => `| ${r.size} | ${r.quality} | ${r.rate}× | ${r.view} | ${r.mean.toFixed(1)} | ${(1000 / r.mean).toFixed(1)} | ${r.median.toFixed(1)} | ${r.p95.toFixed(1)} |`), ""];
fs.writeFileSync(path.join(out, "desempenho-medidas.md"), md.join("\n"));
