import { useMemo } from 'react';
import { AdditiveBlending, FrontSide, Vector3 } from 'three';
import { atmosphereFragmentShader, atmosphereVertexShader } from '@/lib/three/shaders';
import { color, palette } from '@/lib/three/colors';
import { ATMOSPHERE_SCALE, PLANET_RADIUS, SUN_DIRECTION } from '@/lib/three/config';
import { useAtmospherePulse } from '@/hooks/useAtmospherePulse';

/** Halo atmosférico via Fresnel aditivo: brilha nas bordas, esquenta no lado
 *  do Sol e "respira" lentamente. */
export function Atmosphere({ animate }: { animate: boolean }) {
  const uniforms = useMemo(
    () => ({
      uColor: { value: color(palette.atmosphere).clone() },
      uSunColor: { value: color(palette.atmosphereBright).clone() },
      uSunDirection: { value: new Vector3(...SUN_DIRECTION).normalize() },
      uIntensity: { value: 1 },
      uPower: { value: 3.2 },
      uTime: { value: 0 },
    }),
    [],
  );

  useAtmospherePulse(uniforms, {
    base: 1,
    amplitude: 0.18,
    speed: 0.8,
    enabled: animate,
  });

  return (
    <mesh scale={PLANET_RADIUS * ATMOSPHERE_SCALE}>
      <sphereGeometry args={[1, 64, 64]} />
      <shaderMaterial
        vertexShader={atmosphereVertexShader}
        fragmentShader={atmosphereFragmentShader}
        uniforms={uniforms}
        transparent
        blending={AdditiveBlending}
        side={FrontSide}
        depthWrite={false}
      />
    </mesh>
  );
}
