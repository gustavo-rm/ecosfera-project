import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import type { DirectionalLight } from 'three';
import { SUN_DIRECTION } from '@/lib/three/config';

const BASE_INTENSITY = 2.8;

/** Sol vivo: luz direcional no canto superior direito com pulsação de
 *  intensidade extremamente discreta. É a fonte que ilumina o planeta,
 *  reflete nos oceanos e acende o halo na borda da atmosfera. */
export function SunLight({ animate }: { animate: boolean }) {
  const ref = useRef<DirectionalLight>(null);

  useFrame((state) => {
    const light = ref.current;
    if (!light) return;
    const pulse = animate ? Math.sin(state.clock.elapsedTime * 0.5) * 0.22 : 0;
    light.intensity = BASE_INTENSITY + pulse;
  });

  return (
    <directionalLight
      ref={ref}
      position={SUN_DIRECTION}
      intensity={BASE_INTENSITY}
      color="#fff3e0"
    />
  );
}
