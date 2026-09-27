'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { createPlanetMaterial, createAtmosphere } from '@/lib/planetKit'

/**
 * Cena 3D do hero — versão final.
 * Sem DNA: o planeta é o visual principal, grande e centralizado,
 * girando bem devagar e de forma constante.
 */
export default function HeroScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const scene = new THREE.Scene()
    // Sem cor de fundo sólida: o fundo espacial fixo (GlobalStarfield)
    // aparece por trás, criando profundidade entre as camadas.

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200)
    camera.position.set(0, 1.2, 20)

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    /* ---------- planeta procedural ---------- */
    const planet = new THREE.Mesh(new THREE.SphereGeometry(6.4, 96, 96), createPlanetMaterial({ seed: 7.0 }))
    planet.position.set(0, -2.6, 0)
    scene.add(planet)

    const atmo = createAtmosphere(6.78, '#3FA9FF')
    atmo.position.copy(planet.position)
    scene.add(atmo)

    /* ---------- loop ---------- */
    const PLANET_SPEED = 0.045 // rad/s ≈ 140s por volta
    const clock = new THREE.Clock()
    let visible = true
    let frameId = 0

    function resize() {
      const w = canvas!.clientWidth
      const h = canvas!.clientHeight
      if (!w || !h) return
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      // enquadramento responsivo: recua a câmera em telas estreitas
      camera.position.z = w < 760 ? 27 : 20
      camera.updateProjectionMatrix()
    }
    window.addEventListener('resize', resize)
    resize()

    const observer = new IntersectionObserver(
      (entries) => {
        visible = entries[0].isIntersecting
      },
      { threshold: 0 }
    )
    observer.observe(canvas)

    function tick() {
      frameId = requestAnimationFrame(tick)
      const dt = clock.getDelta()
      if (!visible) return
      planet.rotation.y += PLANET_SPEED * dt
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener('resize', resize)
      observer.disconnect()
      planet.geometry.dispose()
      ;(planet.material as THREE.Material).dispose()
      atmo.geometry.dispose()
      ;(atmo.material as THREE.Material).dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full"
      style={{
        maskImage: 'linear-gradient(to bottom, #000 80%, transparent)',
        WebkitMaskImage: 'linear-gradient(to bottom, #000 80%, transparent)',
      }}
    />
  )
}
