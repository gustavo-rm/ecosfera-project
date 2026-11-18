"use client";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { AdditiveBlending, BufferAttribute, BufferGeometry, ShaderMaterial, Vector3, type DirectionalLight, type Group, type Mesh } from "three";
import { mulberry32 } from "@/core/math/rng";
import { STAR_TABLE } from "@/core/state/catalogs";
import { usePlanetStore } from "@/store/planetStore";
import { runtime } from "./quality";
import { SUN_FRAGMENT, UV_VERTEX } from "./shaders/sky";

/** Star, moons and background stars. Everything is seeded: the same planet always has the same sky. */
export function Sky({ stars }: { stars: number }) {
  const seed = usePlanetStore((s) => s.frame?.params.seed ?? 1);
  const moons = usePlanetStore((s) => s.frame?.params.moons ?? 0);
  const starType = usePlanetStore((s) => s.frame?.params.starType ?? "G");
  const orbitAU = usePlanetStore((s) => s.frame?.params.orbitAU ?? 1);
  const sun = useRef<Mesh>(null), light = useRef<DirectionalLight>(null), moonGroup = useRef<Group>(null);
  const starGeometry = useMemo(() => {
    const rng = mulberry32(seed * 13 + 1), pos = new Float32Array(stars * 3), col = new Float32Array(stars * 3);
    for (let i = 0; i < stars; i++) {
      const z = rng() * 2 - 1, a = rng() * Math.PI * 2, r = Math.sqrt(1 - z * z), b = 0.35 + 0.65 * rng() ** 3, tint = rng();
      pos.set([r * Math.cos(a) * 90, z * 90, r * Math.sin(a) * 90], i * 3);
      col.set([b * (0.85 + 0.15 * tint), b * 0.92, b * (1 - 0.15 * tint)], i * 3);
    }
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(pos, 3)); g.setAttribute("color", new BufferAttribute(col, 3));
    return g;
  }, [seed, stars]);
  const sunMat = useMemo(() => new ShaderMaterial({ vertexShader: UV_VERTEX, fragmentShader: SUN_FRAGMENT, transparent: true, depthWrite: false, blending: AdditiveBlending, uniforms: { uStarColor: { value: new Vector3(1, 1, 1) }, uSunDim: { value: 1 } } }), []);
  const moonDefs = useMemo(() => { const rng = mulberry32(seed * 7 + 3); return Array.from({ length: 4 }, (_, i) => ({ radius: 1.9 + i * 0.55 + rng() * 0.2, size: 0.035 + rng() * 0.05, phase: rng() * 6.28, incl: (rng() - 0.5) * 0.5, period: 40 + i * 35 + rng() * 20 })); }, [seed]);

  useFrame((state) => {
    const star = STAR_TABLE[starType], [x, y, z] = runtime.sunWorld;
    if (sun.current) {
      sun.current.position.set(x * 60, y * 60, z * 60); sun.current.lookAt(state.camera.position);
      // Same apparent size the state -> appearance mapping reports (uniform starSize), in scene units.
      sun.current.scale.setScalar(Math.min(3.5, Math.max(0.25, (star.size / Math.max(0.1, orbitAU)) * 0.9)) * 7.5);
      (sunMat.uniforms.uStarColor.value as Vector3).set(star.color[0], star.color[1], star.color[2]);
    }
    light.current?.position.set(x * 10, y * 10, z * 10);
    if (moonGroup.current) moonGroup.current.children.forEach((m, i) => {
      const d = moonDefs[i], a = d.phase + (runtime.time * 2 * Math.PI) / d.period;
      m.position.set(Math.cos(a) * d.radius, Math.sin(a) * d.incl * d.radius, Math.sin(a) * d.radius);
    });
  });
  return (
    <>
      <points geometry={starGeometry} frustumCulled={false}><pointsMaterial size={1.6} sizeAttenuation={false} vertexColors transparent opacity={0.9} depthWrite={false} /></points>
      <mesh ref={sun} material={sunMat}><planeGeometry args={[1, 1]} /></mesh>
      <directionalLight ref={light} intensity={2.4} />
      <ambientLight intensity={0.04} />
      <group ref={moonGroup}>
        {moonDefs.slice(0, moons).map((d, i) => (
          <mesh key={i}><icosahedronGeometry args={[d.size, 2]} /><meshStandardMaterial color={i % 2 ? "#9a948c" : "#b9b4ad"} roughness={1} /></mesh>
        ))}
      </group>
    </>
  );
}
