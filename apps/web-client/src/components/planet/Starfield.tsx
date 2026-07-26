import { useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { AdditiveBlending } from 'three';
import {
  starfieldFragmentShader,
  starfieldVertexShader,
} from '@/lib/three/shaders';
import { createRng, TWO_PI } from '@/lib/three/math';

interface StarfieldProps {
  count: number;
  animate: boolean;
}

type Rgb = readonly [number, number, number];

const STAR_TINTS: readonly Rgb[] = [
  [1, 1, 1],
  [0.72, 0.85, 1],
  [1, 0.9, 0.76],
  [0.8, 1, 0.95],
];

/** Campo de estrelas distribuído numa casca esférica ao redor da câmera, com
 *  cintilância independente por estrela (shader). */
export function Starfield({ count, animate }: StarfieldProps) {
  const pixelRatio = useThree((state) => state.gl.getPixelRatio());

  const attributes = useMemo(() => {
    const rng = createRng(0x5f3a71 ^ count);
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const phases = new Float32Array(count);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const u = rng() * 2 - 1;
      const angle = rng() * TWO_PI;
      const ring = Math.sqrt(1 - u * u);
      const radius = 45 + rng() * 50;
      positions[i * 3] = Math.cos(angle) * ring * radius;
      positions[i * 3 + 1] = u * radius;
      positions[i * 3 + 2] = Math.sin(angle) * ring * radius;

      sizes[i] = 1 + rng() * 2.2;
      phases[i] = rng() * TWO_PI;

      const tint: Rgb =
        rng() < 0.7
          ? [1, 1, 1]
          : STAR_TINTS[Math.floor(rng() * STAR_TINTS.length)] ?? [1, 1, 1];
      colors[i * 3] = tint[0];
      colors[i * 3 + 1] = tint[1];
      colors[i * 3 + 2] = tint[2];
    }

    return { positions, sizes, phases, colors };
  }, [count]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixelRatio: { value: Math.min(pixelRatio, 2) },
    }),
    [pixelRatio],
  );

  useFrame((state) => {
    if (animate) uniforms.uTime.value = state.clock.elapsedTime;
  });

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[attributes.positions, 3]} />
        <bufferAttribute attach="attributes-aSize" args={[attributes.sizes, 1]} />
        <bufferAttribute attach="attributes-aPhase" args={[attributes.phases, 1]} />
        <bufferAttribute attach="attributes-aColor" args={[attributes.colors, 3]} />
      </bufferGeometry>
      <shaderMaterial
        vertexShader={starfieldVertexShader}
        fragmentShader={starfieldFragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={AdditiveBlending}
      />
    </points>
  );
}
