// Usage: node scripts/shot.mjs <out.png> "<url path>" [width] [height]
import { launch, openPlanet } from "./browser.mjs";
const [out, url, w = "900", h = "700"] = process.argv.slice(2);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
const errors = await openPlanet(page, url);
await page.screenshot({ path: out });
console.log(errors.length ? "console errors:\n" + errors.join("\n") : "no console errors");
await browser.close();
