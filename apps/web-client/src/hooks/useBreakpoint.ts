'use client';

import { useEffect, useState } from 'react';
import { QUALITY, type QualitySettings } from '@/lib/three/config';

export type Breakpoint = 'mobile' | 'tablet' | 'notebook' | 'desktop';

function resolve(width: number): Breakpoint {
  if (width < 768) return 'mobile';
  if (width < 1024) return 'tablet';
  if (width < 1440) return 'notebook';
  return 'desktop';
}

const QUALITY_BY_BREAKPOINT: Record<Breakpoint, QualitySettings> = {
  mobile: QUALITY.low,
  tablet: QUALITY.medium,
  notebook: QUALITY.high,
  desktop: QUALITY.high,
};

/**
 * Observa a largura da viewport e deriva o breakpoint atual e o nível de
 * qualidade da cena 3D. Inicia em `desktop` para casar com o SSR e atualiza
 * após a montagem, evitando divergência de hidratação.
 */
export function useBreakpoint(): {
  breakpoint: Breakpoint;
  quality: QualitySettings;
} {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('desktop');

  useEffect(() => {
    const update = () => setBreakpoint(resolve(window.innerWidth));
    update();
    window.addEventListener('resize', update, { passive: true });
    return () => window.removeEventListener('resize', update);
  }, []);

  return { breakpoint, quality: QUALITY_BY_BREAKPOINT[breakpoint] };
}
