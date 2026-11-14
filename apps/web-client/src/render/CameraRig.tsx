"use client";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { Vector2, Vector3, type Group } from "three";
import { getMesh, nearestCell } from "@/core/mesh/geodesic";
import { usePlanetStore } from "@/store/planetStore";
import { runtime } from "./quality";

export const CAMERA_LIMITS = { min: 1.45, max: 7, home: 3.9, focus: 2.05 };
/** Imperative camera API, used by keyboard handlers and UI buttons. */
const pending: (() => void)[] = [];
export const cameraApi = {
  rotate: (dTheta: number, dPhi: number) => { pending.push(() => cameraApi.rotate(dTheta, dPhi)); },
  zoom: (factor: number) => { pending.push(() => cameraApi.zoom(factor)); },
  reset: () => {}, pickCenter: () => {},
};

/** Orbit camera with inertia, wheel and pinch zoom, focus on a cell, auto-rotation at rest and full keyboard control (RF-053). */
export function CameraRig({ planet, interactive = true }: { planet: React.RefObject<Group | null>; interactive?: boolean }) {
  const { camera, gl, raycaster } = useThree();
  const s = useRef({ theta: 0.6, phi: 1.25, radius: CAMERA_LIMITS.home, tTheta: 0.6, tPhi: 1.25, tRadius: CAMERA_LIMITS.home, vTheta: 0, vPhi: 0 });
  const tmp = useMemo(() => ({ v: new Vector3(), ndc: new Vector2(), o: new Vector3(), d: new Vector3() }), []);

  const pick = (clientX: number, clientY: number): number | null => {
    const rect = gl.domElement.getBoundingClientRect();
    tmp.ndc.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(tmp.ndc, camera);
    const o = raycaster.ray.origin, d = raycaster.ray.direction;
    const b = o.dot(d), c = o.lengthSq() - 1, disc = b * b - c;
    if (disc < 0 || !planet.current) return null;
    tmp.v.copy(d).multiplyScalar(-b - Math.sqrt(disc)).add(o);
    planet.current.worldToLocal(tmp.v).normalize();
    const frame = usePlanetStore.getState().frame;
    return frame ? nearestCell(getMesh(frame.level), tmp.v.x, tmp.v.y, tmp.v.z) : null;
  };

  useEffect(() => {
    const st = s.current;
    cameraApi.rotate = (dt, dp) => { st.tTheta += dt; st.tPhi = Math.min(Math.PI - 0.15, Math.max(0.15, st.tPhi + dp)); runtime.lastInput = performance.now(); };
    cameraApi.zoom = (f) => { st.tRadius = Math.min(CAMERA_LIMITS.max, Math.max(CAMERA_LIMITS.min, st.tRadius * f)); runtime.lastInput = performance.now(); };
    cameraApi.reset = () => { st.tTheta = 0.6; st.tPhi = 1.25; st.tRadius = CAMERA_LIMITS.home; runtime.lastInput = performance.now(); };
    cameraApi.pickCenter = () => { const r = gl.domElement.getBoundingClientRect(); const cell = pick(r.left + r.width / 2, r.top + r.height / 2); if (cell !== null) usePlanetStore.getState().selectCell(cell); };
    pending.splice(0).forEach((f) => f());
    if (!interactive) return;
    const el = gl.domElement;
    const pointers = new Map<number, { x: number; y: number }>();
    let moved = 0, pinch = 0, lastHover = 0;
    const down = (e: PointerEvent) => { el.setPointerCapture(e.pointerId); pointers.set(e.pointerId, { x: e.clientX, y: e.clientY }); moved = 0; pinch = 0; st.vTheta = st.vPhi = 0; runtime.lastInput = performance.now(); };
    const move = (e: PointerEvent) => {
      const p = pointers.get(e.pointerId);
      if (!p) {
        if (e.pointerType === "mouse" && performance.now() - lastHover > 70) { lastHover = performance.now(); const cell = pick(e.clientX, e.clientY); if (cell !== usePlanetStore.getState().hoveredCell) usePlanetStore.setState({ hoveredCell: cell }); }
        return;
      }
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY; moved += Math.abs(dx) + Math.abs(dy);
      const k = (0.005 * st.radius) / CAMERA_LIMITS.home / Math.max(1, pointers.size);
      cameraApi.rotate(-dx * k, -dy * k);
      st.vTheta = -dx * k * 12; st.vPhi = -dy * k * 12;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()], dist = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch > 0) cameraApi.zoom(pinch / dist);
        pinch = dist;
      }
    };
    const up = (e: PointerEvent) => {
      if (pointers.size === 1 && moved < 6) { const cell = pick(e.clientX, e.clientY); usePlanetStore.getState().selectCell(cell); }
      pointers.delete(e.pointerId); pinch = 0;
    };
    const wheel = (e: WheelEvent) => { e.preventDefault(); cameraApi.zoom(Math.exp(e.deltaY * 0.0012)); };
    const dbl = (e: MouseEvent) => { const cell = pick(e.clientX, e.clientY); if (cell !== null) usePlanetStore.getState().focusOn(cell); };
    const leave = () => usePlanetStore.setState({ hoveredCell: null });
    el.addEventListener("pointerdown", down); el.addEventListener("pointermove", move); el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
    el.addEventListener("wheel", wheel, { passive: false }); el.addEventListener("dblclick", dbl); el.addEventListener("pointerleave", leave);
    el.style.touchAction = "none";
    return () => {
      el.removeEventListener("pointerdown", down); el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up); el.removeEventListener("pointercancel", up);
      el.removeEventListener("wheel", wheel); el.removeEventListener("dblclick", dbl); el.removeEventListener("pointerleave", leave);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl, camera, interactive]);

  // Focus on a region: turn the camera to the cell and move closer.
  useEffect(() => usePlanetStore.subscribe((state, prev) => {
    if (state.focusSeq === prev.focusSeq || state.focusCell === null || !state.frame || !planet.current) return;
    const c = getMesh(state.frame.level).centers, i = state.focusCell * 3, st = s.current;
    tmp.v.set(c[i], c[i + 1], c[i + 2]);
    planet.current.localToWorld(tmp.v).normalize();
    const theta = Math.atan2(tmp.v.x, tmp.v.z);
    st.tTheta = st.theta + Math.atan2(Math.sin(theta - st.theta), Math.cos(theta - st.theta));
    st.tPhi = Math.min(Math.PI - 0.15, Math.max(0.15, Math.acos(tmp.v.y)));
    st.tRadius = CAMERA_LIMITS.focus; runtime.lastInput = performance.now();
  }), [planet, tmp]);

  useFrame((_, dt) => {
    const st = s.current, store = usePlanetStore.getState();
    const d = Math.min(dt, 0.1), k = store.still ? 1 : 1 - Math.exp(-d * 7);
    const idle = performance.now() - runtime.lastInput > 6000;
    if (!store.still) {
      if (Math.abs(st.vTheta) > 1e-4) { st.tTheta += st.vTheta * d; st.vTheta *= Math.exp(-d * 4); }
      if (idle && store.autoRotate && interactive) st.tTheta += d * 0.035;
    }
    st.theta += (st.tTheta - st.theta) * k; st.phi += (st.tPhi - st.phi) * k; st.radius += (st.tRadius - st.radius) * k;
    const sp = Math.sin(st.phi);
    camera.position.set(st.radius * sp * Math.sin(st.theta), st.radius * Math.cos(st.phi), st.radius * sp * Math.cos(st.theta));
    camera.lookAt(0, 0, 0);
    runtime.cameraDistance = st.radius;
  });
  return null;
}
