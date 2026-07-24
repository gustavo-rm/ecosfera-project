'use client';

import { useEffect, useRef, type RefObject } from 'react';

export interface Pointer {
  x: number;
  y: number;
}

/**
 * Rastreia a posição normalizada do ponteiro (-1..1 em cada eixo) num `ref`
 * mutável, sem provocar re-render. Ideal para consumo dentro de `useFrame`,
 * onde aplicamos o parallax com amortecimento.
 */
export function usePointerParallax(): RefObject<Pointer> {
  const pointer = useRef<Pointer>({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      pointer.current.x = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (event.clientY / window.innerHeight) * 2 - 1;
    };
    const onLeave = () => {
      pointer.current.x = 0;
      pointer.current.y = 0;
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerleave', onLeave, { passive: true });
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerleave', onLeave);
    };
  }, []);

  return pointer;
}
