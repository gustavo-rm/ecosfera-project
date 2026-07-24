import { palette } from '@/lib/three/colors';
import { SunLight } from './SunLight';

/** Iluminação da cena: Sol animado (canto superior direito), luz ambiente
 *  azulada (para o lado noturno não ficar preto) e leve preenchimento
 *  hemisférico. */
export function PlanetLights({ animate }: { animate: boolean }) {
  return (
    <>
      <ambientLight intensity={0.18} color={palette.atmosphere} />
      <hemisphereLight
        args={[palette.atmosphereBright, palette.spaceVoid, 0.16]}
      />
      <SunLight animate={animate} />
    </>
  );
}
