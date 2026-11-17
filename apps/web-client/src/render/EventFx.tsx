"use client";
import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import { Color, DoubleSide, DynamicDrawUsage, InstancedMesh, Matrix4, Mesh, MeshBasicMaterial, Quaternion, RingGeometry, SphereGeometry, Vector3 } from "three";
import { getMesh } from "@/core/mesh/geodesic";
import { usePlanetStore } from "@/store/planetStore";
import { runtime } from "./quality";

const PUFFS = 48, RINGS = 4;
/**
 * 3D parts of event effects (RF-056). The surface effects (lava, burn, ash, crater, shock wave) live in the surface shader.
 * Here: ash column and smoke as soft puffs, the incoming meteor, and warning rings during the telegraph phase.
 * No flashing: everything moves slowly and stays still under reduced motion (WCAG 2.3.1).
 */
export function EventFx({ reducedMotion }: { reducedMotion: boolean }) {
  const o = useMemo(() => {
    const puffs = new InstancedMesh(new SphereGeometry(1, 8, 6), new MeshBasicMaterial({ transparent: true, opacity: 0.5, depthWrite: false }), PUFFS);
    puffs.instanceMatrix.setUsage(DynamicDrawUsage); puffs.count = 0; puffs.frustumCulled = false; puffs.renderOrder = 5;
    const rings = Array.from({ length: RINGS }, () => { const m = new Mesh(new RingGeometry(0.9, 1, 40), new MeshBasicMaterial({ color: "#ffd866", transparent: true, opacity: 0.7, side: DoubleSide, depthWrite: false })); m.visible = false; m.renderOrder = 6; return m; });
    const meteor = new Mesh(new SphereGeometry(0.012, 8, 6), new MeshBasicMaterial({ color: "#ffe9c4" })); meteor.visible = false;
    return { puffs, rings, meteor, m: new Matrix4(), q: new Quaternion(), p: new Vector3(), s: new Vector3(), up: new Vector3(0, 0, 1), n: new Vector3(), ash: new Color("#6b6660"), smoke: new Color("#8b8680") };
  }, []);
  useFrame(() => {
    const st = usePlanetStore.getState(), frame = st.frame;
    let k = 0, r = 0;
    o.meteor.visible = false;
    if (frame && st.layer === null) {
      const c = getMesh(frame.level).centers, time = st.still || reducedMotion ? 0.35 : runtime.time;
      for (const e of frame.events) {
        o.n.set(c[e.cell * 3], c[e.cell * 3 + 1], c[e.cell * 3 + 2]);
        if (e.phase === "telegraph" && e.origin !== "background" && r < RINGS) {
          const ring = o.rings[r++], pulse = st.still || reducedMotion ? 1 : 0.85 + 0.15 * Math.sin(time * 1.5);
          ring.visible = true; ring.position.copy(o.n).multiplyScalar(1.03); ring.quaternion.setFromUnitVectors(o.up, o.n);
          ring.scale.setScalar(Math.sin((e.radiusDeg * Math.PI) / 180) * 0.6 * pulse);
          if (e.type === "impact") { const left = Math.max(0, (e.startTick - frame.tick) / Math.max(1, e.startTick - e.telegraphTick)); o.meteor.visible = true; o.meteor.position.copy(o.n).multiplyScalar(1.15 + left * 2.2).addScaledVector(o.up, left * 0.8); }
        }
        const column = e.type === "volcanism" && e.intensity > 0.05 ? 9 : e.type === "fire" && e.intensity > 0.1 ? 4 : e.type === "impact" && e.phase === "active" ? 10 : 0;
        for (let j = 0; j < column && k < PUFFS; j++) {
          const rise = ((j / column + time * 0.05) % 1), size = (0.012 + 0.03 * rise) * (e.type === "fire" ? 0.6 : 1) * (0.5 + 0.5 * e.intensity);
          o.p.copy(o.n).multiplyScalar(1.02 + rise * (e.type === "fire" ? 0.05 : 0.14)); o.p.x += Math.sin(j * 2.4) * 0.02 * rise; o.p.z += Math.cos(j * 1.7) * 0.02 * rise;
          o.m.compose(o.p, o.q, o.s.set(size, size, size)); o.puffs.setMatrixAt(k, o.m); o.puffs.setColorAt(k, e.type === "fire" ? o.smoke : o.ash); k++;
        }
      }
    }
    for (let i = r; i < RINGS; i++) o.rings[i].visible = false;
    o.puffs.count = k;
    if (k) { o.puffs.instanceMatrix.needsUpdate = true; if (o.puffs.instanceColor) o.puffs.instanceColor.needsUpdate = true; }
  });
  return <><primitive object={o.puffs} />{o.rings.map((ring, i) => <primitive key={i} object={ring} />)}<primitive object={o.meteor} /></>;
}
