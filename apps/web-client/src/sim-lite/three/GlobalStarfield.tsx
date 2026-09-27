'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * Fundo espacial fixo (position: fixed), atrás de toda a página — para
 * que a página inteira leia como uma cena contínua no espaço. Estrelas
 * com tamanho e brilho variados e leve cintilação via shader; sem
 * nebulosa, perto de preto puro.
 */
export default function GlobalStarfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const scene = new THREE.Scene()
    const camera = new THREE.OrthographicCamera(0, 1, 0, 1, 0, 10)
    camera.position.z = 5

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true })
    renderer.setClearColor(0x000000, 0)
    const pixelRatio = Math.min(window.devicePixelRatio, 2)
    renderer.setPixelRatio(pixelRatio)

    const material = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uTime: { value: 0 }, uPixelRatio: { value: pixelRatio } },
      vertexShader: /* glsl */ `
        attribute float aSize;
        attribute float aPhase;
        attribute vec3 aColor;
        varying float vPhase;
        varying vec3 vColor;
        uniform float uPixelRatio;
        void main() {
          vPhase = aPhase;
          vColor = aColor;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * uPixelRatio;
        }
      `,
      fragmentShader: /* glsl */ `
        precision mediump float;
        uniform float uTime;
        varying float vPhase;
        varying vec3 vColor;
        void main() {
          vec2 uv = gl_PointCoord - 0.5;
          float d = length(uv);
          if (d > 0.5) discard;
          float disc = smoothstep(0.5, 0.0, d);
          float twinkle = 0.5 + 0.5 * sin(uTime * 1.4 + vPhase * 6.2831853);
          float alpha = disc * (0.55 + 0.45 * twinkle);
          gl_FragColor = vec4(vColor, alpha);
        }
      `,
    })

    const points = new THREE.Points(new THREE.BufferGeometry(), material)
    scene.add(points)

    const WHITE = new THREE.Color('#EAF3FF')
    const BLUEISH = new THREE.Color('#C9D9F2')
    const WARM = new THREE.Color('#F3CE9B')

    function populate(w: number, h: number) {
      const density = 0.00075 // estrelas por px² — ajusta a quantidade à área visível
      const count = Math.round(Math.min(Math.max(w * h * density, 260), 1100))

      const positions = new Float32Array(count * 3)
      const sizes = new Float32Array(count)
      const phases = new Float32Array(count)
      const colors = new Float32Array(count * 3)
      const tint = new THREE.Color()

      for (let i = 0; i < count; i++) {
        positions[i * 3] = Math.random() * w
        positions[i * 3 + 1] = Math.random() * h
        positions[i * 3 + 2] = 0

        const roll = Math.random()
        sizes[i] = roll > 0.94 ? 2.2 + Math.random() * 1.4 : 0.9 + Math.random() * 1.1
        phases[i] = Math.random()

        const colorRoll = Math.random()
        if (colorRoll < 0.06) tint.copy(WARM)
        else if (colorRoll < 0.4) tint.copy(BLUEISH)
        else tint.copy(WHITE)
        colors[i * 3] = tint.r
        colors[i * 3 + 1] = tint.g
        colors[i * 3 + 2] = tint.b
      }

      const geo = points.geometry
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
      geo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))
      geo.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    }

    function resize() {
      const w = canvas!.clientWidth
      const h = canvas!.clientHeight
      if (!w || !h) return
      renderer.setSize(w, h, false)
      camera.left = 0
      camera.right = w
      camera.top = h
      camera.bottom = 0
      camera.updateProjectionMatrix()
      populate(w, h)
    }

    let resizeTimer: ReturnType<typeof setTimeout>
    const onResize = () => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(resize, 150)
    }
    window.addEventListener('resize', onResize)
    resize()

    const clock = new THREE.Timer()
    let frameId = 0
    function tick() {
      frameId = requestAnimationFrame(tick)
      if (document.hidden) return
      material.uniforms.uTime.value = clock.getElapsed()
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      cancelAnimationFrame(frameId)
      clearTimeout(resizeTimer)
      window.removeEventListener('resize', onResize)
      points.geometry.dispose()
      material.dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 bg-space" aria-hidden="true">
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
    </div>
  )
}
