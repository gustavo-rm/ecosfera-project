// Shared Playwright launcher. Headless Chromium has no GPU here, so WebGL runs on SwiftShader (software):
// a pessimistic floor for performance and a faithful renderer for images.
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); } catch { pw = require("/opt/node-tools/node_modules/playwright"); }
export const { chromium } = pw;
export const BASE = process.env.BASE_URL ?? "http://localhost:3000";
export async function launch() {
  return chromium.launch({ args: ["--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"] });
}
/** Opens a page and waits until the planet has a frame on screen. Returns console errors collected. */
export async function openPlanet(page, url, { settle = 900 } = {}) {
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + url, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-status="ready"]', { timeout: 90000 });
  await page.waitForSelector("canvas", { timeout: 30000 });
  await page.waitForTimeout(settle);
  return errors;
}
