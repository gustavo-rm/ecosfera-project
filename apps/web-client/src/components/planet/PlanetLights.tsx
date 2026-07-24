import { palette } from '@/lib/three/colors';
import { SUN_DIRECTION } from '@/lib/three/config';

/** Iluminação da cena: Sol quente vindo do canto superior direito, luz
 *  ambiente azulada (para o lado noturno não ficar preto) e um leve
 *  preenchimento hemisférico. */
export function PlanetLights() {
  return (
    <>
      <ambientLight intensity={0.18} color={palette.atmosphere} />
      <hemisphereLight
        args={[palette.atmosphereBright, palette.spaceVoid, 0.16]}
      />
      <directionalLight
        position={SUN_DIRECTION}
        intensity={2.6}
        color="#fff3e0"
      />
    </>
  );
}
