import * as THREE from 'three'
import type { RefObject } from 'react'
import { createPlanetMaterial, createAtmosphere } from '@/lib/planetKit'
import { createStarMaterial, createGlow } from '@/lib/starkit'
import type { SimState } from '@/components/simulador/types'
import { AXIAL_TILT_DEG, MIN_ZOOM, MAX_ZOOM, VIEW_SYSTEM } from '@/components/simulador/data'

/**
 * Monta a cena inteira (starfield + estrela + planeta orbitando + a
 * câmera que segue o planeta) dentro do canvas informado.
 * 
 * De propósito, este arquivo não usa hooks nem sabe nada de React — só
 * recebe o `sim` (um MutableRefObject) para ler/escrever o estado da
 * simulação a cada quadro sem precisar re-renderizar componente nenhum.
 * Chame de dentro de um `useEffect(() => createPlanetSystemScene(...), [])`
 * (ver `Viewport.tsx`) e use o retorno como função de limpeza.
 */
export function createPlanetSystemScene(
  canvas: HTMLCanvasElement,
  viewport: HTMLElement,
  sim: RefObject<SimState>
): () => void {
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200)

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setClearColor(0x000000, 0)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  /* ---------- starfield (cintilante) ---------- */
  const starFieldMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 } },
    vertexShader: /* glsl */ `
      attribute float aSize; attribute float aPhase;
      varying float vPhase;
      void main() {
        vPhase = aPhase;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = aSize;
      }`,
    fragmentShader: /* glsl */ `
      precision mediump float;
      uniform float uTime;
      varying float vPhase;
      void main() {
        vec2 uv = gl_PointCoord - 0.5;
        float d = length(uv);
        if (d > 0.5) discard;
        float disc = smoothstep(0.5, 0.0, d);
        float twinkle = 0.5 + 0.5 * sin(uTime * 1.4 + vPhase * 6.2831853);
        gl_FragColor = vec4(vec3(0.92, 0.95, 1.0), disc * (0.5 + 0.5 * twinkle));
      }`,
  })
  const starCount = 900
  const starPos = new Float32Array(starCount * 3)
  const starSize = new Float32Array(starCount)
  const starPhase = new Float32Array(starCount)
  for (let i = 0; i < starCount; i++) {
    const r = 60 * (0.6 + Math.random() * 0.4)
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    starPos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    starPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    starPos[i * 3 + 2] = r * Math.cos(phi)
    starSize[i] = Math.random() > 0.92 ? 2.4 : 1.1
    starPhase[i] = Math.random()
  }
  const starFieldGeo = new THREE.BufferGeometry()
  starFieldGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3))
  starFieldGeo.setAttribute('aSize', new THREE.BufferAttribute(starSize, 1))
  starFieldGeo.setAttribute('aPhase', new THREE.BufferAttribute(starPhase, 1))
  const starField = new THREE.Points(starFieldGeo, starFieldMaterial)
  scene.add(starField)

  /* ---------- estrela: granulação + escurecimento de limbo, com corona ---------- */
  const starMat = createStarMaterial()
  const star = new THREE.Mesh(new THREE.SphereGeometry(2.0, 64, 64), starMat)
  scene.add(star)
  scene.add(createGlow(2.5, '#FFD98A', 3.2, 0.85))
  scene.add(createGlow(3.2, '#FFB65C', 2.0, 0.5))

  /* ---------- caminho da órbita (guia visual) ---------- */
  const ORBIT_RADIUS = 8.5
  const orbitPts: THREE.Vector3[] = []
  for (let i = 0; i <= 128; i++) {
    const a = (i / 128) * Math.PI * 2
    orbitPts.push(new THREE.Vector3(Math.cos(a) * ORBIT_RADIUS, 0, Math.sin(a) * ORBIT_RADIUS))
  }
  const orbitLine = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(orbitPts),
    new THREE.LineBasicMaterial({ color: '#3FA9FF', transparent: true, opacity: 0.22 })
  )
  scene.add(orbitLine)

  /* ---------- planeta: gira no próprio eixo E orbita a estrela ---------- */
  const orbitPivot = new THREE.Group() // gira em Y → move o planeta ao redor da estrela
  scene.add(orbitPivot)

  const tiltGroup = new THREE.Group() // inclinação axial fixa, não acompanha a órbita
  tiltGroup.rotation.z = THREE.MathUtils.degToRad(AXIAL_TILT_DEG)
  tiltGroup.position.set(ORBIT_RADIUS, 0, 0)
  orbitPivot.add(tiltGroup)

  const planet = new THREE.Mesh(new THREE.SphereGeometry(1.3, 96, 96), createPlanetMaterial({ seed: 7.0 }))
  tiltGroup.add(planet)

  const atmo = createAtmosphere(1.37, '#3FA9FF')
  tiltGroup.add(atmo)

  const axisMat = new THREE.LineDashedMaterial({ color: '#7FD1FF', dashSize: 0.08, gapSize: 0.06, transparent: true, opacity: 0.55 })
  const axisGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -1.9, 0), new THREE.Vector3(0, 1.9, 0)])
  const axisLine = new THREE.Line(axisGeo, axisMat)
  axisLine.computeLineDistances()
  tiltGroup.add(axisLine)

  /* ---------- câmera: segue o planeta (não a estrela) ---------- */
  let azimuth = 0.6
  let elevation = 0.32
  let radius = VIEW_SYSTEM
  const planetWorldPos = new THREE.Vector3()

  function updateCamera() {
    planet.getWorldPosition(planetWorldPos)
    const clampedElev = Math.max(-1.2, Math.min(1.2, elevation))
    camera.position.set(
      planetWorldPos.x + radius * Math.cos(clampedElev) * Math.sin(azimuth),
      planetWorldPos.y + radius * Math.sin(clampedElev),
      planetWorldPos.z + radius * Math.cos(clampedElev) * Math.cos(azimuth)
    )
    camera.lookAt(planetWorldPos)
  }
  updateCamera()

  /* ---------- interação: arrastar para orbitar, scroll para zoom ---------- */
  let dragging = false
  let lastX = 0
  let lastY = 0
  const onPointerDown = (e: PointerEvent) => {
    dragging = true
    lastX = e.clientX
    lastY = e.clientY
    viewport.style.cursor = 'grabbing'
    viewport.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: PointerEvent) => {
    if (!dragging) return
    azimuth -= (e.clientX - lastX) * 0.0055
    elevation += (e.clientY - lastY) * 0.0055
    lastX = e.clientX
    lastY = e.clientY
  }
  const onPointerEnd = () => {
    dragging = false
    viewport.style.cursor = 'grab'
  }
  const onWheel = (e: WheelEvent) => {
    e.preventDefault()
    radius = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, radius + e.deltaY * 0.012))
    sim.current.targetRadius = radius // scroll manual cancela transição em andamento
  }
  viewport.style.cursor = 'grab'
  viewport.addEventListener('pointerdown', onPointerDown)
  viewport.addEventListener('pointermove', onPointerMove)
  viewport.addEventListener('pointerup', onPointerEnd)
  viewport.addEventListener('pointercancel', onPointerEnd)
  viewport.addEventListener('pointerleave', onPointerEnd)
  viewport.addEventListener('wheel', onWheel, { passive: false })

  /* ---------- responsivo ---------- */
  function resize() {
    const w = viewport.clientWidth
    const h = viewport.clientHeight
    if (!w || !h) return
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }
  window.addEventListener('resize', resize)
  resize()

  /* ---------- loop ---------- */
  const ROTATION_SPEED = 0.18 // rad/s na velocidade 1× — dia (rotação própria)
  const ORBIT_SPEED = 0.055 // rad/s na velocidade 1× — ano (translação, mais lenta que o dia)
  const clock = new THREE.Clock()
  let frameId = 0

  function tick() {
    frameId = requestAnimationFrame(tick)
    const dt = clock.getDelta()
    const elapsed = clock.getElapsedTime()
    starFieldMaterial.uniforms.uTime.value = elapsed
    starMat.uniforms.uTime.value = elapsed

    if (sim.current.rotating) {
      planet.rotation.y += ROTATION_SPEED * sim.current.speed * dt
      orbitPivot.rotation.y += ORBIT_SPEED * sim.current.speed * dt
    }

    radius += (sim.current.targetRadius - radius) * 0.08 // zoom suave até o preset
    updateCamera() // a câmera segue o planeta, que está sempre se movendo
    renderer.render(scene, camera)
  }
  tick()

  /* ---------- limpeza ---------- */
  return function dispose() {
    cancelAnimationFrame(frameId)
    window.removeEventListener('resize', resize)
    viewport.removeEventListener('pointerdown', onPointerDown)
    viewport.removeEventListener('pointermove', onPointerMove)
    viewport.removeEventListener('pointerup', onPointerEnd)
    viewport.removeEventListener('pointercancel', onPointerEnd)
    viewport.removeEventListener('pointerleave', onPointerEnd)
    viewport.removeEventListener('wheel', onWheel)

    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if ('geometry' in mesh && mesh.geometry) mesh.geometry.dispose()
      const material = (mesh as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined
      if (Array.isArray(material)) material.forEach((m) => m.dispose())
      else material?.dispose()
    })
    renderer.dispose()
  }
}