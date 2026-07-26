import { useFrame } from '@react-three/fiber';

interface PulseUniforms {
  uTime: { value: number };
  uIntensity: { value: number };
}

interface PulseOptions {
  base: number;
  amplitude: number;
  speed: number;
  enabled?: boolean;
}

/**
 * Faz a atmosfera "respirar": atualiza o tempo do shader e oscila suavemente a
 * intensidade do glow em torno de um valor base.
 */
export function useAtmospherePulse(uniforms: PulseUniforms, options: PulseOptions): void {
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    uniforms.uTime.value = t;
    const active = options.enabled === false ? 0 : 1;
    uniforms.uIntensity.value =
      options.base + Math.sin(t * options.speed) * options.amplitude * active;
  });
}
