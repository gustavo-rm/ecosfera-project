// Lists i18n keys used in the source that are missing from the message files, and dynamic key templates.
import fs from "node:fs";
import path from "node:path";
const root = new URL("../src", import.meta.url).pathname;
const files = [];
(function walk(d) { for (const f of fs.readdirSync(d)) { const p = path.join(d, f); if (fs.statSync(p).isDirectory()) walk(p); else if (/\.(ts|tsx)$/.test(f) && !p.includes("/messages/") && !f.includes(".test.")) files.push(p); } })(root);
const literal = new Set(), dynamic = new Set();
for (const f of files) {
  const s = fs.readFileSync(f, "utf8");
  for (const m of s.matchAll(/(?:\bt\(|\bk=|[kK]ey: |Key: |labelKey: |dataKey: |promptKey: |nextKey: )"([a-zA-Z0-9_.]+)"/g)) literal.add(m[1]);
  for (const m of s.matchAll(/"((?:ped|diary|notice)\.[a-zA-Z0-9_.]+)"/g)) literal.add(m[1]);
  for (const m of s.matchAll(/(?:\bt\(|\bk=\{?)`([^`]+)`/g)) dynamic.add(m[1]);
}
const msgDir = path.join(root, "i18n/messages");
const have = new Set();
const text = fs.readdirSync(msgDir, { recursive: true }).filter((f) => String(f).endsWith(".ts")).map((f) => fs.readFileSync(path.join(msgDir, String(f)), "utf8")).join("\n");
// crude but effective: evaluate by importing compiled keys is avoided; rely on the test for exactness
const missing = [...literal].filter((k) => !new RegExp(`(^|[\\s{,])"?${k.split(".").pop().replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"?:`, "m").test(text));
console.log("LITERAL KEYS POSSIBLY MISSING (" + missing.length + "):\n" + missing.sort().join("\n"));
console.log("\nDYNAMIC TEMPLATES:\n" + [...dynamic].sort().join("\n"));
