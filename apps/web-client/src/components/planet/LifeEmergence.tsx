import { useMemo, useRef, type RefObject } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import {
  AdditiveBlending,
  type Group,
  type Sprite,
  type SpriteMaterial,
  type Texture,
  Vector3,
} from 'three';
import { color, palette } from '@/lib/three/colors';
import {
  LIFE_EMERGENCE_BOOST,
  LIFE_EMERGENCE_FADE_IN_S,
  LIFE_EMERGENCE_FADE_OUT_S,
  LIFE_EMERGENCE_HOLD_S,
  LIFE_EMERGENCE_INTERVAL_S,
  PLANET_RADIUS,
} from '@/lib/three/config';

interface LifeEmergenceProps {
  landPoints: readonly Vector3[];
  symbolTexture: Texture;
  haloTexture: Texture;
  /** Compartilhado com o PlanetMesh: intensifica as redes durante o evento. */
  emissiveBoostRef: RefObject<number>;
  animate: boolean;
}

// A silhueta já traz cor/contraste na textura → material sem tingimento.
const SYMBOL_COLOR = color('#ffffff');
const HALO_COLOR = color(palette.cyan);
const SURFACE_OFFSET = PLANET_RADIUS * 1.03;
const HOLD_END = LIFE_EMERGENCE_FADE_IN_S + LIFE_EMERGENCE_HOLD_S;
const OUT_END = HOLD_END + LIFE_EMERGENCE_FADE_OUT_S;

function easeInOut(t: number): number {
  return t * t * (3 - 2 * t);
}

/**
 * Evento recorrente que simboliza o surgimento da vida. A cada 20 s escolhe uma
 * região *visível* do planeta e faz surgir suavemente um pequeno símbolo de
 * vida (silhueta), com halo próprio; ao mesmo tempo intensifica levemente as
 * redes biológicas. Tudo retorna ao normal ao fim do ciclo.
 *
 * O símbolo é filho do grupo que rotaciona com a superfície, portanto
 * acompanha o continente onde nasceu. A seleção de posição roda uma única vez
 * por ciclo (barata); o `useFrame` apenas interpola opacidade/escala.
 */
export function LifeEmergence({
  landPoints,
  symbolTexture,
  haloTexture,
  emissiveBoostRef,
  animate,
}: LifeEmergenceProps) {
  const rootRef = useRef<Group>(null);
  const symbolRef = useRef<Sprite>(null);
  const haloRef = useRef<Sprite>(null);
  const cycleRef = useRef(-1);
  const hasPositionRef = useRef(false);

  const camera = useThree((state) => state.camera);
  const worldPos = useMemo(() => new Vector3(), []);
  const worldNormal = useMemo(() => new Vector3(), []);
  const toCamera = useMemo(() => new Vector3(), []);
  const ndc = useMemo(() => new Vector3(), []);

  const selectPosition = () => {
    const root = rootRef.current;
    const surface = root?.parent;
    if (!root || !surface || landPoints.length === 0) {
      hasPositionRef.current = false;
      return;
    }
    surface.updateWorldMatrix(true, false);
    // Garante matrizes da câmera atualizadas (o primeiro frame pode chegar
    // antes de o renderer atualizar o inverso) para uma projeção confiável.
    camera.updateMatrixWorld();
    camera.matrixWorldInverse.copy(camera.matrixWorld).invert();

    for (let attempt = 0; attempt < 48; attempt++) {
      const point = landPoints[Math.floor(Math.random() * landPoints.length)];
      if (!point) continue;

      worldPos.copy(point).multiplyScalar(SURFACE_OFFSET).applyMatrix4(surface.matrixWorld);
      worldNormal.copy(point).transformDirection(surface.matrixWorld);
      toCamera.copy(camera.position).sub(worldPos);
      // Exige que o ponto encare bem a câmera (fica sobre o disco visível, não
      // no limbo rasante onde o símbolo ficaria pela metade).
      if (worldNormal.dot(toCamera) / toCamera.length() < 0.4) continue;

      // Mantém o símbolo sobre o corpo visível do planeta, longe das bordas
      // (onde ficaria cortado) e da área do cartão.
      ndc.copy(worldPos).project(camera);
      if (ndc.x < -0.88 || ndc.x > 0.88 || ndc.y < -0.76 || ndc.y > 0.86) continue;

      root.position.copy(point).multiplyScalar(SURFACE_OFFSET);
      hasPositionRef.current = true;
      return;
    }
    hasPositionRef.current = false;
  };

  useFrame((state) => {
    const root = rootRef.current;
    const symbol = symbolRef.current;
    const halo = haloRef.current;
    if (!root || !symbol || !halo) return;

    if (!animate) {
      root.visible = false;
      emissiveBoostRef.current = 0;
      return;
    }

    const elapsed = state.clock.elapsedTime;
    const cycle = Math.floor(elapsed / LIFE_EMERGENCE_INTERVAL_S);
    if (cycle !== cycleRef.current) {
      cycleRef.current = cycle;
      selectPosition();
    }

    const t = elapsed - cycle * LIFE_EMERGENCE_INTERVAL_S;
    // Rede de segurança: se nenhuma região visível foi encontrada no início do
    // ciclo (ex.: continentes no lado oposto), tenta novamente por um instante.
    if (!hasPositionRef.current && t < 2) selectPosition();
    let alpha = 0;
    if (t < LIFE_EMERGENCE_FADE_IN_S) alpha = easeInOut(t / LIFE_EMERGENCE_FADE_IN_S);
    else if (t < HOLD_END) alpha = 1;
    else if (t < OUT_END) alpha = easeInOut(1 - (t - HOLD_END) / LIFE_EMERGENCE_FADE_OUT_S);

    const visible = hasPositionRef.current && alpha > 0.001;
    root.visible = visible;
    if (visible) {
      const scale = 0.9 * (0.68 + 0.32 * alpha);
      symbol.scale.setScalar(scale);
      halo.scale.setScalar(scale * 2.8);
      (symbol.material as SpriteMaterial).opacity = alpha;
      (halo.material as SpriteMaterial).opacity = alpha * 0.8;
    }
    emissiveBoostRef.current = alpha * LIFE_EMERGENCE_BOOST;
  });

  return (
    <group ref={rootRef} visible={false}>
      <sprite ref={haloRef}>
        <spriteMaterial
          map={haloTexture}
          color={HALO_COLOR}
          transparent
          depthWrite={false}
          blending={AdditiveBlending}
          opacity={0}
        />
      </sprite>
      <sprite ref={symbolRef}>
        <spriteMaterial map={symbolTexture} color={SYMBOL_COLOR} transparent depthWrite={false} opacity={0} />
      </sprite>
    </group>
  );
}
