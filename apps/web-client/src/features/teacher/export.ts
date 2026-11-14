/** Client-side exports (RF-066): CSV and a minimal PDF writer. Nothing leaves the browser. */
export function toCsv(header: string[], rows: (string | number)[][]): string {
  // Text that starts like a formula is prefixed with an apostrophe, so a spreadsheet never executes it.
  const esc = (v: string | number) => { const s = typeof v === "number" ? String(v).replace(".", ",") : /^[=+\-@]/.test(v) ? "'" + v : v; return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  // Semicolon separator and BOM: opens correctly in spreadsheet programs configured for pt-BR.
  return "﻿" + [header, ...rows].map((r) => r.map(esc).join(";")).join("\r\n");
}
export function download(filename: string, content: BlobPart, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type })), a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const WIN1252: Record<string, number> = { "–": 0x96, "—": 0x97, "“": 0x93, "”": 0x94, "’": 0x92, "•": 0x95, "…": 0x85, "€": 0x80, "₂": 0x32, "₄": 0x34, "≥": 0x3e, "→": 0x3e, "⊕": 0x2b };
function encode(s: string): string {
  let out = "";
  for (const ch of s) { const c = ch.charCodeAt(0); const b = c < 256 ? c : WIN1252[ch] ?? 63; out += b === 40 || b === 41 || b === 92 ? "\\" + String.fromCharCode(b) : String.fromCharCode(b); }
  return out;
}
/**
 * Text-only PDF (A4, Helvetica, WinAnsi) written by hand to avoid a heavy dependency.
 * Lines starting with "# " are headings. Long lines wrap by character count.
 */
export function buildPdf(title: string, lines: string[]): Uint8Array {
  const wrapped: { text: string; size: number }[] = [{ text: title, size: 18 }, { text: "", size: 10 }];
  for (const raw of lines) {
    const heading = raw.startsWith("# "), text = heading ? raw.slice(2) : raw, max = heading ? 70 : 96;
    if (text.length <= max) { wrapped.push({ text, size: heading ? 13 : 10 }); continue; }
    let rest = text;
    while (rest.length > max) { let cut = rest.lastIndexOf(" ", max); if (cut < 20) cut = max; wrapped.push({ text: rest.slice(0, cut), size: 10 }); rest = rest.slice(cut).trimStart(); }
    wrapped.push({ text: rest, size: 10 });
  }
  const pages: string[] = [];
  let y = 800, body = "";
  for (const l of wrapped) {
    const lead = l.size + 5;
    if (y - lead < 50) { pages.push(body); body = ""; y = 800; }
    y -= lead;
    body += `BT /F${l.size >= 13 ? 2 : 1} ${l.size} Tf 50 ${y} Td (${encode(l.text)}) Tj ET\n`;
  }
  pages.push(body);
  const objs: string[] = [];
  objs.push("<< /Type /Catalog /Pages 2 0 R >>");
  objs.push(`<< /Type /Pages /Kids [${pages.map((_, i) => `${5 + i * 2} 0 R`).join(" ")}] /Count ${pages.length} >>`);
  objs.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  objs.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  pages.forEach((p, i) => {
    objs.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${6 + i * 2} 0 R >>`);
    objs.push(`<< /Length ${p.length} >>\nstream\n${p}endstream`);
  });
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((o, i) => { offsets.push(pdf.length); pdf += `${i + 1} 0 obj\n${o}\nendobj\n`; });
  const xref = pdf.length;
  pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n${offsets.map((o) => String(o).padStart(10, "0") + " 00000 n \n").join("")}trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  const bytes = new Uint8Array(pdf.length);
  for (let i = 0; i < pdf.length; i++) bytes[i] = pdf.charCodeAt(i) & 0xff;
  return bytes;
}
