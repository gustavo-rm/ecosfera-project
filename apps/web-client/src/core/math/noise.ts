import { hash4 } from "./rng";

const fade = (t: number) => t * t * t * (t * (t * 6 - 15) + 10);

/** 3D value noise in [0, 1], deterministic per seed. */
export function noise3(x: number, y: number, z: number, seed: number): number {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const u = fade(x - xi), v = fade(y - yi), w = fade(z - zi);
  const c000 = hash4(xi, yi, zi, seed), c100 = hash4(xi + 1, yi, zi, seed);
  const c010 = hash4(xi, yi + 1, zi, seed), c110 = hash4(xi + 1, yi + 1, zi, seed);
  const c001 = hash4(xi, yi, zi + 1, seed), c101 = hash4(xi + 1, yi, zi + 1, seed);
  const c011 = hash4(xi, yi + 1, zi + 1, seed), c111 = hash4(xi + 1, yi + 1, zi + 1, seed);
  const x00 = c000 + (c100 - c000) * u, x10 = c010 + (c110 - c010) * u;
  const x01 = c001 + (c101 - c001) * u, x11 = c011 + (c111 - c011) * u;
  const y0 = x00 + (x10 - x00) * v, y1 = x01 + (x11 - x01) * v;
  return y0 + (y1 - y0) * w;
}

/** Fractal Brownian motion, normalized to about [0, 1]. */
export function fbm3(x: number, y: number, z: number, seed: number, octaves = 5, lacunarity = 2.03, gain = 0.5): number {
  let amp = 0.5, freq = 1, sum = 0, norm = 0;
  for (let o = 0; o < octaves; o++) {
    sum += amp * noise3(x * freq, y * freq, z * freq, seed + o * 101);
    norm += amp;
    amp *= gain;
    freq *= lacunarity;
  }
  return sum / norm;
}

/** Ridged multifractal in [0, 1]: sharp crests, used for mountain ranges. */
export function ridged3(x: number, y: number, z: number, seed: number, octaves = 4): number {
  let amp = 0.5, freq = 1, sum = 0, norm = 0;
  for (let o = 0; o < octaves; o++) {
    const n = 1 - Math.abs(noise3(x * freq, y * freq, z * freq, seed + o * 57) * 2 - 1);
    sum += amp * n * n;
    norm += amp;
    amp *= 0.5;
    freq *= 2.1;
  }
  return sum / norm;
}
