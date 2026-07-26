import {
  CanvasTexture,
  LinearSRGBColorSpace,
  RepeatWrapping,
  SRGBColorSpace,
  Vector3,
} from 'three';
import { clamp, TWO_PI } from './math';
import { palette } from './colors';

/*
 * Texturas 100% procedurais — nenhuma imagem estática do planeta é usada
 * (requisito). O relevo é gerado por ruído de valor 3D amostrado sobre a
 * direção da esfera, o que torna a textura perfeitamente contínua (sem costura
 * na longitude) quando aplicada à `SphereGeometry`.
 */

type Rgb = [number, number, number];

function hexToRgb(hex: string): Rgb {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mixChannel(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Noise3D = (x: number, y: number, z: number) => number;

function makeValueNoise3D(seed: number): Noise3D {
  const perm = new Uint8Array(512);
  const source = new Uint8Array(256);
  for (let i = 0; i < 256; i++) source[i] = i;
  const rng = mulberry32(seed);
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const tmp = source[i];
    source[i] = source[j];
    source[j] = tmp;
  }
  for (let i = 0; i < 512; i++) perm[i] = source[i & 255];

  const fade = (t: number) => t * t * t * (t * (t * 6 - 15) + 10);
  const lerp = (a: number, b: number, t: number) => a + t * (b - a);
  const hash = (x: number, y: number, z: number) =>
    perm[(perm[(perm[x & 255] + y) & 255] + z) & 255] / 255;

  return (x, y, z) => {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const zi = Math.floor(z);
    const xf = fade(x - xi);
    const yf = fade(y - yi);
    const zf = fade(z - zi);
    const x00 = lerp(hash(xi, yi, zi), hash(xi + 1, yi, zi), xf);
    const x10 = lerp(hash(xi, yi + 1, zi), hash(xi + 1, yi + 1, zi), xf);
    const x01 = lerp(hash(xi, yi, zi + 1), hash(xi + 1, yi, zi + 1), xf);
    const x11 = lerp(hash(xi, yi + 1, zi + 1), hash(xi + 1, yi + 1, zi + 1), xf);
    return lerp(lerp(x00, x10, yf), lerp(x01, x11, yf), zf);
  };
}

function fbm(noise: Noise3D, x: number, y: number, z: number, octaves: number): number {
  let amplitude = 0.5;
  let frequency = 1;
  let sum = 0;
  let norm = 0;
  for (let o = 0; o < octaves; o++) {
    sum += amplitude * noise(x * frequency, y * frequency, z * frequency);
    norm += amplitude;
    amplitude *= 0.5;
    frequency *= 2;
  }
  return sum / norm;
}

function createCanvas(width: number, height: number): {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
} {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas 2D não disponível neste ambiente.');
  return { canvas, ctx };
}

export interface PlanetTextures {
  surface: CanvasTexture;
  emissive: CanvasTexture;
  roughness: CanvasTexture;
  landPoints: Vector3[];
}

/** Gera, num único passo, o mapa de cor (oceanos/continentes) e o mapa
 *  emissivo (redes biológicas verdes), além de coletar pontos de terra onde a
 *  vida pode surgir. */
export function generatePlanetTextures(size: number): PlanetTextures {
  const width = size;
  const height = Math.max(2, Math.floor(size / 2));

  const surfaceLayer = createCanvas(width, height);
  const emissiveLayer = createCanvas(width, height);
  const roughnessLayer = createCanvas(width, height);
  const surfaceImg = surfaceLayer.ctx.createImageData(width, height);
  const emissiveImg = emissiveLayer.ctx.createImageData(width, height);
  const roughnessImg = roughnessLayer.ctx.createImageData(width, height);
  const sd = surfaceImg.data;
  const ed = emissiveImg.data;
  const rd = roughnessImg.data;

  const elevation = makeValueNoise3D(1337);
  const detail = makeValueNoise3D(7919);
  const veins = makeValueNoise3D(4242);

  const oceanDeep = hexToRgb(palette.oceanDeep);
  const ocean = hexToRgb(palette.ocean);
  const land = hexToRgb(palette.land);
  const landHigh = hexToRgb(palette.landHigh);
  const bio = hexToRgb(palette.bio);
  const bioBright = hexToRgb(palette.bioBright);
  const ice: Rgb = [223, 239, 255];

  const landPoints: Vector3[] = [];
  const seaLevel = 0.5;
  const sampleStep = Math.max(4, Math.floor(width / 48));

  for (let py = 0; py < height; py++) {
    const theta = (py / (height - 1)) * Math.PI;
    const sinT = Math.sin(theta);
    const cosT = Math.cos(theta);
    for (let px = 0; px < width; px++) {
      const phi = (px / width) * TWO_PI;
      const dx = sinT * Math.cos(phi);
      const dy = cosT;
      const dz = sinT * Math.sin(phi);
      const idx = (py * width + px) * 4;

      const e =
        fbm(elevation, dx * 1.7 + 5, dy * 1.7 + 5, dz * 1.7 + 5, 5) * 0.82 +
        fbm(detail, dx * 4.6, dy * 4.6, dz * 4.6, 3) * 0.18;

      let r: number;
      let g: number;
      let b: number;
      if (e < seaLevel) {
        const depth = smoothstep(seaLevel, 0.12, e);
        r = mixChannel(ocean[0], oceanDeep[0], depth);
        g = mixChannel(ocean[1], oceanDeep[1], depth);
        b = mixChannel(ocean[2], oceanDeep[2], depth);
      } else {
        const h = smoothstep(seaLevel, 1, e);
        r = mixChannel(land[0], landHigh[0], h);
        g = mixChannel(land[1], landHigh[1], h);
        b = mixChannel(land[2], landHigh[2], h);
      }

      const polar = Math.abs(cosT);
      if (polar > 0.82) {
        const iceF = smoothstep(0.82, 0.98, polar) * 0.85;
        r = mixChannel(r, ice[0], iceF);
        g = mixChannel(g, ice[1], iceF);
        b = mixChannel(b, ice[2], iceF);
      }

      sd[idx] = r;
      sd[idx + 1] = g;
      sd[idx + 2] = b;
      sd[idx + 3] = 255;

      // Oceanos são lisos (baixa rugosidade → reflexos intensos do Sol); a
      // terra é fosca. Alimenta o `roughnessMap`.
      const rough = e < seaLevel ? 46 : 235;
      rd[idx] = rough;
      rd[idx + 1] = rough;
      rd[idx + 2] = rough;
      rd[idx + 3] = 255;

      if (e >= seaLevel + 0.02 && polar < 0.8) {
        const vn = fbm(veins, dx * 3.6 + 11, dy * 3.6 + 11, dz * 3.6 + 11, 4);
        const ridged = 1 - Math.abs(vn * 2 - 1);
        const net = smoothstep(0.82, 0.99, ridged);
        if (net > 0) {
          const bright = smoothstep(0.9, 1, ridged);
          ed[idx] = mixChannel(bio[0], bioBright[0], bright) * net;
          ed[idx + 1] = mixChannel(bio[1], bioBright[1], bright) * net;
          ed[idx + 2] = mixChannel(bio[2], bioBright[2], bright) * net;
          ed[idx + 3] = 255;
        }
      }

      if (
        e >= seaLevel + 0.05 &&
        polar < 0.75 &&
        px % sampleStep === 0 &&
        py % sampleStep === 0
      ) {
        landPoints.push(new Vector3(dx, dy, dz));
      }
    }
  }

  surfaceLayer.ctx.putImageData(surfaceImg, 0, 0);
  emissiveLayer.ctx.putImageData(emissiveImg, 0, 0);
  roughnessLayer.ctx.putImageData(roughnessImg, 0, 0);

  const surface = new CanvasTexture(surfaceLayer.canvas);
  surface.colorSpace = SRGBColorSpace;
  surface.wrapS = RepeatWrapping;
  surface.anisotropy = 4;

  const emissive = new CanvasTexture(emissiveLayer.canvas);
  emissive.colorSpace = SRGBColorSpace;
  emissive.wrapS = RepeatWrapping;

  // Mapa de dados (não é cor) → espaço linear.
  const roughness = new CanvasTexture(roughnessLayer.canvas);
  roughness.colorSpace = LinearSRGBColorSpace;
  roughness.wrapS = RepeatWrapping;

  if (landPoints.length === 0) {
    landPoints.push(new Vector3(0.3, 0.2, 0.9).normalize());
  }

  return { surface, emissive, roughness, landPoints };
}

/** Ícone de "vida": uma silhueta humana simples (símbolo universal de vida),
 *  branca sobre fundo transparente e tingida via `material.color`. */
export function createLifeSymbolTexture(size = 128): CanvasTexture {
  const { canvas, ctx } = createCanvas(size, size);
  const s = size / 128;
  ctx.clearRect(0, 0, size, size);

  const drawFigure = () => {
    ctx.beginPath();
    ctx.arc(64 * s, 40 * s, 15 * s, 0, TWO_PI);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(64 * s, 58 * s);
    ctx.bezierCurveTo(87 * s, 58 * s, 90 * s, 98 * s, 85 * s, 116 * s);
    ctx.lineTo(43 * s, 116 * s);
    ctx.bezierCurveTo(38 * s, 98 * s, 41 * s, 58 * s, 64 * s, 58 * s);
    ctx.closePath();
    ctx.fill();
  };

  // Aura escura suave: garante contraste da silhueta sobre nuvens claras.
  ctx.fillStyle = 'rgba(3, 18, 22, 0.8)';
  ctx.shadowColor = 'rgba(3, 18, 22, 0.85)';
  ctx.shadowBlur = 12 * s;
  drawFigure();

  // Figura luminosa (verde-esmeralda claro) por cima.
  ctx.shadowColor = 'rgba(150, 255, 220, 0.95)';
  ctx.shadowBlur = 6 * s;
  ctx.fillStyle = '#aeffe8';
  drawFigure();

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/** Nuvens volumétricas em uma casca transparente, giradas independentemente. */
export function createCloudTexture(size: number): CanvasTexture {
  const width = size;
  const height = Math.max(2, Math.floor(size / 2));
  const { canvas, ctx } = createCanvas(width, height);
  const img = ctx.createImageData(width, height);
  const data = img.data;
  const noise = makeValueNoise3D(2024);

  for (let py = 0; py < height; py++) {
    const theta = (py / (height - 1)) * Math.PI;
    const sinT = Math.sin(theta);
    const cosT = Math.cos(theta);
    for (let px = 0; px < width; px++) {
      const phi = (px / width) * TWO_PI;
      const dx = sinT * Math.cos(phi);
      const dy = cosT;
      const dz = sinT * Math.sin(phi);
      const density = fbm(noise, dx * 2.3 + 3, dy * 2.3 + 3, dz * 2.3 + 3, 5);
      const coverage = smoothstep(0.5, 0.72, density);
      const idx = (py * width + px) * 4;
      data[idx] = 255;
      data[idx + 1] = 255;
      data[idx + 2] = 255;
      data[idx + 3] = Math.round(coverage * 235);
    }
  }

  ctx.putImageData(img, 0, 0);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.wrapS = RepeatWrapping;
  return texture;
}

/** Nebulosa suave (blobs radiais aditivos) para o fundo espacial. */
export function createNebulaTexture(size = 1024): CanvasTexture {
  const { canvas, ctx } = createCanvas(size, size);
  ctx.clearRect(0, 0, size, size);
  ctx.globalCompositeOperation = 'lighter';

  const blobs: Array<{ x: number; y: number; r: number; color: string }> = [
    { x: 0.32, y: 0.34, r: 0.34, color: '59,130,246' },
    { x: 0.46, y: 0.28, r: 0.26, color: '34,211,238' },
    { x: 0.58, y: 0.4, r: 0.3, color: '109,59,214' },
    { x: 0.4, y: 0.46, r: 0.22, color: '52,211,153' },
    { x: 0.66, y: 0.24, r: 0.2, color: '124,178,255' },
  ];

  for (const blob of blobs) {
    const cx = blob.x * size;
    const cy = blob.y * size;
    const radius = blob.r * size;
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    gradient.addColorStop(0, `rgba(${blob.color},0.5)`);
    gradient.addColorStop(0.5, `rgba(${blob.color},0.15)`);
    gradient.addColorStop(1, `rgba(${blob.color},0)`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  }

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/** Sprite radial branco (centro → transparente). Tingido via `material.color`
 *  para reaproveitar em glow atmosférico, Sol e focos de vida. */
export function createRadialTexture(size = 128): CanvasTexture {
  const { canvas, ctx } = createCanvas(size, size);
  const half = size / 2;
  const gradient = ctx.createRadialGradient(half, half, 0, half, half, half);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.25, 'rgba(255,255,255,0.75)');
  gradient.addColorStop(0.6, 'rgba(255,255,255,0.18)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}
