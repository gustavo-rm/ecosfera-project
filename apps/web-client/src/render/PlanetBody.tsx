"use client";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, DataTexture, DoubleSide, DynamicDrawUsage, LinearFilter, Matrix4, RGBAFormat, ShaderMaterial,
  Vector3, Vector4, type Group, type IUniform, type Mesh,
} from "three";
import { axisEuler, computeAppearance, createAppearance, type PlanetUniforms } from "@/core/appearance/appearance";
import { buildLut, DIVERGING, SEQUENTIAL, type PaletteSet } from "@/core/appearance/palettes";
import { expandToRenderLevel, getMesh } from "@/core/mesh/geodesic";
import { usePlanetStore } from "@/store/planetStore";
import { CELL_VERTEX } from "./shaders/common";
import { ATMOSPHERE_FRAGMENT, AURORA_FRAGMENT, AURORA_VERTEX, CLOUD_FRAGMENT, SHELL_VERTEX } from "./shaders/sky";
import { SURFACE_FRAGMENT } from "./shaders/surface";
import { perfStats, runtime } from "./quality";

const CHANNELS = ["A", "B", "C", "D"] as const;
// Module-level helpers: nothing is created inside the render loop.
const lerp3 = (u: IUniform, c: [number, number, number], k: number) => { const v = u.value as Vector3; v.x += (c[0] - v.x) * k; v.y += (c[1] - v.y) * k; v.z += (c[2] - v.z) * k; };
const damp = (u: IUniform, v: number, k: number) => { u.value += (v - u.value) * k; };
const BLEND_SECONDS = 0.9, ERA_FADE_SECONDS = 1.6;
type U = Record<string, IUniform>;

/** One-shot visual feedback at a point (RNF-002): call it the moment the student acts, before the new state arrives. */
export const feedback = { rippleCell: -1, rippleStart: -1, trigger(cell: number) { this.rippleCell = cell; this.rippleStart = performance.now(); } };

