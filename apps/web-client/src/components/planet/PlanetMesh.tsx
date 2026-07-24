import { useRef, type RefObject } from 'react';
import { useFrame } from '@react-three/fiber';
import type { MeshStandardMaterial, Texture } from 'three';
import { PLANET_RADIUS } from '@/lib/three/config';

interface PlanetMeshProps {
  surface: Texture;
  emissive: Texture;
  roughnessMap: Texture;
  segments: number;
  /** Reforço de brilho emissivo escrito pelos eventos de vida (0 = normal). */
  emissiveBoostRef: RefObject<number>;
  baseEmissive?: number;
}

/** Superfície do planeta: cor procedural + mapa emissivo (redes biológicas) +
 *  rugosidade (oceanos lisos refletem o Sol). O brilho das redes responde
 *  suavemente ao surgimento da vida via `emissiveBoostRef`. */
export function PlanetMesh({
  surface,
  emissive,
  roughnessMap,
  segments,
  emissiveBoostRef,
  baseEmissive = 1.15,
}: PlanetMeshProps) {
  const materialRef = useRef<MeshStandardMaterial>(null);

  useFrame(() => {
    const material = materialRef.current;
    if (material) material.emissiveIntensity = baseEmissive + emissiveBoostRef.current;
  });

  return (
    <mesh>
      <sphereGeometry args={[PLANET_RADIUS, segments, segments]} />
      <meshStandardMaterial
        ref={materialRef}
        map={surface}
        emissive="#ffffff"
        emissiveMap={emissive}
        emissiveIntensity={baseEmissive}
        roughnessMap={roughnessMap}
        roughness={1}
        metalness={0.08}
      />
    </mesh>
  );
}
