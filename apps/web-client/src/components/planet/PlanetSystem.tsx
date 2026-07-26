import { useEffect, useMemo, useRef } from 'react';
import { AdditiveBlending, type Group, type Texture } from 'three';
import { PlanetMesh } from './PlanetMesh';
import { CloudLayer } from './CloudLayer';
import { Atmosphere } from './Atmosphere';
import { LifeEffects } from './LifeEffects';
import { LifeEmergence } from './LifeEmergence';
import { AtmosphericDust } from './AtmosphericDust';
import { usePlanetRotation } from '@/hooks/usePlanetRotation';
import {
  createCloudTexture,
  createLifeSymbolTexture,
  generatePlanetTextures,
} from '@/lib/three/textures';
import { palette } from '@/lib/three/colors';
import {
  CLOUD_ROTATION_PERIOD_S,
  GLOW_SCALE,
  PLANET_RADIUS,
  PLANET_ROTATION_PERIOD_S,
  PLANET_TILT,
  type QualitySettings,
} from '@/lib/three/config';

interface PlanetSystemProps {
  radialTexture: Texture;
  quality: QualitySettings;
  animate: boolean;
}

/** Compõe o planeta completo: glow externo, superfície + vida (girando com os
 *  continentes), nuvens (rotação própria), atmosfera e poeira. */
export function PlanetSystem({ radialTexture, quality, animate }: PlanetSystemProps) {
  const surfaceRef = useRef<Group>(null);
  const cloudRef = useRef<Group>(null);
  const emissiveBoostRef = useRef(0);

  const planet = useMemo(
    () => generatePlanetTextures(quality.textureSize),
    [quality.textureSize],
  );
  const cloudTexture = useMemo(
    () => createCloudTexture(quality.textureSize),
    [quality.textureSize],
  );
  const symbolTexture = useMemo(() => createLifeSymbolTexture(128), []);

  const speed = animate ? 1 : 0.12;
  usePlanetRotation(surfaceRef, PLANET_ROTATION_PERIOD_S, speed);
  usePlanetRotation(cloudRef, CLOUD_ROTATION_PERIOD_S, speed);

  useEffect(
    () => () => {
      planet.surface.dispose();
      planet.emissive.dispose();
      planet.roughness.dispose();
      cloudTexture.dispose();
      symbolTexture.dispose();
    },
    [planet, cloudTexture, symbolTexture],
  );

  return (
    <group rotation={[0, 0, PLANET_TILT]}>
      <sprite scale={PLANET_RADIUS * GLOW_SCALE} position={[0, 0, -0.6]}>
        <spriteMaterial
          map={radialTexture}
          color={palette.atmosphere}
          transparent
          opacity={0.55}
          depthWrite={false}
          blending={AdditiveBlending}
        />
      </sprite>

      <group ref={surfaceRef}>
        <PlanetMesh
          surface={planet.surface}
          emissive={planet.emissive}
          roughnessMap={planet.roughness}
          segments={quality.sphereSegments}
          emissiveBoostRef={emissiveBoostRef}
        />
        <LifeEffects landPoints={planet.landPoints} texture={radialTexture} animate={animate} />
        <LifeEmergence
          landPoints={planet.landPoints}
          symbolTexture={symbolTexture}
          haloTexture={radialTexture}
          emissiveBoostRef={emissiveBoostRef}
          animate={animate}
        />
      </group>

      <group ref={cloudRef}>
        <CloudLayer texture={cloudTexture} segments={quality.sphereSegments} />
      </group>

      <Atmosphere animate={animate} />
      <AtmosphericDust count={quality.dustCount} texture={radialTexture} animate={animate} />
    </group>
  );
}
