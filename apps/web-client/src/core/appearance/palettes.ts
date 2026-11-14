/** Color-vision-safe palettes, contrast math and color-blindness simulation. Pure functions, unit tested. */
export type RGB = [number, number, number]; // sRGB 0..1
export type PaletteSet = "default" | "cividis" | "gray";

const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];
export const toHex = (c: RGB) => "#" + c.map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, "0")).join("");

const STOPS: Record<string, string[]> = {
  viridis: ["#440154", "#482878", "#3e4989", "#31688e", "#26828e", "#1f9e89", "#35b779", "#6ece58", "#b5de2b", "#fde725"],
  cividis: ["#00224e", "#123570", "#3b496c", "#575d6d", "#707173", "#8a8678", "#a59c74", "#c3b369", "#e1cc55", "#fee838"],
  gray: ["#1a1a1a", "#f2f2f2"],
  // Diverging blue to orange, light neutral in the middle: safe for the three common types of color blindness.
  blueOrange: ["#0b3c7a", "#2f6fb5", "#7fb0dc", "#dbe7f0", "#f6dcc0", "#ef9d55", "#d4621a", "#8a3305"],
  blueYellow: ["#00204d", "#31446b", "#666970", "#958f78", "#cbba69", "#ffea46"],
};
export const SEQUENTIAL: Record<PaletteSet, string> = { default: "viridis", cividis: "cividis", gray: "gray" };
export const DIVERGING: Record<PaletteSet, string> = { default: "blueOrange", cividis: "blueYellow", gray: "gray" };

export function samplePalette(name: string, t: number): RGB {
  const s = STOPS[name] ?? STOPS.viridis, x = Math.min(1, Math.max(0, t)) * (s.length - 1), i = Math.min(s.length - 2, Math.floor(x)), f = x - i;
  const a = hex(s[i]), b = hex(s[i + 1]);
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}
/** 256-entry RGBA lookup table for the GPU. */
export function buildLut(name: string): Uint8Array {
  const out = new Uint8Array(256 * 4);
  for (let i = 0; i < 256; i++) { const c = samplePalette(name, i / 255); out[i * 4] = c[0] * 255; out[i * 4 + 1] = c[1] * 255; out[i * 4 + 2] = c[2] * 255; out[i * 4 + 3] = 255; }
  return out;
}

/** Okabe-Ito categorical colors for chart series. Always paired with a marker shape and a label (never color alone). */
export const SERIES_COLORS = ["#0072b2", "#e69f00", "#009e73", "#d55e00", "#cc79a7", "#56b4e9", "#f0e442", "#000000"];
/** Dark-surface steps, validated with the dataviz palette validator (lightness band, chroma, CVD and normal-vision separation). */
export const SERIES_COLORS_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#c3c2b7"];
export const SERIES_SHAPES = ["circle", "square", "triangle", "diamond", "cross", "star", "wye", "circle"] as const;

const lin = (v: number) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
const unlin = (v: number) => (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
export const luminance = (c: RGB) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
/** WCAG 2.1 contrast ratio between two sRGB colors. */
export function contrastRatio(a: RGB | string, b: RGB | string): number {
  const la = luminance(typeof a === "string" ? hex(a) : a), lb = luminance(typeof b === "string" ? hex(b) : b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

export type CvdType = "protan" | "deutan" | "tritan";
// Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB.
const CVD: Record<CvdType, number[]> = {
  protan: [0.152286, 1.052583, -0.204868, 0.114503, 0.786281, 0.099216, -0.003882, -0.048116, 1.051998],
  deutan: [0.367322, 0.860646, -0.227968, 0.280085, 0.672501, 0.047413, -0.01182, 0.04294, 0.968881],
  tritan: [1.255528, -0.076749, -0.178779, -0.078411, 0.930809, 0.147602, 0.004733, 0.691367, 0.3039],
};
export function simulateCvd(c: RGB | string, type: CvdType): RGB {
  const s = typeof c === "string" ? hex(c) : c, m = CVD[type], r = lin(s[0]), g = lin(s[1]), b = lin(s[2]);
  const cl = (v: number) => unlin(Math.min(1, Math.max(0, v)));
  return [cl(m[0] * r + m[1] * g + m[2] * b), cl(m[3] * r + m[4] * g + m[5] * b), cl(m[6] * r + m[7] * g + m[8] * b)];
}
/** Perceptual distance (CIE76 in CIELAB). About 2.3 is a just-noticeable difference. */
export function deltaE(a: RGB | string, b: RGB | string): number {
  const lab = (c: RGB | string) => {
    const s = typeof c === "string" ? hex(c) : c, r = lin(s[0]), g = lin(s[1]), bl = lin(s[2]);
    const f = (t: number) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
    const x = f((0.4124 * r + 0.3576 * g + 0.1805 * bl) / 0.95047), y = f(0.2126 * r + 0.7152 * g + 0.0722 * bl), z = f((0.0193 * r + 0.1192 * g + 0.9505 * bl) / 1.08883);
    return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
  };
  const p = lab(a), q = lab(b);
  return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
}
export { hex as hexToRgb };
