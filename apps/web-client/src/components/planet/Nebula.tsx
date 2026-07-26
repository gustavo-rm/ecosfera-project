import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { AdditiveBlending, type Group, type Texture } from 'three';

interface NebulaProps {
  texture: Texture;
  animate: boolean;
}

/** Nebulosa diagonal no fundo, com deriva quase imperceptível. */
export function Nebula({ texture, animate }: NebulaProps) {
  const ref = useRef<Group>(null);

  useFrame((_, delta) => {
    if (animate && ref.current) ref.current.rotation.z += delta * 0.004;
  });

  return (
    <group ref={ref} position={[0, 7, -32]} rotation={[0, 0, -0.6]}>
      <mesh>
        <planeGeometry args={[90, 60]} />
        <meshBasicMaterial
          map={texture}
          transparent
          opacity={0.5}
          depthWrite={false}
          blending={AdditiveBlending}
        />
      </mesh>
    </group>
  );
}
