import { useMemo, useRef } from 'react';
import { Vector3 } from 'three';
import { randRange } from '@/lib/three/math';
import {
  LIFE_LIFETIME_S,
  LIFE_MAX_CONCURRENT,
  LIFE_SPAWN_MAX_S,
  LIFE_SPAWN_MIN_S,
} from '@/lib/three/config';

export interface LifeSpark {
  active: boolean;
  age: number;
  ttl: number;
  scale: number;
  tint: number;
  position: Vector3;
}

export interface LifeController {
  sparks: LifeSpark[];
  update: (delta: number) => void;
}

/**
 * Orquestra o "surgimento da vida": em intervalos aleatórios ativa um foco
 * luminoso sobre uma região de terra do planeta. Cada foco nasce, permanece
 * alguns segundos e desaparece — e nunca surgem todos de uma vez.
 */
export function useLifeEvents(
  landPoints: readonly Vector3[],
  radius: number,
  enabled = true,
): LifeController {
  const sparks = useMemo<LifeSpark[]>(
    () =>
      Array.from({ length: LIFE_MAX_CONCURRENT }, () => ({
        active: false,
        age: 0,
        ttl: 0,
        scale: 1,
        tint: 0,
        position: new Vector3(),
      })),
    [],
  );

  const timer = useRef(randRange(2, LIFE_SPAWN_MAX_S));

  return useMemo<LifeController>(() => {
    const spawn = () => {
      const dir = landPoints[Math.floor(Math.random() * landPoints.length)];
      if (!dir) return;
      const free = sparks.find((s) => !s.active);
      if (!free) return;
      free.position.copy(dir).multiplyScalar(radius * 1.008);
      free.active = true;
      free.age = 0;
      free.ttl = randRange(LIFE_LIFETIME_S * 0.7, LIFE_LIFETIME_S * 1.3);
      free.scale = randRange(0.18, 0.42) * radius;
      free.tint = Math.random();
    };

    const update = (delta: number) => {
      if (!enabled) return;
      timer.current -= delta;
      if (timer.current <= 0) {
        spawn();
        timer.current = randRange(LIFE_SPAWN_MIN_S, LIFE_SPAWN_MAX_S);
      }
      for (const spark of sparks) {
        if (!spark.active) continue;
        spark.age += delta;
        if (spark.age >= spark.ttl) spark.active = false;
      }
    };

    return { sparks, update };
  }, [sparks, landPoints, radius, enabled]);
}
