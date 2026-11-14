// Contact sheet: node scripts/sheet.mjs <out.png> <cols> <width> <height> "label=url" ...
// Captures each URL and composes one labeled image, so a person can look at many states at once.
import sharp from "sharp";
import { launch, openPlanet } from "./browser.mjs";
const [out, colsArg, wArg, hArg, ...items] = process.argv.slice(2);
const cols = +colsArg, w = +wArg, h = +hArg, pad = 26;
const browser = await launch();
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
const tiles = [];
let allErrors = 0;
for (const item of items) {
  const k = item.indexOf("="), label = item.slice(0, k), url = item.slice(k + 1);
  const errors = await openPlanet(page, url, { settle: +(process.env.SETTLE ?? 900) });
  allErrors += errors.length;
  if (errors.length) console.log(`[${label}] console errors:`, errors.slice(0, 3));
  tiles.push({ label, png: await page.screenshot() });
}
await browser.close();
const rows = Math.ceil(tiles.length / cols);
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const composite = [];
tiles.forEach((t, i) => {
  const x = (i % cols) * w, y = Math.floor(i / cols) * (h + pad);
  composite.push({ input: t.png, left: x, top: y + pad });
  composite.push({ input: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${pad}"><rect width="100%" height="100%" fill="#10141f"/><text x="8" y="18" font-family="sans-serif" font-size="14" fill="#fff">${esc(t.label)}</text></svg>`), left: x, top: y });
});
await sharp({ create: { width: cols * w, height: rows * (h + pad), channels: 3, background: "#000" } }).composite(composite).png().toFile(out);
console.log(`${out}: ${tiles.length} tiles, ${allErrors} console errors`);
