/**
 * Constantes de tunning da cena. Centralizadas para manter os componentes
 * livres de "números mágicos" e facilitar ajustes de arte/performance.
 */

/** Uma volta completa entre 2 e 4 min: movimento perceptível, porém natural. */
export const PLANET_ROTATION_PERIOD_S = 3 * 60;
/** Nuvens giram um pouco mais rápido para gerar sensação de profundidade. */
export const CLOUD_ROTATION_PERIOD_S = 2.5 * 60;

export const PLANET_RADIUS = 3.2;
export const CLOUD_SCALE = 1.012;
export const ATMOSPHERE_SCALE = 1.055;
export const GLOW_SCALE = 3;

/** Inclinação axial sutil, apenas estética. */
export const PLANET_TILT = 0.28;

/** Direção da luz principal (Sol) — canto superior direito da tela. */
export const SUN_DIRECTION: readonly [number, number, number] = [6.5, 4.2, 3.5];

/** Janela aleatória de surgimento dos focos luminosos ambientes (segundos). */
export const LIFE_SPAWN_MIN_S = 8;
export const LIFE_SPAWN_MAX_S = 20;
export const LIFE_MAX_CONCURRENT = 5;
export const LIFE_LIFETIME_S = 4.5;

/** Evento de "surgimento da vida": um símbolo aparece a cada 20 s, permanece
 *  ~3 s e desaparece suavemente. */
export const LIFE_EMERGENCE_INTERVAL_S = 20;
export const LIFE_EMERGENCE_FADE_IN_S = 0.6;
export const LIFE_EMERGENCE_HOLD_S = 3;
export const LIFE_EMERGENCE_FADE_OUT_S = 0.9;
/** Quanto o brilho das redes biológicas se intensifica durante o evento. */
export const LIFE_EMERGENCE_BOOST = 0.22;

export type QualityTier = 'high' | 'medium' | 'low';

export interface QualitySettings {
  readonly tier: QualityTier;
  readonly textureSize: number;
  readonly sphereSegments: number;
  readonly starCount: number;
  readonly dustCount: number;
  readonly dpr: [number, number];
  readonly bloom: boolean;
  readonly bloomIntensity: number;
}

export const QUALITY: Record<QualityTier, QualitySettings> = {
  high: {
    tier: 'high',
    textureSize: 1024,
    sphereSegments: 96,
    starCount: 1600,
    dustCount: 90,
    dpr: [1, 1.8],
    bloom: true,
    bloomIntensity: 0.85,
  },
  medium: {
    tier: 'medium',
    textureSize: 768,
    sphereSegments: 72,
    starCount: 950,
    dustCount: 50,
    dpr: [1, 1.5],
    bloom: true,
    bloomIntensity: 0.7,
  },
  low: {
    tier: 'low',
    textureSize: 512,
    sphereSegments: 48,
    starCount: 500,
    dustCount: 0,
    dpr: [1, 1],
    bloom: false,
    bloomIntensity: 0,
  },
};
