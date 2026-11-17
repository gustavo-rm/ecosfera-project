"use client";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Color, ConeGeometry, DynamicDrawUsage, IcosahedronGeometry, InstancedMesh, Matrix4, MeshLambertMaterial, Quaternion, TetrahedronGeometry, Vector3, type BufferGeometry } from "three";
import { HEIGHT_SCALE_M } from "@/core/appearance/appearance";
import { hash4 } from "@/core/math/rng";
import { getMesh } from "@/core/mesh/geodesic";
import type { PlanetFrame, SpeciesRecord } from "@/core/state/types";
import { usePlanetStore } from "@/store/planetStore";
import { runtime } from "./quality";

/**
 * Abstract representation of cohorts, never articulated creatures (spec NO-03). One instanced mesh per trophic group:
 * producers are tufts (cones), herbivores are rounded bodies, carnivores are pointed bodies.
 * Scale comes from adult mass (log), color and two-tone pattern from the appearance marker, amount from density.
 * The budget is per view: only cells in front of the camera receive instances.
 */
export const ZOOM_THRESHOLD = 0.3;
const GROUP_SHARE = [0.62, 0.28, 0.1];

export function appearanceColors(tag: number[]): [Color, Color] {
  const a = new Color().setHSL(((tag[0] * 8 + tag[1]) % 64) / 64, 0.45 + (tag[2] / 8) * 0.4, 0.42 + (tag[3] / 8) * 0.25);
  const b = new Color().setHSL(((tag[4] * 8 + tag[5]) % 64) / 64, 0.5, 0.3 + (tag[2] / 8) * 0.3);
  return [a, b];
}
export const organismScale = (s: SpeciesRecord) => 0.006 * (1 + 0.16 * (Math.log10(Math.max(1e-6, s.phenotype.adult_mass as number)) + 6));

