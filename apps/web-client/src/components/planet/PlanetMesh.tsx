import type { Texture } from 'three';
import { PLANET_RADIUS } from '@/lib/three/config';

interface PlanetMeshProps {
  surface: Texture;
  emissive: Texture;
  segments: number;
}

/** Superfície do planeta: cor procedural + mapa emissivo (redes biológicas)
 *  iluminados fisicamente, o que cria naturalmente o terminador dia/noite. */
export function PlanetMesh({ surface, emissive, segments }: PlanetMeshProps) {
  return (
    <mesh>
      <sphereGeometry args={[PLANET_RADIUS, segments, segments]} />
      <meshStandardMaterial
        map={surface}
        emissive="#ffffff"
        emissiveMap={emissive}
        emissiveIntensity={1.15}
        roughness={0.72}
        metalness={0.06}
      />
    </mesh>
  );
}
