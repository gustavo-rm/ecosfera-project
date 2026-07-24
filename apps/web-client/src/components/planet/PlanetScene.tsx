'use client';

import { Suspense, useMemo, type RefObject } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Starfield } from './Starfield';
import { Nebula } from './Nebula';
import { PlanetLights } from './PlanetLights';
import { PlanetSystem } from './PlanetSystem';
import { PostProcessing } from './PostProcessing';
import { useBreakpoint, type Breakpoint } from '@/hooks/useBreakpoint';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { usePointerParallax, type Pointer } from '@/hooks/usePointerParallax';
import { createNebulaTexture, createRadialTexture } from '@/lib/three/textures';
import { palette } from '@/lib/three/colors';

interface Placement {
  position: [number, number, number];
  scale: number;
}

/** Posição/escala do planeta por breakpoint. Ele é o elemento principal: fica
 *  grande e deslocado para o canto inferior esquerdo (~35% da largura fora pela
 *  esquerda, ~20% da altura abaixo da viewport), transmitindo a sensação de um
 *  planeta muito maior. No mobile sobe para o topo (o card fica abaixo, no DOM). */
const PLACEMENT: Record<Breakpoint, Placement> = {
  desktop: { position: [-6, -2, 0], scale: 1.35 },
  notebook: { position: [-5.4, -2.15, 0], scale: 1.26 },
  tablet: { position: [-3.3, -3.1, 0], scale: 1.16 },
  mobile: { position: [0, 3.1, 0], scale: 0.85 },
};

function CameraParallax({
  pointer,
  enabled,
}: {
  pointer: RefObject<Pointer>;
  enabled: boolean;
}) {
  useFrame((state) => {
    if (!enabled) return;
    const target = pointer.current;
    const targetX = target.x * 0.5;
    const targetY = -target.y * 0.35;
    state.camera.position.x += (targetX - state.camera.position.x) * 0.03;
    state.camera.position.y += (targetY - state.camera.position.y) * 0.03;
    state.camera.lookAt(0, 0, 0);
  });
  return null;
}

export function PlanetScene() {
  const { breakpoint, quality } = useBreakpoint();
  const reducedMotion = usePrefersReducedMotion();
  const pointer = usePointerParallax();
  const animate = !reducedMotion;

  const radialTexture = useMemo(() => createRadialTexture(256), []);
  const nebulaTexture = useMemo(() => createNebulaTexture(1024), []);
  const placement = PLACEMENT[breakpoint];

  return (
    <Canvas
      dpr={quality.dpr}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      camera={{ position: [0, 0, 16], fov: 32 }}
      onCreated={({ gl }) => gl.setClearColor(palette.spaceVoid, 1)}
    >
      <Suspense fallback={null}>
        <Starfield count={quality.starCount} animate={animate} />
        <Nebula texture={nebulaTexture} animate={animate} />
        <PlanetLights animate={animate} />
        <group position={placement.position} scale={placement.scale}>
          <PlanetSystem radialTexture={radialTexture} quality={quality} animate={animate} />
        </group>
        <CameraParallax pointer={pointer} enabled={animate} />
        {quality.bloom && <PostProcessing intensity={quality.bloomIntensity} />}
      </Suspense>
    </Canvas>
  );
}