export function Organisms({ budget }: { budget: number }) {
  const geometries = useMemo<BufferGeometry[]>(() => {
    const cone = new ConeGeometry(0.55, 1.6, 5); cone.translate(0, 0.8, 0);
    const blob = new IcosahedronGeometry(0.6, 0); blob.scale(1.3, 0.75, 1); blob.translate(0, 0.45, 0);
    const dart = new TetrahedronGeometry(0.7, 0); dart.scale(1.7, 0.7, 0.8); dart.translate(0, 0.5, 0);
    return [cone, blob, dart];
  }, []);
  const material = useMemo(() => new MeshLambertMaterial(), []);
  const meshes = useMemo(() => geometries.map((g, i) => { const m = new InstancedMesh(g, material, Math.max(1, Math.ceil(budget * GROUP_SHARE[i]))); m.instanceMatrix.setUsage(DynamicDrawUsage); m.count = 0; m.frustumCulled = false; return m; }), [geometries, material, budget]);
  const tmp = useMemo(() => ({ m: new Matrix4(), q: new Quaternion(), up: new Vector3(0, 1, 0), n: new Vector3(), p: new Vector3(), s: new Vector3(), cam: new Vector3(), t1: new Vector3(), t2: new Vector3(), colors: new Map<string, [Color, Color]>() }), []);
  const state = useRef({ last: 0, frame: null as PlanetFrame | null, camKey: "" });

  useFrame(({ camera }) => {
    if (budget <= 0) return;
    const st = usePlanetStore.getState(), frame = st.frame, now = performance.now();
    const group = meshes[0].parent;
    const show = !!frame && runtime.zoom > ZOOM_THRESHOLD && frame.meta.mode === "normal" && st.layer === null && frame.globals.surfaceHeat < 0.3;
    if (!show || !group) { if (meshes[0].count) for (const m of meshes) m.count = 0; state.current.frame = null; return; }
    tmp.cam.copy(camera.position); group.worldToLocal(tmp.cam);
    const r = tmp.cam.length(); tmp.cam.normalize();
    const camKey = `${tmp.cam.x.toFixed(2)},${tmp.cam.y.toFixed(2)},${tmp.cam.z.toFixed(2)},${r.toFixed(1)}`;
    if (state.current.frame === frame && state.current.camKey === camKey) return;
    if (now - state.current.last < 350) return;
    state.current = { last: now, frame, camKey };

    const mesh = getMesh(frame.level), c = mesh.centers, f = frame.fields, n = frame.cellCount;
    const cosA = Math.cos(Math.min(Math.acos(1 / r), 0.5 * (r - 1) + 0.06));
    const cellRadius = Math.sqrt(4 / n) * 0.75, sea = frame.globals.seaLevelM < -9e4 ? 0 : frame.globals.seaLevelM, exag = st.exaggeration;
    const fields = [f.biomassPhoto, f.biomassHerb, f.biomassCarn], doms = [f.domProducer, f.domHerb, f.domCarn];
    const byIndex = new Map(frame.bio.species.map((s) => [s.index, s]));
    for (let gi = 0; gi < 3; gi++) {
      const im = meshes[gi], cap = im.instanceMatrix.count, field = fields[gi], dom = doms[gi];
      let total = 0;
      for (let i = 0; i < n; i++) if (dom[i] >= 0 && c[i * 3] * tmp.cam.x + c[i * 3 + 1] * tmp.cam.y + c[i * 3 + 2] * tmp.cam.z > cosA && (gi > 0 || !f.isWater[i])) total += field[i];
      let k = 0;
      if (total > 0) for (let i = 0; i < n && k < cap; i++) {
        if (dom[i] < 0 || (gi === 0 && f.isWater[i])) continue;
        if (c[i * 3] * tmp.cam.x + c[i * 3 + 1] * tmp.cam.y + c[i * 3 + 2] * tmp.cam.z <= cosA) continue;
        const sp = byIndex.get(dom[i]);
        if (!sp) continue;
        const want = (field[i] / total) * cap, count = Math.floor(want) + (hash4(i, gi, 3, 9) < want % 1 ? 1 : 0);
        if (!count) continue;
        let cols = tmp.colors.get(sp.id);
        if (!cols) { cols = appearanceColors(sp.phenotype.appearance_tag as number[]); tmp.colors.set(sp.id, cols); }
        const scale = organismScale(sp) * (gi === 0 ? 1 + Math.min(2, (sp.phenotype.height as number) / 12) : 1);
        const radius = 1 + (f.isWater[i] ? 0 : Math.max(0, (f.elevation[i] - sea) / HEIGHT_SCALE_M) * exag) + 0.001;
        tmp.n.set(c[i * 3], c[i * 3 + 1], c[i * 3 + 2]);
        tmp.t1.set(0, 1, 0.001).cross(tmp.n).normalize(); tmp.t2.copy(tmp.n).cross(tmp.t1);
        for (let j = 0; j < count && k < cap; j++) {
          const a = hash4(i, j, gi, 1) * 6.283, d = Math.sqrt(hash4(i, j, gi, 2)) * cellRadius;
          tmp.p.copy(tmp.n).addScaledVector(tmp.t1, Math.cos(a) * d).addScaledVector(tmp.t2, Math.sin(a) * d).normalize();
          tmp.q.setFromUnitVectors(tmp.up, tmp.p);
          const sc = scale * (0.75 + 0.5 * hash4(i, j, gi, 4));
          tmp.m.compose(tmp.p.multiplyScalar(radius), tmp.q, tmp.s.set(sc, sc, sc));
          im.setMatrixAt(k, tmp.m); im.setColorAt(k, cols[(i + j) % 3 === 0 ? 1 : 0]);
          k++;
        }
      }
      im.count = k; im.instanceMatrix.needsUpdate = true; if (im.instanceColor) im.instanceColor.needsUpdate = true;
    }
  });
  return <>{meshes.map((m, i) => <primitive key={i} object={m} />)}</>;
}
