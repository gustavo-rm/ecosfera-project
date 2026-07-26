import { useFrame } from '@react-three/fiber';
import type { RefObject } from 'react';
import type { Object3D } from 'three';
import { TWO_PI } from '@/lib/three/math';

/**
 * Aplica rotação contínua no eixo Y de um objeto. O período (em segundos)
 * define uma volta completa; `speedScale` permite desacelerar (ex.: modo de
 * movimento reduzido) sem recriar o efeito.
 */
export function usePlanetRotation(
  ref: RefObject<Object3D | null>,
  periodSeconds: number,
  speedScale = 1,
): void {
  useFrame((_, delta) => {
    const obj = ref.current;
    if (!obj || speedScale === 0) return;
    // delta limitado evita "saltos" ao voltar de uma aba inativa.
    obj.rotation.y += (TWO_PI / periodSeconds) * speedScale * Math.min(delta, 0.1);
  });
}
