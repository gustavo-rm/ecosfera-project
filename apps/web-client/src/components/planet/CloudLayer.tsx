import type { Texture } from 'three';
import { CLOUD_SCALE, PLANET_RADIUS } from '@/lib/three/config';

interface CloudLayerProps {
  texture: Texture;
  segments: number;
}

/** Casca de nuvens ligeiramente maior que a superfície. A rotação própria (um
 *  pouco diferente da do planeta) é aplicada pelo grupo pai. */
export function CloudLayer({ texture, segments }: CloudLayerProps) {
  return (
    <mesh scale={PLANET_RADIUS * CLOUD_SCALE}>
      <sphereGeometry args={[1, segments, segments]} />
      <meshStandardMaterial
        map={texture}
        transparent
        opacity={0.9}
        depthWrite={false}
        roughness={1}
        metalness={0}
      />
    </mesh>
  );
}
