import { useCallback, useMemo } from 'react';
import type { BufferAttribute } from 'three';
import { randRange, TWO_PI } from '@/lib/three/math';

/**
 * Gera e anima partículas luminosas muito discretas que sobem lentamente ao
 * redor do planeta, reforçando a sensação de atmosfera viva.
 */
export function useDustParticles(count: number, radius: number) {
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const angle = randRange(0, TWO_PI);
      const distance = radius * randRange(1.06, 1.7);
      arr[i * 3] = Math.cos(angle) * distance;
      arr[i * 3 + 1] = randRange(-radius, radius);
      arr[i * 3 + 2] = Math.sin(angle) * distance * 0.6;
    }
    return arr;
  }, [count, radius]);

  const tick = useCallback(
    (attr: BufferAttribute, delta: number) => {
      const arr = attr.array as Float32Array;
      const bound = radius * 1.7;
      for (let i = 1; i < arr.length; i += 3) {
        arr[i] += delta * 0.16;
        if (arr[i] > bound) arr[i] = -bound;
      }
      attr.needsUpdate = true;
    },
    [radius],
  );

  return { positions, tick };
}
