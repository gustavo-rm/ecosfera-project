'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { createPlanetMaterial, createAtmosphere } from '@/lib/planetKit'

/**
 * Cena 3D da seção final.
 * Sem terreno, sem horizonte: o planeta é o único elemento visual,
 * centralizado, ecoando o planeta do hero em outra paleta (azul-gelo).
 *
 * A luz vem do lado/de trás de propósito: a face voltada para a câmera
 * (onde o texto fica por cima) permanece mais escura, só uma lateral
 * pega o brilho — isso melhora o contraste do texto centralizado sem
 * precisar de nenhuma camada extra atrás dele.
 */
export default function CtaScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 100)
    camera.position.set(0, 0, 20)

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    const planet = new THREE.Mesh(
      new THREE.SphereGeometry(5.4, 96, 96),
      createPlanetMaterial({
        seed: 41.0,
        ocean: '#173E72',
        shelf: '#2C6FB0',
        coast: '#8FB8DE',
        land: '#3E6FA0',
        forest: '#2A5A8C',
        rock: '#5B7690',
        ice: '#EAF4FF',
        rim: '#7FD1FF',
        lightDir: new THREE.Vector3(-0.85, 0.35, -0.25),
      })
    )
    planet.position.set(0, 0, 0)
    scene.add(planet)

    const atmo = createAtmosphere(5.7, '#7FD1FF')
    atmo.position.copy(planet.position)
    scene.add(atmo)

    const ROTATION_SPEED = 0.05 // bem mais lento — dá presença, sem distrair do texto
    const clock = new THREE.Timer()
    let visible = true
    let frameId = 0

    function resize() {
      const w = canvas!.clientWidth
      const h = canvas!.clientHeight
      if (!w || !h) return
      renderer.setSize(w, h, false)
      camera.aspect = w / h
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
      planet.rotation.y += ROTATION_SPEED * dt
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

  return <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />
}
