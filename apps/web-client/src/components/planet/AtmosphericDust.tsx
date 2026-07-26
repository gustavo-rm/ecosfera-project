import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { AdditiveBlending, type BufferAttribute, type Points, type Texture } from 'three';
import { useDustParticles } from '@/hooks/useDustParticles';
import { palette } from '@/lib/three/colors';
import { PLANET_RADIUS } from '@/lib/three/config';

interface AtmosphericDustProps {
  count: number;
  texture: Texture;
  animate: boolean;
}

/** Partículas luminosas muito discretas que atravessam a atmosfera. */
export function AtmosphericDust({ count, texture, animate }: AtmosphericDustProps) {
  const { positions, tick } = useDustParticles(count, PLANET_RADIUS);
  const ref = useRef<Points>(null);

  useFrame((_, delta) => {
    if (!animate) return;
    const attribute = ref.current?.geometry.getAttribute('position');
    if (attribute) tick(attribute as BufferAttribute, delta);
  });

  if (count <= 0) return null;

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        map={texture}
        color={palette.bioBright}
        size={0.06}
        sizeAttenuation
        transparent
        opacity={0.45}
        depthWrite={false}
        blending={AdditiveBlending}
      />
    </points>
  );
}
