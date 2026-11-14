// UI contact sheet: node scripts/ui-sheet.mjs <out.png> <cols> <width> <height> "label=url[@@waitSelector]" ...
// Like sheet.mjs, but for any screen: waits for a selector (default [data-screen]) instead of the planet canvas.
import sharp from "sharp";
import { BASE, launch } from "./browser.mjs";
const [out, colsArg, wArg, hArg, ...items] = process.argv.slice(2);
const cols = +colsArg, w = +wArg, h = +hArg, pad = 26, scale = +(process.env.SCALE ?? 0.5);
const browser = await launch();
const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: process.env.TOUCH === "1" });
const tiles = [];
let total = 0;
for (const item of items) {
  const k = item.indexOf("="), label = item.slice(0, k);
  const [url, sel = "[data-screen]"] = item.slice(k + 1).split("@@");
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + url, { waitUntil: "domcontentloaded" });
  try { await page.waitForSelector(sel, { timeout: 60000 }); } catch { errors.push(`selector not found: ${sel}`); }
  await page.waitForTimeout(+(process.env.SETTLE ?? 2500));
  if (process.env.FULL === "1") await page.setViewportSize({ width: w, height: Math.min(4000, await page.evaluate(() => document.documentElement.scrollHeight)) });
  const png = await sharp(await page.screenshot()).resize({ width: Math.round(w * scale), height: Math.round(h * scale), fit: "cover", position: "top" }).png().toBuffer();
  total += errors.length;
  if (errors.length) console.log(`[${label}] console errors:`, errors.slice(0, 4));
  tiles.push({ label, png });
  await page.close();
}
await browser.close();
const tw = Math.round(w * scale), th = Math.round(h * scale), rows = Math.ceil(tiles.length / cols);
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const composite = [];
tiles.forEach((t, i) => {
  const x = (i % cols) * tw, y = Math.floor(i / cols) * (th + pad);
  composite.push({ input: t.png, left: x, top: y + pad });
  composite.push({ input: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${tw}" height="${pad}"><rect width="100%" height="100%" fill="#10141f"/><text x="8" y="18" font-family="sans-serif" font-size="14" fill="#fff">${esc(t.label)}</text></svg>`), left: x, top: y });
});
await sharp({ create: { width: cols * tw, height: rows * (th + pad), channels: 3, background: "#000" } }).composite(composite).png().toFile(out);
console.log(`${out}: ${tiles.length} tiles, ${total} console errors`);
