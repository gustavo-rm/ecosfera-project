import { Color } from 'three';

/**
 * Paleta central da cena 3D. Mantida em JS (Three precisa dos valores em
 * runtime) e espelhada como design tokens em `globals.css` para a camada DOM.
 */
export const palette = {
  spaceVoid: '#04060d',
  spaceDeep: '#050b16',
  spaceBlue: '#0d1628',
  atmosphere: '#3b82f6',
  atmosphereBright: '#7cb2ff',
  cyan: '#22d3ee',
  bio: '#34d399',
  bioBright: '#8bffcf',
  soft: '#f5f7fa',
  amber: '#ffb765',
  ocean: '#0a2540',
  oceanDeep: '#061428',
  land: '#123a2e',
  landHigh: '#1c5a42',
} as const;

export type PaletteKey = keyof typeof palette;

const cache = new Map<string, Color>();

/** Retorna uma instância `THREE.Color` memoizada para um hex da paleta. */
export function color(hex: string): Color {
  let value = cache.get(hex);
  if (!value) {
    value = new Color(hex);
    cache.set(hex, value);
  }
  return value;
}
