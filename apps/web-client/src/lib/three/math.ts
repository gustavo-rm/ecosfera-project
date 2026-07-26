export const TWO_PI = Math.PI * 2;

export function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

export function randRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

/** PRNG determinístico (mulberry32). Usado para gerar dados aleatórios de forma
 *  *pura* durante o render (ex.: campo de estrelas), sempre idêntico por seed. */
export function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Envelope suave 0→1→0 usado para nascer/morrer de efeitos (age em 0..1). */
export function pulseEnvelope(t: number): number {
  return Math.sin(clamp(t, 0, 1) * Math.PI);
}
