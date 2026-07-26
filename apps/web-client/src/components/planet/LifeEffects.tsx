import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import {
  AdditiveBlending,
  Color,
  type Sprite,
  type SpriteMaterial,
  type Texture,
  Vector3,
} from 'three';
import { useLifeEvents } from '@/hooks/useLifeEvents';
import { pulseEnvelope } from '@/lib/three/math';
import { color, palette } from '@/lib/three/colors';
import { LIFE_MAX_CONCURRENT, PLANET_RADIUS } from '@/lib/three/config';

interface LifeEffectsProps {
  landPoints: readonly Vector3[];
  texture: Texture;
  animate: boolean;
}

const BIO = color(palette.bio);
const BIO_BRIGHT = color(palette.bioBright);

/** Focos luminosos de "vida surgindo": nascem sobre continentes, crescem,
 *  permanecem alguns segundos e desaparecem. São filhos do grupo que rotaciona
 *  com a superfície, portanto acompanham os continentes. */
export function LifeEffects({ landPoints, texture, animate }: LifeEffectsProps) {
  const controller = useLifeEvents(landPoints, PLANET_RADIUS, animate);
  const sprites = useRef<Array<Sprite | null>>([]);
  const scratch = useMemo(() => new Color(), []);

  useFrame((_, delta) => {
    controller.update(delta);
    for (let i = 0; i < controller.sparks.length; i++) {
      const spark = controller.sparks[i];
      const sprite = sprites.current[i];
      if (!spark || !sprite) continue;
      if (!spark.active) {
        sprite.visible = false;
        continue;
      }
      const envelope = pulseEnvelope(spark.age / spark.ttl);
      sprite.visible = true;
      sprite.position.copy(spark.position);
      sprite.scale.setScalar(spark.scale * (0.35 + envelope * 0.65));
      const material = sprite.material as SpriteMaterial;
      material.opacity = envelope;
      material.color.copy(scratch.copy(BIO).lerp(BIO_BRIGHT, spark.tint));
    }
  });

  return (
    <group>
      {Array.from({ length: LIFE_MAX_CONCURRENT }, (_, i) => (
        <sprite
          key={i}
          ref={(el) => {
            sprites.current[i] = el;
          }}
          visible={false}
        >
          <spriteMaterial
            map={texture}
            transparent
            depthWrite={false}
            blending={AdditiveBlending}
            opacity={0}
          />
        </sprite>
      ))}
    </group>
  );
}
