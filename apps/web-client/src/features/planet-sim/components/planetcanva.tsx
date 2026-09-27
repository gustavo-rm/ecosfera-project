'use client'

import { useEffect, useRef, useState } from 'react'
import type { SimState, ViewMode } from '@/components/simulador/types'
import { INITIAL_TASKS, VIEW_PLANET, VIEW_SYSTEM } from '@/components/simulador/data'
import Viewport from '@/components/simulador/sidebar/viewport'
import Sidebar from '@/components/simulador/sidebar/sidebasr'

/**
 * Ponto de entrada do simulador. Só cuida de estado (React) e composição
 * — toda a cena 3D mora em `scene.ts` (via `Viewport`), e a barra
 * lateral está dividida em `TasksPanel` / `PlanetDataPanel` /
 * `SimulationControls` (via `Sidebar`).
 */
export default function PlanetSimulator() {
  const simRef = useRef<SimState>({ rotating: false, speed: 1, targetRadius: VIEW_SYSTEM })

  const [rotating, setRotating] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [activeView, setActiveView] = useState<ViewMode>('system')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [tasks, setTasks] = useState(INITIAL_TASKS)

  useEffect(() => {
    simRef.current.rotating = rotating
  }, [rotating])

  useEffect(() => {
    simRef.current.speed = speed
  }, [speed])

  function setView(view: ViewMode) {
    setActiveView(view)
    simRef.current.targetRadius = view === 'system' ? VIEW_SYSTEM : VIEW_PLANET
  }

  function toggleTask(index: number) {
    setTasks((prev) => prev.map((t, i) => (i === index ? { ...t, done: !t.done } : t)))
  }

  return (
    <div className="fixed inset-0 flex h-svh w-screen overflow-hidden bg-space text-ink">
      <Viewport simRef={simRef} activeView={activeView} onSetView={setView} onOpenSidebar={() => setSidebarOpen(true)} />

      {/* backdrop do painel no mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-30 bg-[rgba(2,5,12,.55)] md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        tasks={tasks}
        onToggleTask={toggleTask}
        rotating={rotating}
        onToggleRotating={() => setRotating((r) => !r)}
        speed={speed}
        onSpeedChange={setSpeed}
      />
    </div>
  )
}