export function PlanetBody({ planetRef, renderOffset, octaves, paletteSet, reducedMotion, children }: { planetRef: React.RefObject<Group | null>; renderOffset: number; octaves: number; paletteSet: PaletteSet; reducedMotion: boolean; children?: React.ReactNode }) {
  const dataLevel = usePlanetStore((s) => s.frame?.level ?? 5);
  const showClouds = usePlanetStore((s) => s.showClouds && s.layer === null);
  const { camera, gl } = useThree();
  const tilt = useRef<Group>(null), shell = useRef<Mesh>(null);
  const dataMesh = useMemo(() => getMesh(dataLevel), [dataLevel]);
  const renderMesh = useMemo(() => getMesh(Math.max(2, Math.min(6, dataLevel + renderOffset))), [dataLevel, renderOffset]);

  const gpu = useMemo(() => {
    const n = renderMesh.count, geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(renderMesh.centers, 3));
    geometry.setIndex(new BufferAttribute(renderMesh.indices, 1));
    const attrs: Record<string, BufferAttribute> = {};
    for (const c of CHANNELS) for (const k of [0, 1]) {
      const a = new BufferAttribute(new Float32Array(n * 4), 4); a.setUsage(DynamicDrawUsage);
      geometry.setAttribute(`a${c}${k}`, a); attrs[`${c}${k}`] = a;
    }
    const grad = new BufferAttribute(new Float32Array(n * 3), 3); grad.setUsage(DynamicDrawUsage);
    geometry.setAttribute("aGrad", grad);
    perfStats.attributeBytes = n * (8 * 16 + 12 + 12) + renderMesh.indices.byteLength;
    return { geometry, attrs, grad, scratch: new Float32Array(n * 4), app: createAppearance(dataMesh.count), first: true, blendStart: -1e9, blendDur: BLEND_SECONDS, synced: { A: true, B: true, C: true, D: true }, lastTick: 0, target: null as PlanetUniforms | null, uploads: 0 };
  }, [renderMesh, dataMesh]);
  useEffect(() => () => gpu.geometry.dispose(), [gpu]);

  const luts = useMemo(() => {
    const make = (name: string) => { const t = new DataTexture(buildLut(name), 256, 1, RGBAFormat); t.minFilter = t.magFilter = LinearFilter; t.needsUpdate = true; return t; };
    return { sequential: make(SEQUENTIAL[paletteSet]), diverging: make(DIVERGING[paletteSet]) };
  }, [paletteSet]);
  useEffect(() => () => { luts.sequential.dispose(); luts.diverging.dispose(); }, [luts]);

  const mats = useMemo(() => {
    const shared: U = {
      uBlend: { value: 1 }, uExag: { value: 0.07 }, uTime: { value: 0 }, uSeed: { value: 0 }, uSunDir: { value: new Vector3(1, 0, 0) }, uCamPos: { value: new Vector3(0, 0, 4) },
      uSkyColor: { value: new Vector3(0.3, 0.5, 1) }, uStarColor: { value: new Vector3(1, 1, 1) }, uSunDim: { value: 1 }, uAtmo: { value: 0.5 },
    };
    const surface = new ShaderMaterial({
      vertexShader: CELL_VERTEX, fragmentShader: SURFACE_FRAGMENT, defines: { OCTAVES: octaves },
      uniforms: {
        ...shared, uShell: { value: 0 }, uOceanShallow: { value: new Vector3() }, uOceanDeep: { value: new Vector3() }, uZoom: { value: 0 }, uHaze: { value: 0 }, uTermSoft: { value: 0.2 },
        uStarInt: { value: 1 }, uSurfaceHeat: { value: 0 }, uDesat: { value: 0 }, uLayerMode: { value: 0 }, uLayerOpacity: { value: 0 }, uHighlightPulse: { value: 0 }, uLut: { value: luts.sequential },
        uRipple: { value: new Vector4(0, 1, 0, -1) }, uShock: { value: new Vector4(0, 1, 0, -1) }, uSelect: { value: new Vector4(0, 1, 0, 0) },
      },
    });
    const clouds = new ShaderMaterial({
      vertexShader: CELL_VERTEX, fragmentShader: CLOUD_FRAGMENT, defines: { OCTAVES: Math.min(octaves, 4) }, transparent: true, depthWrite: false,
      uniforms: { ...shared, uShell: { value: 0.03 }, uCloudColor: { value: new Vector3(1, 1, 1) }, uCloudOpacity: { value: 0.6 }, uFlash: { value: 0 }, uStorms: { value: [new Vector4(), new Vector4(), new Vector4()] } },
    });
    const atmosphere = new ShaderMaterial({
      vertexShader: SHELL_VERTEX, fragmentShader: ATMOSPHERE_FRAGMENT, defines: { OCTAVES: 2 }, transparent: true, depthWrite: false,
      uniforms: { ...shared, uScale: { value: 0.03 }, uErosion: { value: 0 } },
    });
    const aurora = new ShaderMaterial({
      vertexShader: AURORA_VERTEX, fragmentShader: AURORA_FRAGMENT, defines: { OCTAVES: 2 }, transparent: true, depthWrite: false, blending: AdditiveBlending, side: DoubleSide,
      uniforms: { uAurora: { value: 0 }, uTime: shared.uTime, uSunDir: shared.uSunDir },
    });
    return { surface, clouds, atmosphere, aurora, shared };
  }, [octaves, luts]);
  useEffect(() => () => { mats.surface.dispose(); mats.clouds.dispose(); mats.atmosphere.dispose(); mats.aurora.dispose(); }, [mats]);

  // ---- state -> GPU. Runs only when the frame or the view options change, never per rendered frame.
  useEffect(() => {
    const apply = () => {
      const st = usePlanetStore.getState(), frame = st.frame;
      if (!frame || frame.level !== dataMesh.level) return;
      const app = computeAppearance(frame, dataMesh, { layer: st.layer, revealed: st.revealed, showHabitat: !!st.selectedSpecies }, gpu.app);
      const now = performance.now() / 1000;
      const blend = gpu.first || st.still ? 1 : Math.min(1, (now - gpu.blendStart) / gpu.blendDur);
      const eased = blend * blend * (3 - 2 * blend);
      let changedAny = false;
      const changed: Record<string, boolean> = {};
      for (const c of CHANNELS) {
        expandToRenderLevel(app[c], dataMesh, renderMesh, 4, gpu.scratch);
        const next = gpu.attrs[`${c}1`].array as Float32Array;
        let diff = gpu.first;
        if (!diff) for (let i = 0; i < next.length; i++) if (next[i] !== gpu.scratch[i]) { diff = true; break; }
        changed[c] = diff; changedAny ||= diff;
        if (diff) {
          const prev = gpu.attrs[`${c}0`].array as Float32Array;
          if (gpu.first || st.still) prev.set(gpu.scratch); else for (let i = 0; i < prev.length; i++) prev[i] += (next[i] - prev[i]) * eased;
          next.set(gpu.scratch);
          gpu.attrs[`${c}0`].needsUpdate = true; gpu.attrs[`${c}1`].needsUpdate = true; gpu.synced[c] = gpu.first || st.still; gpu.uploads += 2;
        }
      }
      if (changedAny && !gpu.first && !st.still) {
        // Unchanged channels keep their image: bake the running blend into "prev" so restarting the blend is seamless.
        for (const c of CHANNELS) if (!changed[c] && !gpu.synced[c]) {
          const prev = gpu.attrs[`${c}0`].array as Float32Array, next = gpu.attrs[`${c}1`].array as Float32Array;
          for (let i = 0; i < prev.length; i++) prev[i] += (next[i] - prev[i]) * eased;
          gpu.attrs[`${c}0`].needsUpdate = true; gpu.synced[c] = blend >= 1; gpu.uploads++;
        }
        gpu.blendDur = Math.abs(frame.tick - gpu.lastTick) > 600 ? ERA_FADE_SECONDS : BLEND_SECONDS; // jumps between eras fade longer
        gpu.blendStart = now;
      }
      expandToRenderLevel(app.grad, dataMesh, renderMesh, 3, gpu.grad.array as Float32Array);
      gpu.grad.needsUpdate = true;
      gpu.lastTick = frame.tick; gpu.target = app.uniforms; gpu.first = false;
      const storms = mats.clouds.uniforms.uStorms.value as Vector4[];
      const list = frame.events.filter((e) => e.type === "storm" && e.intensity > 0.05).sort((a, b) => b.intensity - a.intensity);
      for (let k = 0; k < 3; k++) { const e = list[k]; if (e) storms[k].set(dataMesh.centers[e.cell * 3], dataMesh.centers[e.cell * 3 + 1], dataMesh.centers[e.cell * 3 + 2], e.intensity); else storms[k].w = 0; }
    };
    gpu.first = true;
    apply();
    return usePlanetStore.subscribe((s, p) => { if (s.frame !== p.frame || s.layer !== p.layer || s.revealed !== p.revealed || s.selectedSpecies !== p.selectedSpecies || s.still !== p.still) apply(); });
  }, [gpu, dataMesh, renderMesh, mats]);

  const tmp = useMemo(() => ({ inv: new Matrix4(), sun: new Vector3(), cam: new Vector3(), spin: 0, orbit: 0, flashAt: 0, flash: 0, shockEvent: "" }), []);
  useFrame((state, dt) => {
    const st = usePlanetStore.getState(), t = gpu.target, group = planetRef.current;
    if (!t || !group || !tilt.current) return;
    const still = st.still, d = Math.min(dt, 0.1), k = still ? 1 : 1 - Math.exp(-d / 0.6);
    // Reduced motion: shader time stands still (no waves, drifting clouds, lava flicker or aurora ribbons).
    const time = still || reducedMotion ? 0 : state.clock.elapsedTime;
    runtime.time = time;
    const sh = mats.shared, su = mats.surface.uniforms, cu = mats.clouds.uniforms, au = mats.atmosphere.uniforms;
    // Orbit and rotation (stylized pacing: one planet day takes a minute at 24 h; see the legend).
    // The star stays fixed in the scene and the tilted axis turns around it through the year, so seasons are
    // physically oriented while the lit side keeps facing the default camera.
    const axis = axisEuler(t.yearPhase, t.axialTiltDeg);
    tmp.orbit += Math.atan2(Math.sin(axis.y - tmp.orbit), Math.cos(axis.y - tmp.orbit)) * k;
    tilt.current.rotation.set(0, tmp.orbit, axis.z, "YZX");
    if (!still && !reducedMotion && st.playing) tmp.spin += (d * 2 * Math.PI) / (60 * Math.max(0.25, t.dayHours / 24));
    group.rotation.y = tmp.spin;
    group.updateWorldMatrix(true, false);
    tmp.inv.copy(group.matrixWorld).invert();
    (sh.uSunDir.value as Vector3).set(runtime.sunWorld[0], runtime.sunWorld[1], runtime.sunWorld[2]).transformDirection(tmp.inv);
    (sh.uCamPos.value as Vector3).copy(camera.position).applyMatrix4(tmp.inv);

    const blend = still ? 1 : Math.min(1, (performance.now() / 1000 - gpu.blendStart) / gpu.blendDur);
    sh.uBlend.value = blend * blend * (3 - 2 * blend);
    sh.uTime.value = time; sh.uSeed.value = (t.seed % 97) * 1.37;
    sh.uExag.value += (st.exaggeration - sh.uExag.value) * k;
    cu.uShell.value = sh.uExag.value * 0.62 + 0.012;
    const ecc = 1 + 2 * t.eccentricity * Math.cos(2 * Math.PI * t.yearPhase);
    lerp3(sh.uSkyColor, t.skyColor, k); lerp3(sh.uStarColor, t.starColor, k); lerp3(su.uOceanShallow, t.oceanShallow, k); lerp3(su.uOceanDeep, t.oceanDeep, k); lerp3(cu.uCloudColor, t.cloudColor, k);
    damp(sh.uSunDim, t.sunDim, k); damp(sh.uAtmo, t.atmoDensity, k); damp(su.uHaze, t.haze, k); damp(su.uTermSoft, t.terminatorSoftness, k); damp(su.uStarInt, t.starIntensity * ecc, k);
    damp(su.uSurfaceHeat, t.surfaceHeat, k); damp(su.uDesat, t.desaturate, k); damp(cu.uCloudOpacity, t.cloudOpacity, k); damp(au.uErosion, t.erosion, k); damp(mats.aurora.uniforms.uAurora, t.aurora, k);
    au.uScale.value = 0.018 + 0.03 * sh.uAtmo.value;
    // The shell is only as large as the glow needs: fewer shaded pixels. It grows when the atmosphere leaks (erosion tail).
    if (shell.current) { shell.current.visible = sh.uAtmo.value > 0.005; shell.current.scale.setScalar(au.uErosion.value > 0.01 ? 1.5 : 1.06 + 5 * au.uScale.value); }
    su.uLayerMode.value = t.layerMode; su.uLut.value = t.layerKind === "diverging" ? luts.diverging : luts.sequential;
    damp(su.uLayerOpacity, t.layerMode ? 0.94 : 0, k);
    runtime.zoom = Math.min(1, Math.max(0, (3.6 - runtime.cameraDistance) / 1.9));
    su.uZoom.value = runtime.zoom;
    su.uHighlightPulse.value = still || reducedMotion ? 0.5 : 0.5 + 0.5 * Math.sin(time * 2.2);

    // Selection ring and immediate feedback ripple.
    const c = dataMesh.centers, sel = su.uSelect.value as Vector4;
    if (st.selectedCell !== null && st.selectedCell < dataMesh.count) sel.set(c[st.selectedCell * 3], c[st.selectedCell * 3 + 1], c[st.selectedCell * 3 + 2], 0.035); else sel.w = 0;
    const rip = su.uRipple.value as Vector4, age = (performance.now() - feedback.rippleStart) / 1000;
    if (feedback.rippleCell >= 0 && age < 1 && feedback.rippleCell < dataMesh.count) rip.set(c[feedback.rippleCell * 3], c[feedback.rippleCell * 3 + 1], c[feedback.rippleCell * 3 + 2], reducedMotion ? 0.5 : age); else rip.w = -1;
    // Impact shock wave: one expanding ring over a few seconds, no flashing.
    const shock = su.uShock.value as Vector4, impact = st.frame?.events.find((e) => e.type === "impact" && e.phase === "active");
    if (impact && !still) {
      if (tmp.shockEvent !== impact.id) { tmp.shockEvent = impact.id; tmp.flashAt = time; }
      const r = (time - tmp.flashAt) * 0.35;
      if (r < Math.PI) shock.set(c[impact.cell * 3], c[impact.cell * 3 + 1], c[impact.cell * 3 + 2], reducedMotion ? 0.4 : r); else shock.w = -1;
    } else shock.w = -1;
    // Lightning: soft pulses, at most one every 0.8 s (WCAG 2.3.1 allows up to three flashes per second).
    const stormy = (cu.uStorms.value as Vector4[])[0].w > 0.2;
    cu.uFlash.value = stormy && !still && !reducedMotion ? Math.max(0, Math.sin((time % 0.8) / 0.8 * Math.PI)) * (Math.floor(time / 0.8) % 3 === 0 ? 0.55 : 0) : 0;

    perfStats.uploadsPerSecond = gpu.uploads; perfStats.drawCalls = gl.info.render.calls; perfStats.triangles = gl.info.render.triangles;
    perfStats.geometries = gl.info.memory.geometries; perfStats.textures = gl.info.memory.textures; perfStats.programs = gl.info.programs?.length ?? 0;
  });

  return (
    <group ref={tilt}>
      <group ref={planetRef}>
        <mesh geometry={gpu.geometry} material={mats.surface} frustumCulled={false} />
        <mesh geometry={gpu.geometry} material={mats.clouds} frustumCulled={false} renderOrder={2} visible={showClouds} />
        <mesh ref={shell} material={mats.atmosphere} renderOrder={3} scale={1.3}><sphereGeometry args={[1, 48, 32]} /></mesh>
        {[1, -1].map((sgn) => (
          <mesh key={sgn} material={mats.aurora} renderOrder={4} position={[0, sgn * 0.955, 0]} rotation={[sgn > 0 ? 0 : Math.PI, 0, 0]}>
            <cylinderGeometry args={[0.40, 0.33, 0.09, 64, 1, true]} />
          </mesh>
        ))}
        {children}
      </group>
    </group>
  );
}
